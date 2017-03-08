#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Coalition server.
"""

from twisted.web import xmlrpc, server, static, http
from twisted.internet import defer, reactor
from twisted.web.server import Session
import cPickle, time, os, getopt, sys, base64, re, thread, ConfigParser, random, shutil
import atexit, json
import smtplib
from email.mime.text import MIMEText
from textwrap import dedent, fill

from db_sqlite import DBSQLite
from db_mysql import DBMySQL
from db_sql import LdapError


### Functions ###

# Configuration functions
def cfgInt (name, defvalue):
	global config
	if config.has_option('server', name):
		try:
			return int (config.get('server', name))
		except:
			pass
	return defvalue


def cfgBool (name, defvalue):
	global config
	if config.has_option('server', name):
		try:
			return int (config.get('server', name)) != 0
		except:
			pass
	return defvalue


def cfgStr (name, defvalue):
	global config
	if config.has_option('server', name):
		try:
			return str (config.get('server', name))
		except:
			pass
	return defvalue

def usage():
	print ("Usage: server [OPTIONS]")
	print ("Start a Coalition server.\n")
	print ("Options:")
	print ("  -h, --help\t\tShow this help")
	print ("  -p, --port=PORT\tPort used by the server (default: "+str(port)+")")
	print ("  -v, --verbose\t\tIncrease verbosity")
	print ("  --init\t\tInitialize the database")
	print ("  --migrate\t\tMigrate the database with interactive confirmation")
	print ("  --reset\t\tReset the database (warning: all previous data are lost)")
	if sys.platform == "win32":	
		print ("  -c, --console=\t\tRun as a windows console application")
		print ("  -s, --service=\t\tRun as a windows service")
	print ("\nExample : server -p 1234")


# Log functions
def vprint (str):
	if verbose:
		print (str)
		sys.stdout.flush()

def getLogFilename (jobId):
	global dataDir
	return dataDir + "/logs/" + str(jobId) + ".log"


def getLogFilter (pattern):
	"""Get the pattern filter from the cache or add one"""
	global LogFilterCache
	try:	
		filter = LogFilterCache[pattern]
	except KeyError:
		filter = LogFilter (pattern)
		LogFilterCache[pattern] = filter
	return filter


def writeJobLog (jobId, log):
	logFile = open (getLogFilename (jobId), "a")
	logFile.write (log)
	logFile.close ()	

# Notify functions
def sendEmail (to, message) :
	if to != "" :
		vprint ("Send email to " + to + " : " + message)
		if smtphost != "" :
			# Create a text/plain message
			msg = MIMEText(message)

			# me == the sender's email address
			# you == the recipient's email address
			msg['Subject'] = message
			msg['From'] = smtpsender
			msg['To'] = to

			# Send the message via our own SMTP server, but don't include the
			# envelope header.
			try:
				s = smtplib.SMTP(smtphost, smtpport)
				if smtptls:
					s.ehlo()
					s.starttls()
					s.ehlo() 
				if smtplogin != '' or smtppasswd != '':
					s.login(smtplogin, smtppasswd)
				s.sendmail (smtpsender, [to], msg.as_string())
				s.quit()
			except Exception as inst:
				vprint (inst)
				pass


def notifyError (job):
	if job['user'] :
		sendEmail (job['user'], 'ERRORS in job ' + job['title'] + ' (' + str(job['id']) + ').')


def notifyFinished (job):
	if job['user'] :
		sendEmail (job['user'], 'The job ' + job['title'] + ' (' + str(job['id']) + ') is FINISHED.')


def notifyFirstFinished (job):
	if job['user'] :
		sendEmail (job['user'], 'The job ' + job['title'] + ' (' + str(job['id']) + ') has finished ' + str(notifyafter) + ' jobs.')

def _interactiveConfirmation(confirmation_sentence="Yes I know what I'm doing."):
	"""Ask the user for confirmation."""
	text = "Please write this sentence then press enter to confirm:\n"+confirmation_sentence+'\n'
	print (text)
	sys.stdout.flush()
	answer = raw_input()
	if answer == confirmation_sentence:
		return True
	return False


### LDAP functions ###

### LDAP classes and functions ###

def authenticate(request):
	"""Check user authentication via LDAP if LDAP is configured in settings. If authenticated, get users permissions."""

	ldap_permissions = {
			"ldaptemplatecreatejob": False, 
			"ldaptemplateviewjob": False, 
			"ldaptemplateeditjob": False, 
			"ldaptemplatedeletejob": False, 
			"ldaptemplatecreatejobglobal": False, 
			"ldaptemplateviewjobglobal": False, 
			"ldaptemplateeditjobglobal": False, 
			"ldaptemplatedeletejobglobal": False, 
			}

	def _getLdapPermissions(connection, username):
		ldap_base = cfgStr("ldapbase", "")

		def _ldapSearch(connection, query):
			if connection.search_ext_s(ldap_base, ldap.SCOPE_SUBTREE, query, ['dn']):
				return True
			return False

		for permission in ldap_permissions.keys():
			search_template = cfgStr(permission, "").replace("__login__", username)
			ldap_permissions[permission] = _ldapSearch(connection, search_template)

		return ldap_permissions

	if LDAPServer:
		username = request.getUser()
		password = request.getPassword()

		# Check if the request comes from the webfrontend.
		m = re.match(r"^/api/webfrontend/", request.path)
		if m:
			webfrontendrequest = True
			request.path = request.path.replace("webfrontend/", "", 1)
		else:
			webfrontendrequest = False

		if config.has_option("server", "ldapunsafeapi") and config.getboolean("server", "ldapunsafeapi") and webfrontendrequest is False:
			# This request does not comes from the webfrontend and unsafe mode is set.
			# Granting full access.
			vprint("[LDAP] Access granted for unsafe API")
			for k in ldap_permissions.keys():
				ldap_permissions[k] = True
			return True, ldap_permissions

		if username or password:
			l = ldap.initialize(LDAPServer)
			vprint("[LDAP] Authenticate {}".format(username))
			ldapUsername = LDAPTemplateLogin.replace("__login__", username)
			try:
				if l.bind_s(ldapUsername, password, ldap.AUTH_SIMPLE):
					vprint("[LDAP] Authentication accepted for user {}".format(username))
					request.addCookie("authenticated_user", username, path="/")
					ldap_permissions = _getLdapPermissions(l, username)
					return True, ldap_permissions

			except ldap.LDAPError as e:
				vprint("[LDAP] Authentication failed for user {}".format(username))
				vprint("[LDAP] {}".format(e))
				pass
		else:
			vprint("[LDAP] Authentication required")
		request.setHeader("WWW-Authenticate", 'Basic realm="Coalition login"')
		request.setResponseCode(http.UNAUTHORIZED)
		return False, {}
	return True, {}

def grantAddJob(user, cmd):
	"""Check if the logged in user can add this command."""
	def checkWhiteList(wl):
		for pattern in wl:
			if (re.match (pattern, cmd)):
				return True
		else:
			vprint("[LDAP] Not authorized. User {} is not allowed to add the command {}".format(user, cmd))
		return False

	# Is user defined white list ?		
	if user in UserCmdWhiteList:
		wl = UserCmdWhiteList[user]
		if checkWhiteList(wl):
			return True
		# If in the global command white list
		if GlobalCmdWhiteList:
			if checkWhiteList(GlobalCmdWhiteList):
				return True
		return False
	else:
		# If in the global command white list
		if GlobalCmdWhiteList:
			if not checkWhiteList(GlobalCmdWhiteList):
				return False

	# Cleared
	return True

def listenUDP():
	"""Listen to UDP socket to respond to the workers broadcast."""
	from socket import SOL_SOCKET, SO_BROADCAST
	from socket import socket, AF_INET, SOCK_DGRAM, error
	s = socket (AF_INET, SOCK_DGRAM)
	s.bind (('0.0.0.0', port))
	while 1:
		try:
			data, addr = s.recvfrom (1024)
			s.sendto ("roxor", addr)
		except:
			pass


def main():
	"""Start the UDP server used for the broadcast."""
	thread.start_new_thread (listenUDP, ())

	from twisted.internet import reactor
	from twisted.web import server
	root = Root("public_html")
	webService = Master()
	workers = Workers()
	root.putChild('xmlrpc', webService)
	root.putChild('api', webService)
	root.putChild('workers', workers)
	vprint ("[Init] Listen on port " + str (port))
	reactor.listenTCP(port, server.Site(root))
	reactor.run()


### Classes ###

class LogFilter:
	"""A log filter object. The log pattern must include a '%percent' or a '%one' key word."""

	def __init__ (self, pattern):
		# 0~100 or 0~1 ?
		self.IsPercent = re.match (".*%percent.*", pattern) != None

		# Build the final pattern for the RE
		if self.IsPercent:
			pattern = re.sub ("%percent", "([0-9.]+)", pattern)
		else:
			pattern = re.sub ("%one", "([0-9.]+)", pattern)

		# Final progress filter
		self.RE = re.compile(pattern)

		# Put it in the cache
		global LogFilterCache
		LogFilterCache[pattern] = self

	def filterLogs (self, log):
		"""Return the filtered log and the last progress, if any"""
		progress = None
		for m in self.RE.finditer (log):
			capture = m.group(1)
			try:
				progress = float(capture) / (self.IsPercent and 100.0 or 1.0)
			except ValueError:
				pass
		#return self.RE.sub ("", log), progress
		return log, progress


def ldapUserAllowed(user, action):
	"""Check if user is allowed to do this action."""
	vprint("Is user {} allowed to do {}?".format(user, action))
	# Cleared
	return True

### Twisted class ###
class Root(static.File):
	"""Create twisted landing page and check if LDAP authentication is required."""

	def __init__(self, path, defaultType="text/html", ignoredExts=(), registry=None, allowExt=0):
		static.File.__init__(self, path, defaultType, ignoredExts, registry, allowExt)

	def render(self, request):
		(authenticated, permissions) = authenticate(request)
		if authenticated:
			return static.File.render(self, request)
		request.setResponseCode(http.UNAUTHORIZED)
		return "LDAP authorization required."

### XMLRPC API classes ###
class Master(xmlrpc.XMLRPC):
	"""Defines XMLRPC and API for users interactions. Defines logger.""" 

	def __init__(self):
		self.user = "" # Default value, overwritten later in case of LDAP authentication

	def render(self, request):
		with db:
			vprint("[{}] {}".format(request.method, request.path))
			(authenticated, permissions) = authenticate(request)
			if authenticated:
				self.user = db.ldap_user = request.getUser()
				db.permissions = permissions

				def getArg(name, default):
					value = request.args.get(name, [default])
					return value[0]

				# The legacy method for compatibility
				if request.path == "/xmlrpc/addjob":
					parent = getArg("parent", "0")
					title = getArg("title", "New job")
					cmd = getArg("cmd", getArg("command", ""))
					dir = getArg("dir", ".")
					environment = getArg("env", None)
					if environment == "":
						environment = None
					priority = getArg("priority", "1000")
					timeout = getArg("timeout", "0")
					affinity = getArg("affinity", "")
					dependencies = getArg("dependencies", "")
					progress_pattern = getArg("localprogress", "")
					url = getArg("url", "")
					user = getArg("user", "")
					state = getArg("state", "WAITING")
					paused = getArg("paused", "0")
					if self.user != "":
						user = self.user

					if grantAddJob(self.user, cmd):
						vprint ("Add job: {}".format(cmd))
						# try as an int
						parent = int(parent)
						if type(dependencies) is str:
							# Parse the dependencies string
							dependencies = re.findall('(\d+)', dependencies)
						for i, dep in enumerate(dependencies) :
							dependencies[i] = int(dep)

						job = db.newJob (parent, str (title), str (cmd), str (dir), str (environment),
								str (state), int (paused), int (timeout), int (priority), str (affinity),
								str (user), str (url), str (progress_pattern))
						if job is not None:
							db.setJobDependencies(job['id'], dependencies)
							return str(job['id'])
					return "-1"
				else:
					try:
						value = request.content.getvalue()
						if request.method != "GET":
							data = value and json.loads(request.content.getvalue()) or {}
							if verbose:
								vprint ("[Content] {}".format(repr(data)))
						else:
							if verbose:
								vprint ("[Content] {}".format(repr(request.args)))

						def getArg(name, default):
							if request.method == "GET":
								# GET params
								value = request.args.get(name, [default])[0]
								value = type(default)(default if value == None else value)
								assert(value != None)
								return value
							else:
								# JSON params
								value = data.get(name)
								value = type(default)(default if value == None else value)
								assert(value != None)
								return value

						def api_rest():
							"""REST API."""
							
							# REST PUT API
							if request.method == "PUT":
								if request.path == "/api/jobs":
									if grantAddJob(self.user, getArg("command","")):
										job = db.newJob ((getArg("parent",0)),
														 (getArg("title","")),
														 (getArg("command","")),
														 (getArg("dir","")),
														 (getArg("environment","")), 
														 (getArg("state","WAITING")),
														 (getArg("paused",0)),
														 (getArg("timeout",1000)),
														 (getArg("priority",1000)),
														 (getArg("affinity", "")), 
														 (getArg("user", "")),
														 (getArg("url", "")),
														 (getArg("progress_pattern", "")),
														 (getArg("dependencies", [])))
										return job['id']
									else:
										return False

							# REST GET API
							elif request.method == "GET":
								m = re.match(r"^/api/jobs/(\d+)$", request.path)
								if m:
									return db.getJob(int(m.group (1)))
								m = re.match(r"^/api/jobs/(\d+)/children$", request.path)
								if m:
									return db.getJobChildren(int(m.group (1)), {})
								m = re.match(r"^/api/jobs/(\d+)/dependencies$", request.path)
								if m:
									return db.getJobDependencies(int(m.group (1)))
								m = re.match(r"^/api/jobs/(\d+)/childrendependencies$", request.path)
								if m:
									return db.getChildrenDependencyIds(int(m.group (1)))
								m = re.match(r"^/api/jobs/(\d+)/log$", request.path)
								if m:
									return self.getLog(int(m.group (1)))
								if request.path == "/api/jobs":
									db.ldap_permission = ldapUserActionAllowed(self.user, "view")
									return db.getJobChildren(0, {})

								m = re.match(r"^/api/jobs/count/where/$", request.path)
								if m:
									return db.getCountJobsWhere(request.args["where_clause"])

								m = re.match(r"^/api/jobs/where/$", request.path)
								if m:
									return db.getJobsWhere(
											where_clause=request.args["where_clause"][0],
											index_min=request.args["min"][0],
											index_max=request.args["max"][0],
											)

								if request.path == "/api/workers":
									return db.getWorkers()
								if request.path == "/api/events":
									return db.getEvents(getArg("job", -1), getArg("worker", ""), getArg("howlong", -1))
								if request.path == "/api/affinities":
									return db.getAffinities()

							if request.path == "/api/jobs/users/":
								return db.getJobsUsers()

							if request.path == "/api/jobs/states/":
								return db.getJobsStates()

							if request.path == "/api/jobs/workers/":
								return db.getJobsWorkers()

							if request.path == "/api/jobs/priorities/":
								return db.getJobsPriorities()

							if request.path == "/api/jobs/affinities/":
								return db.getJobsAffinities()

							# REST POST API
							elif request.method == "POST":
								if request.path == "/api/jobs":
									db.editJobs(data)
									return 1
								if request.path == "/api/workers":
									db.editWorkers(data)
									return 1
								m = re.match(r"^/api/jobs/(\d+)/dependencies$", request.path)
								if m:
									db.setJobDependencies(int(m.group (1)), data)
									return 1
								if request.path == "/api/resetjobs":
									for jobId in data:
										db.resetJob(int(jobId))
									return 1
								if request.path == "/api/reseterrorjobs":
									for jobId in data:
										db.resetErrorJob(int(jobId))
									return 1
								if request.path == "/api/startjobs":
									for jobId in data:
										db.startJob(int(jobId))
									return 1
								if request.path == "/api/pausejobs":
									for jobId in data:
										db.pauseJob(int(jobId))
									return 1
								if request.path == "/api/stopworkers":
									for name in data:
										db.stopWorker(name)
									return 1
								if request.path == "/api/startworkers":
									for name in data:
										db.startWorker(name)
									return 1
								if request.path == "/api/affinities":
									db.setAffinities(data)
									return 1
								if request.path == "/api/terminateworkers":
									if servermode != "normal": # Cloud mode
										for name in data:
											db.cloudmanager.stopInstance(name)
											db._setWorkerState(name, "TERMINATED")
										return 1
									else:
										return None

							# REST DELETE API
							elif request.method == "DELETE":
								if request.path == "/api/jobs":
									for jobId in data:
										deletedJobs = []
										db.deleteJob(int(jobId), deletedJobs)
										for deleteJobId in deletedJobs:
											self.deleteLog(deleteJobId)
									return 1
								if request.path == "/api/workers":
									for name in data:
										db.deleteWorker(name)
									return 1

						result = api_rest ()
						if result != None:
							# Only JSON right now
							return json.dumps(result)
						else:
							# return server.NOT_DONE_YET
							request.setResponseCode(404)
							return "Web service not found."
					except LdapError as error:
						vprint(error)
						request.setResponseCode(http.UNAUTHORIZED)
			return "LDAP authorization required."

	def getLog (self, jobId):
		# Look for the job
		log = ""
		try:
			logFile = open (getLogFilename (jobId), "r")
			while (1):
				# Read some lines of logs
				line = logFile.readline()
				# "" means EOF
				if line == "":
					break
				log = log + line
			logFile.close ()
		except IOError:
			pass
		return log

	def deleteLog (self, jobId):
		# Look for the job
		try:
			os.remove (getLogFilename (jobId))
		except OSError:
			pass


class Workers(xmlrpc.XMLRPC):
	"""Unauthenticated XmlRPC server for Worker."""

	def render (self, request):
		with db:
			vprint ("[" + request.method + "] "+request.path)
			def getArg (name, default):
				value = request.args.get (name, [default])
				return value[0]

			if request.path == "/workers/heartbeat":
				return self.json_heartbeat (getArg ('hostname', ''), getArg ('jobId', '-1'), getArg ('log', ''), getArg ('load', '[0]'), getArg ('free_memory', '0'), getArg ('total_memory', '0'), request.getClientIP ())
			elif request.path == "/workers/pickjob":
				return self.json_pickjob (getArg ('hostname', ''), getArg ('load', '[0]'), getArg ('free_memory', '0'), getArg ('total_memory', '0'), request.getClientIP ())
			elif request.path == "/workers/endjob":
				return self.json_endjob (getArg ('hostname', ''), getArg ('jobId', '1'), getArg ('errorCode', '0'), request.getClientIP ())
			else:
				# return server.NOT_DONE_YET
				return xmlrpc.XMLRPC.render (self, request)

	def json_heartbeat (self, hostname, jobId, log, load, free_memory, total_memory, ip):
		result = db.heartbeat (hostname, int(jobId), load, int(free_memory), int(total_memory), str(ip))
		if log != "" :
			try:
				logFile = open (getLogFilename (jobId), "a")
				log = base64.decodestring(log)

				# Filter the log progression message
				progress = None
				job = db.getJob (int (jobId))
				progress_pattern = getattr (job, "progress_pattern", DefaultLocalProgressPattern)
				if progress_pattern != "":
					vprint ("progressPattern : \n" + str(progress_pattern))
					lp = None
					gp = None
					lFilter = getLogFilter (progress_pattern)
					log, lp = lFilter.filterLogs (log)
					if lp != None:
						vprint ("lp : "+ str(lp)+"\n")
						if lp != job['progress']:
							db.setJobProgress (int (jobId), lp)				
				logFile.write (log)
				if not result:
					logFile.write ("KillJob: server required worker to kill job.\n")
				logFile.close ()
			except IOError:
				vprint ("Error in logs")
		return result and "true" or "false"

	def json_pickjob (self, hostname, load, free_memory, total_memory, ip):
		return str (db.pickJob (hostname, load, int(free_memory), int(total_memory), str(ip)))

	def json_endjob (self, hostname, jobId, errorCode, ip):
		return str (db.endJob (hostname, int(jobId), int(errorCode), str(ip)))

GErr=0
GOk=0

# Go to the script directory
global installDir, dataDir
if sys.platform=="win32":
	import _winreg
	# under windows, uses the registry setup by the installer
	try:
		hKey = _winreg.OpenKey (_winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Mercenaries Engineering\\Coalition", 0, _winreg.KEY_READ)
		installDir, _type = _winreg.QueryValueEx (hKey, "Installdir")
		dataDir, _type = _winreg.QueryValueEx (hKey, "Datadir")
	except OSError:
		installDir = "."
		dataDir = "."
else:
	installDir = "."
	dataDir = "."
os.chdir (installDir)

# Create the logs/ directory
try:
	os.mkdir (dataDir + "/logs", 0755);
except OSError:
	pass

config = ConfigParser.SafeConfigParser()
config.read ("coalition.ini")

# Default config file values
if not config.has_section('server'):
	config.add_section("server")
if not config.has_option("server", "db_type"):
	config.set ("server", "db_type", "sqlite")

port = cfgInt ('port', 19211)

timeout = cfgInt ('timeout', 60)
verbose = cfgBool ('verbose', False)
service = cfgBool ('service', False)
notifyafter = cfgInt ('notifyafter', 10)
decreasepriorityafter = cfgInt ('decreasepriorityafter', 10)
smtpsender = cfgStr ('smtpsender', "")
smtphost = cfgStr ('smtphost', "")
smtpport = cfgInt ('smtpport', 587)
smtptls = cfgBool ('smtptls', True)
smtplogin = cfgStr ('smtplogin', "")
smtppasswd = cfgStr ('smtppasswd', "")

# LDAP and permissions
webfrontendrequest = True
LDAPServer = cfgStr ('ldaphost', "")
LDAPTemplateLogin = cfgStr ('ldaptemplatelogin', "")
_CmdWhiteList = cfgStr ('commandwhitelist', "")
GlobalCmdWhiteList = None
UserCmdWhiteList = {}
UserCmdWhiteListUser = None
for line in _CmdWhiteList.splitlines (False):
	_re = re.match ("^@(.*)", line)
	if _re:
		UserCmdWhiteListUser = _re.group(1)
		if not UserCmdWhiteListUser in UserCmdWhiteList:
			UserCmdWhiteList[UserCmdWhiteListUser] = []
	else:
		if UserCmdWhiteListUser:
			UserCmdWhiteList[UserCmdWhiteListUser].append (line)			
		else:
			if not GlobalCmdWhiteList:
				GlobalCmdWhiteList = []
			GlobalCmdWhiteList.append (line)

DefaultLocalProgressPattern = "PROGRESS:%percent"
DefaultGlobalProgressPattern = None

# Service only on Windows
service = service and sys.platform == "win32"

migratedb = False
resetdb = False
initdb = False

# Cloud mode
servermode = cfgStr ('servermode', 'normal')
if servermode != "normal":
	cloudconfig = ConfigParser.SafeConfigParser()
	if servermode == "aws":
		cloudconfig.read("cloud_aws.ini")
	elif servermode == "gcloud":
		cloudconfig.read("cloud_gcloud.ini")
	elif servermode == "qarnot_api":
		cloudconfig.read("cloud_qarnot.ini")
	cloudconfig.set("coalition", "port", str(port))
else:
	cloudconfig = None

# Parse the options
try:
	opts, args = getopt.getopt(sys.argv[1:], "hp:vcs", ["help", "port=",
		"verbose", "init", "migrate", "reset"])
	if len(args) != 0:
		usage()
		sys.exit(2)
except getopt.GetoptError, err:
	# print help information and exit:
	print str(err) # will print something like "option -a not recognized"
	usage()
	sys.exit(2)
for o, a in opts:
	if o in ("-h", "--help"):
		usage ()
		sys.exit(2)
	elif o in ("-v", "--verbose"):
		verbose = True
	elif o in ("-p", "--port"):
		port = int(a)
	elif o in ("--migrate"):
		migratedb = True
	elif o in ("--reset"):
		resetdb = True
	elif o in ("--init"):
		initdb = True
	else:
		assert False, "unhandled option " + o

	if LDAPServer != "":
		import ldap

if not verbose or service:
	try:
		outfile = open(dataDir + '/server.log', 'a')
		sys.stdout = outfile
		sys.stderr = outfile
		def _closeLogFile():
			outfile.close()
		atexit.register(_closeLogFile)
	except:
		pass

vprint ("[Init] --- Start ------------------------------------------------------------")
print ("[Init] "+time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(time.time ())))
if service:
	vprint ("[Init] Running service")
else:
	vprint ("[Init] Running standard console")

# Init the good database
if cfgStr ('db_type', 'sqlite') == "mysql":
	vprint ("[Init] Use mysql")
	db = DBMySQL (cfgStr ('db_mysql_host', "127.0.0.1"), cfgStr ('db_mysql_user', ""), cfgStr ('db_mysql_password', ""), cfgStr ('db_mysql_base', "base"), config=config, cloudconfig=cloudconfig)
else:
	vprint ("[Init] Use sqlite")
	db = DBSQLite (cfgStr ('db_sqlite_file', "coalition.db"), config=config, cloudconfig=cloudconfig)

db.NotifyError = notifyError
db.NotifyFinished = notifyFinished
db.Verbose = verbose

if initdb:
	vprint ("[Init] Initial database setup")
	if not db.initDatabase():
		exit(1)

if not len(db._getDatabaseTables()):
	db.initDatabase ()

with db:
	requires_migration = db.requiresMigration()
	if not migratedb and requires_migration:
		print(dedent("""
		Coalition cannot start since the database schema and the source code
		are not compatible. The database needs to be migrated. First the
		database should be backuped in case the migration fails. Then, the
		command 'coalition server.py --verbose --migrate' should be run.
		Another option is to install the previous version of coalition code
		that worked with the current database schema."""))
		exit(1)

	if migratedb and not requires_migration:
		print(dedent("""
		The database does not require migration, but the '--migrate' parameter was provided."""))
		exit(1)

	if requires_migration and migratedb:
		print(dedent("""
		Please consider doing a backup of the database first. Are you ready to proceed?"""))
		if _interactiveConfirmation("Yes, proceed to migration!"):
			success = db.migrateDatabase()
			if success:
				print("Database migration was successfull.")
				exit(0)
			else:
				print("A problem occured during the database migration.")
				exit(1)
		else:
			print("Database migration was cancelled by user.")
			exit(0)

	if resetdb:
		db.reset ()

LogFilterCache = {}


### Main manager ###

if sys.platform=="win32" and service:
	# Windows Service
	import win32serviceutil
	import win32service
	import win32event

	class WindowsService(win32serviceutil.ServiceFramework):
		_svc_name_ = "CoalitionServer"
		_svc_display_name_ = "Coalition Server"

		def __init__(self, args):
			vprint ("[Init] Service init")
			win32serviceutil.ServiceFramework.__init__(self, args)
			self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

		def SvcStop(self):
			vprint ("[Stop] Service stop")
			self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
			win32event.SetEvent(self.hWaitStop)

		def SvcDoRun(self):
			vprint ("[Run] Service running")
			import servicemanager
			self.CheckForQuit()
			main()
			vprint ("Service quitting")

		def CheckForQuit(self):
			vprint ("[Stop] Checking for quit...")
			retval = win32event.WaitForSingleObject(self.hWaitStop, 10)
			if not retval == win32event.WAIT_TIMEOUT:
				# Received Quit from Win32
				reactor.stop()

			reactor.callLater(1.0, self.CheckForQuit)

	if __name__=='__main__':
		win32serviceutil.HandleCommandLine(WindowsService)
else:
	# Simple server
	if __name__ == '__main__':
		main()

# vim: tabstop=4 noexpandtab shiftwidth=4 softtabstop=4 textwidth=79

