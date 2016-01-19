from twisted.web import xmlrpc, server, static, http
from twisted.internet import defer, reactor
import cPickle, time, os, getopt, sys, base64, re, thread, ConfigParser, random, shutil
import atexit, json
import smtplib
from email.mime.text import MIMEText

from db_sqlite import DBSQLite
from db_mysql import DBMySQL

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

global TimeOut, port, verbose, config
config = ConfigParser.SafeConfigParser()
config.read ("coalition.ini")

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

port = cfgInt ('port', 19211)
TimeOut = cfgInt ('timeout', 60)
verbose = cfgBool ('verbose', False)
service = cfgBool ('service', True)
notifyafter = cfgInt ('notifyafter', 10)
decreasepriorityafter = cfgInt ('decreasepriorityafter', 10)
smtpsender = cfgStr ('smtpsender', "")
smtphost = cfgStr ('smtphost', "")
smtpport = cfgInt ('smtpport', 587)
smtptls = cfgBool ('smtptls', True)
smtplogin = cfgStr ('smtplogin', "")
smtppasswd = cfgStr ('smtppasswd', "")

LDAPServer = cfgStr ('ldaphost', "")
LDAPTemplate = cfgStr ('ldaptemplate', "")

_TrustedUsers = cfgStr ('trustedusers', "")

TrustedUsers = {}
for line in _TrustedUsers.splitlines (False):
	TrustedUsers[line] = True

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

def usage():
	print ("Usage: server [OPTIONS]")
	print ("Start a Coalition server.\n")
	print ("Options:")
	print ("  -h, --help\t\tShow this help")
	print ("  -p, --port=PORT\tPort used by the server (default: "+str(port)+")")
	print ("  -v, --verbose\t\tIncrease verbosity")
	if sys.platform == "win32":	
		print ("  -c, --console=\t\tRun as a windows console application")
		print ("  -s, --service=\t\tRun as a windows service")
	print ("\nExample : server -p 1234")

# Service only on Windows
service = service and sys.platform == "win32"

# Parse the options
try:
	opts, args = getopt.getopt(sys.argv[1:], "hp:vcs", ["help", "port=", "verbose"])
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
	else:
		assert False, "unhandled option " + o

	if LDAPServer != "":
		import ldap

if not verbose or service:
	try:
		outfile = open(dataDir + '/server.log', 'a')
		sys.stdout = outfile
		sys.stderr = outfile
		def exit ():
			outfile.close ()
		atexit.register (exit)
	except:
		pass


# Log function
def vprint (str):
	if verbose:
		print (str)
		sys.stdout.flush()

vprint ("[Init] --- Start ------------------------------------------------------------")
print ("[Init] "+time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(time.time ())))

# Init the good database
if cfgStr ('db_type', 'sqlite') == "mysql":
	vprint ("[Init] Use mysql")
	db = DBMySQL (cfgStr ('db_mysql_host', "127.0.0.1"), cfgStr ('db_mysql_user', ""), cfgStr ('db_mysql_password', ""), cfgStr ('db_mysql_base', "base"))
else:
	vprint ("[Init] Use sqlite")
	db = DBSQLite (cfgStr ('db_sqlite_file', "coalition.db"))

if service:
	vprint ("[Init] Running service")
else:
	vprint ("[Init] Running standard console")

def getLogFilename (jobId):
	global dataDir
	return dataDir + "/logs/" + str(jobId) + ".log"

# strip all 
def strToInt (s):
	try:
		return int(s)
	except:
		return 0

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
		return self.RE.sub ("", log), progress
		#return log, progress
		
LogFilterCache = {}

def getLogFilter (pattern):
	"""Get the pattern filter from the cache or add one"""
	global LogFilterCache
	try:	
		filter = LogFilterCache[pattern]
	except KeyError:
		filter = LogFilter (pattern)
		LogFilterCache[pattern] = filter
	return filter

def compareJobs (self, other):
	if self.priority < other.priority:
		return 1
	if self.priority > other.priority:
		return -1
	if self.id > other.id:
		return 1
	if self.id < other.id:
		return -1
	return 0

def compareAffinities (jobAffinity, workerAffinity):
	# check for job with no affinity -- always success
	if jobAffinity == "" :
		return True
	# check for worker with no affinity -- always failure unless no affinity
	if workerAffinity == "" :
		return False
	jobWords = jobAffinity.split (',')

	workerWords = workerAffinity.split (',')
	for jobWord in jobWords:
		found = False
		for workerWord in workerWords:
			if workerWord == jobWord:
				found = True
		if not found:
			return False
	return True

def writeJobLog (jobId, log):
	logFile = open (getLogFilename (jobId), "a")
	logFile.write (log)
	logFile.close ()	
			
# State of the master
# Rules for picking a job:
# If the job has children, they must be finished before
# If no child can be ran (exceeded retries count), then the job cannot be ran
# Children are picked according to their priority
DBVersion = 8
class CState:

	def __init__ (self):
		self.clear ()

	# Clear the whole database
	def clear (self) :
		self._ActiveJobs = set ()
		self._Affinities = {}			# dynamic affinity, job affinity concatened to the children jobs affinity

	def update (self) :
		global	TimeOut
		_time = time.time ()
		for id in State._ActiveJobs.copy () :
			job = db.getJob (id)
			if job.state == "WORKING" and job.command != "":	# Don't update timeout if it is a folder job
				if _time - job.ping_time > TimeOut :
					# Job times out, no heartbeat received for too long
					vprint ("Job " + str(job.id) + " is AWOL")
					self.updateJobState (id, "ERROR")
					self.updateWorkerState (State.getWorker (job.worker), "TIMEOUT")
					writeJobLog (job.id, "SERVER: Worker "+job.worker+" doesn't respond, timeout.")
				elif job.timeout > 0 and _time - job.start_time > job.timeout:
					# job exceeded run time
					vprint ("Job " + str(job.id) + " timeout, exceeded run time")
					self.updateJobState (id, "ERROR")
					self.updateWorkerState (State.getWorker (job.worker), "ERROR")
					writeJobLog (job.id, "SERVER: Job " + str(job.id) + " timeout, exceeded run time")
				if not job.hasChildren () :
					job.duration = _time - job.start_time
					try:
						worker = State.getWorker (job.worker)
						if worker.current_event != -1:
							activity = db.getEvent (worker.current_event)
							if activity.job_id == job.id:
								activity.duration = job.duration
					except KeyError:
						pass
		# Timeout workers
		workers = db.getWorkers ()
		for worker in workers:
			if worker.state != "TIMEOUT" and _time - worker.ping_time > TimeOut:
				self.updateWorkerState (worker, "TIMEOUT")

	# -----------------------------------------------------------------------
	# job handling

	# Is job dependent on another
	def doesJobDependOn (self, id0, id1):
		if id0 == id1:
			return True
		try:
			job0 = db.getJobs (id0)
			dependencies = job0.getDependencies ()
			for dep in dependencies:
				if self.doesJobDependOn (dep.id, id1):
					return True
		except KeyError:
			pass
		return False

	# Find a job by its title
	'''	def findJobByTitle (self, title):
		for id, job in self.Jobs.iteritems ():
			if job.title == title:
				return id'''

	# Find a job by its path, job path atoms are separated by pipe '|'
	'''	def findJobByPath (self, path):
		job = db.getRoot ()
		atoms = re.findall ('([^|]+)', path)
		for atom in atoms :
			found = False
			for id in job.Children :
				try :
					child = db.getJob (id)
					if child.title == atom :
						job = child
						found = True
						break
				except KeyError:
					pass
			if not found :
				return None
		return job.id'''

	# Add a job
	def newJob (self, parent, title, command, dir, environment, state, priority, retry, timeout, affinity, 
		user, dependencies, progress_pattern, url):
		try:
			job = db.newJob (
			parent, title, command, dir, environment, state, "", int(time.time()), 0, int(time.time()), 0, retry, timeout, priority,
			affinity, user, 0, 0, 0, 0, 0, 0, 0, url, 0, progress_pattern)
			db.setJobDependencies (job.id, dependencies)

			if job.id != 0:
				job.parent = parent
				self._updateAffinity (job.id)
				self._updateParentState (parent)
			return job.id

		except KeyError:
			print ("Can't add job to parent " + str (parent) + " type", type (parent))

	# Remove a job
	def removeJob (self, id, updateParentState = True):
		if id != 0:
			try:
				job = db.getJob (id)
				# remove children first
				children = db.getJobChildren (job.id)
				for child in children:
					self.removeJob (child.id)
				# remove self from parent
				parentId = job.parent
				# and unmap
				try:
					db.removeJob (id)
				except KeyError:
					pass
				try:
					del self._Affinities[id]
				except KeyError:
					pass
				try:
					self._ActiveJobs.remove (id)
				except KeyError:
					pass
				# only update parent's state when required (for instance in removeChildren, it is done after removing all children)
				if updateParentState:
					self._updateParentState (parentId)
			except KeyError:
				pass

	# Remove children jobs
	def removeChildren (self, id) :
		job = db.getJob (id)
		children = db.getJobChildren (job.id)
		for child in children:
			self.removeJob (child.id, False)
		self._updateParentState (id)

	# Change job affinity
	def setAffinity (self, id, affinity) :
		try:
			job = db.getJob (id)
			job.affinity = affinity
			self._updateParentState (id)
		except:
			pass

	# Reset a job
	def resetJob (self, id) :
		try:
			job = db.getJob (id)
			job.state = "WAITING"
			job.run_done = 0
			job.worker = ""
			if getattr(job, "progress", False):
				job.progress = 0
			try:
				self._ActiveJobs.remove (id)
			except KeyError:
				pass
			self._updateParentState (job.parent)
			children = db.getJobChildren (job.id)
			for child in children:
				self.resetJob (child.id)

			# Clear the logs
			try:
				os.unlink (getLogFilename (id))
			except OSError:
				pass

		except KeyError:
			pass

	# Reset a job and its error children
	def resetErrorJob (self, id) :
		try:
			job = db.getJob (id)
			job.state = "WAITING"
			job.run_done = 0
			job.worker = ""
			if getattr(job, "progress", False):
				job.progress = 0
			try:
				self._ActiveJobs.remove (id)
			except KeyError:
				pass
			self._updateParentState (job.parent)
			children = db.getJobChildren (job.id)
			for child in children:
				if child.state == "ERROR":
					self.resetErrorJob (child.id)
		except KeyError:
			pass

	# Reset a job
	def startJob (self, id) :
		try:
			job = db.getJob (id)
			job.state = "WAITING"
			job.run_done = 0
			job.worker = ""
			if getattr(job, "progress", False):
				job.progress = 0
			try:
				self._ActiveJobs.remove (id)
			except KeyError:
				pass
			self._updateParentState (id)
		except KeyError:
			pass

	# Start a paused job
	def startJob (self, id) :
		try:
			job = db.getJob (id)
			if job.state == "PAUSED" :
				job.state = "WAITING"
				self._updateParentState (id)
		except KeyError:
			pass

	# Pause a job
	def pauseJob (self, id) :
		try:
			job = db.getJob (id)
			job.state = "PAUSED"
			try:
				self._ActiveJobs.remove (id)
			except KeyError:
				pass
			self._updateParentState (id)
		except KeyError:
			pass

	# Move a job
	def moveJob (self, id, dest) :
		try:
			if id != dest:
				job = db.getJob (id)
				oldParentID = job.parent
				job.parent = dest
				self._updateParentState (dest)
				self._updateParentState (oldParentID)
		except KeyError:
			vprint ("moveJob key error")
			pass

	# Can be executed
	def canExecute (self, id) :
		# Root
		if id == 0:
			return False
		job = db.getJob (id)

		# Don't execute a finished job or a working job
		if job.state == "FINISHED" or job.state == "PAUSED" :
			return False

		# Waiting jobs can be executed only if all dependencies are finished
		# Error jobs can be ran only if they have no children and tries left
		dependencies = job.getDependencies ()
		for dep in dependencies:
			if dep.state != "FINISHED" :
				return False

		# Visit parents, or waiting jobs or error jobs with enough retry
		hasChildren = job.hasChildren ()
		return hasChildren or (not hasChildren and (job.state == "WAITING" or (job.state == "ERROR" and job.run_done < job.retry)))

	# Can be executed
	def compatibleAffinities (self, jobAffinity, workerAffinity) :
		job = frozenset (re.findall ('([^,]+)', jobAffinity))
		worker = frozenset (re.findall ('([^,]+)', workerAffinity))
		if worker >= job:
			return True
		return False
		
	def pickJob (self, id, affinity) :
		job = db.getJob (id)
		nextChild = None
		nextJobID = None

		# Look for the next job
		allFinished = True
		children = db.getJobChildren (job.id)
		for child in children:
			if child.state != "FINISHED" :
				allFinished = False
			# if job can be executed and worker affinity is compatible, add this job as a potential one
			if self.canExecute (child.id):
				if self.compatibleAffinities (child.affinity, affinity):
					#vprint ("++ worker "+str (affinity)+" compatible with job "+str (child.id)+" "+str (self._Affinities[child.id]))
					if nextChild == None or child.priority > nextChild.priority or (child.priority == nextChild.priority and (child.total_working+child.total_finished < nextChild.total_working+nextChild.total_finished)) :
						tryJobId = None
						if child.hasChildren () :
							tryJobId = self.pickJob (child.id, affinity)
						else :
							tryJobId = child.id
						if tryJobId != None:
							nextChild = child
							nextJobID = tryJobId
		return nextJobID

	# Update job state
	def updateJobState (self, id, state) :
		global GErr, GOk
		if state == "ERROR" :
			GErr += 1
		if state == "FINISHED" :
			GOk += 1
		try :
			job = db.getJob (id)
			if job.state != state :
				job.state = state
				
				# Update the event
				activity = None
				try :
					worker = self.getWorker (job.worker)
					if worker.current_event != -1:
						activity = db.getEvent (worker.current_event)
						if activity.job_id == id:
							activity.state = state
				except KeyError:
					pass
				
				if state == "WORKING" :
					job.run_done += 1
					job.start_time = time.time ()
					self._ActiveJobs.add (id)
				elif state == "ERROR" or state == "FINISHED":
					if state == "ERROR" :
						job.priority = max (job.priority-1, 0)
						notifyError (job)
					if state == "FINISHED" :
						notifyFinished (job)
						job.progress = 1
					if not job.hasChildren () :
						_time = time.time()
						job.duration = _time - job.start_time
						if activity:
							activity.duration = job.duration
					try:
						self._ActiveJobs.remove (id)
					except KeyError:
						pass
				self._updateParentState (job.parent)
		except KeyError:
			pass

	# Update parent state
	def _updateParentState (self, id) :
		if id == 0 :
			return																																			
		try:
			job = db.getJob (id)
			jobsToDo = False
			hasError = False
			total = 0
			total_finished = 0
			total_errors = 0
			total_working = 0
			finished = 0
			errors = 0
			working = 0
			durationAvg = 0;
			durationCount = 0;
			children = db.getJobChildren (job.id)
			for child in children:
				if self.canExecute (child.id):
					jobsToDo = True
				state = child.state
				if child.hasChildren () :
					total += child.total or 0
					total_errors += child.total_errors or 0
					total_finished += child.total_finished or 0
					total_working += child.total_working or 0
					durationAvg += child.duration * child.total;
					durationCount += child.total;
				else :
					total += 1
					if state == "ERROR":
						errors += 1
					elif state == "FINISHED":
						finished += 1
					elif state == "WORKING":
						working += 1
					durationAvg += child.duration;
					durationCount += 1;
			if durationCount > 0 :
				durationAvg /= durationCount
			else :
				durationAvg = 0
			total_errors += errors
			total_finished += finished
			total_working += working

			# If this parent job has finished the notifyafter first jobs, notify the user
			if job.finished < notifyafter and finished >= notifyafter :
				notifyFirstFinished (job)

			# If this parent job has finished the notifyafter first jobs, notify the user
			if job.errors < decreasepriorityafter and errors >= decreasepriorityafter :
				job.priority = max (job.priority-1, 0)

			job.finished = finished
			job.errors = errors
			job.working = working
			job.total = total
			job.total_errors = total_errors
			job.total_finished = total_finished
			job.total_working = total_working
			job.duration = durationAvg
			if job.total > 0:
				job.progress = float (total_finished)/float (total)
			
			# New job state
			newState = "WAITING"
			if job.total_working > 0 :
				newState = "WORKING"
			elif job.total_errors > 0 :
				newState = "ERROR"
			elif job.total > 0 and job.total == job.total_finished :
				newState = "FINISHED"
			
			if job.state != "PAUSED" and newState != job.state:
				if newState == "FINISHED" :
					notifyFinished (job)
				if newState == "ERROR" :
					notifyError (job)
				job.state = newState
			self._updateAffinity (id)
			self._updateParentState (job.parent)
		except KeyError:
			pass

	# Update job affinity
	def _updateAffinity (self, id) :
		job = db.getJob (id)
		self._Affinities[id] = frozenset (re.findall ('([^,]+)', job.affinity))

	# -----------------------------------------------------------------------
	# worker handling

	# get a worker
	def getWorker (self, name) :
		worker = db.getWorker (name)
		if worker:
			worker.ping_time = time.time()
			return worker
		else:
			# Worker not found, add it
			db.newWorker (name, int(time.time()))
			worker = db.getWorker (name)
			return worker

	def stopWorker (self, name):
		worker = db.getWorker (name)
		worker.active = False

		# Try to stop the worker's jobs
		job = db.getJob (worker.last_job)
		if job and job.worker == name and job.state == "WORKING":
			job.state = "WAITING"

	def startWorker (self, name):
		worker = db.getWorker (name)
		worker.active = True

	def updateWorkerState (self, worker, state) :
		try:
			if state != worker.state:
				if state == "ERROR" :
					worker.error += 1
					worker.state = "WAITING"
				elif state == "FINISHED" :
					worker.finished += 1
					worker.state = "WAITING"
				elif state == "TIMEOUT" :
					worker.error += 1
					worker.state = "WAITING"
				else:
					worker.state = state
		except KeyError:
			pass

	# -----------------------------------------------------------------------
	# debug/dump

	def dump (self) :
		def dumpJob (id, depth) :
			try:
				job = db.getJob (id)
				print (" "*(depth*2)) + str (job.id) + " " + job.title + " " + job.state + " cmd='" + job.dir + "/" + job.command + "' prio=" + str (job.priority) + " retry=" + str (job.run_done) + "/" + str (job.retry)
				try:
					dyn = self._Affinities[id]
					print (" "*(depth*2+1)), "Dyn:", dyn
				except:
					pass
				children = db.getJobChildren (job.id)
				for child in children:
					dumpJob (child.id, depth+1)
			except KeyError:
				print (" "*(depth*2)) + "<<< Unknown job " + str (id) + " >>>"
		dumpJob (0, 0)

State = CState()



# Authenticate the user
def authenticate (request):
	if LDAPServer != "":
		username = request.getUser ()
		password = request.getPassword ()
		if username in TrustedUsers:
			vprint (username + " in the clearance list")
			vprint ("Authentication OK")
			return True
		if username != "" or password != "":
			l = ldap.open(LDAPServer)
			vprint ("Authenticate "+username+" with LDAP")
			username = LDAPTemplate.replace ("__login__", username)
			try:
				if l.bind_s(username, password, ldap.AUTH_SIMPLE):
					vprint ("Authentication OK")
					return True
			except ldap.LDAPError:
				vprint ("Authentication Failed")
				pass
		else:
			vprint ("Authentication Required")
		request.setHeader ("WWW-Authenticate", "Basic realm=\"Coalition Login\"")
		request.setResponseCode(http.UNAUTHORIZED)
		return False
	return True

# Check if the user can add this command
def grantAddJob (user, cmd):

	def checkWhiteList (wl):
		for pattern in wl:
			if (re.match (pattern, cmd)):
				return True
		else:
			vprint ("user '" + user + "' is not allowed to run the command '" + cmd + "'")
		return False

	# user defined white list ?		
	if user in UserCmdWhiteList:
		wl = UserCmdWhiteList[user]
		if checkWhiteList (wl):
			return True

		# If in the global command white list
		if GlobalCmdWhiteList:
			if checkWhiteList (GlobalCmdWhiteList):
				return True
		return False

	else:
		# If in the global command white list
		if GlobalCmdWhiteList:
			if not checkWhiteList (GlobalCmdWhiteList):
				return False
	
	# Cleared
	return True

class Root (static.File):
	def __init__ (self, path, defaultType='text/html', ignoredExts=(), registry=None, allowExt=0):
		static.File.__init__(self, path, defaultType, ignoredExts, registry, allowExt)

	def render (self, request):
		if authenticate (request):
			return static.File.render (self, request)
		return 'Authorization required!'

class Master (xmlrpc.XMLRPC):
	"""    """

	user = ""

	def render (self, request):
		with db:
			vprint ("[" + request.method + "] "+request.path)
			global State
			if authenticate (request):
				# If not autenticated, user == ""
				self.user = request.getUser ()
				# Addjob

				def getArg (name, default):
					value = request.args.get (name, [default])
					return value[0]

				# The legacy method for compatibility
				if request.path == "/xmlrpc/addjob":

					parent = getArg ("parent", "0")
					title = getArg ("title", "New job")
					cmd = getArg ("cmd", getArg ("command", ""))
					dir = getArg ("dir", ".")
					environment = getArg ("env", None)
					if environment == "":
						environment = None
					priority = getArg ("priority", "1000")
					retry = getArg ("retry", "10")
					timeout = getArg ("timeout", "0")
					affinity = getArg ("affinity", "")
					dependencies = getArg ("dependencies", "")
					progress_pattern = getArg ("localprogress", "")
					url = getArg ("url", "")
					user = getArg ("user", "")
					if self.user != "":
						user = self.user

					if grantAddJob (self.user, cmd):
						vprint ("Add job : " + cmd)
						if isinstance (parent, str):
							try:
								# try as an int
								parent = int (parent)
							except ValueError:
								bypath = db.findJobByPath (parent)
								if bypath:
									parent = bypath
								else:
									parenttitle = parent
									parent = db.findJobByTitle (parent)
									if parent == None:
										print ("Error : can't find job " + str (parenttitle))
										return -1
						if type(dependencies) is str:
							# Parse the dependencies string
							dependencies = re.findall ('(\d+)', dependencies)
						for i, dep in enumerate (dependencies) :
							dependencies[i] = int (dep)
					
						id = State.newJob (parent, str (title), str (cmd), str (dir), str (environment), "WAITING", int (priority), int (retry), int (timeout), str (affinity), str (user), dependencies, progress_pattern, url)

						State.update ()
						return str(id)
					else:
						return -1
				else:
					value = request.content.getvalue()
					if request.method != "GET":
						data = value and json.loads(request.content.getvalue()) or {}
						if verbose:
							vprint ("[Content] "+repr(data))
					else:
						if verbose:
							vprint ("[Content] "+repr(request.args))

					def getArg (name, default):
						if request.method == "GET":
							# GET params
							value = request.args.get (name, [default])[0]
							value = type(default)(default if value == None else value)
							assert (value != None)
							return value
						else:
							# JSON params
							value = data.get (name)
							value = type(default)(default if value == None else value)
							assert (value != None)
							return value

					# REST api
					def api_rest ():
						if request.method == "PUT":
							if request.path == "/api/jobs":
								jod_id = State.newJob ((getArg ("parent",0)), (getArg("title","")), (getArg("command","")), (getArg("dir","")), (getArg("environment","")), 
									(getArg("state","WAITING")),	(getArg("priority",1000)), (getArg("retry",1000)), (getArg("timeout",1000)), (getArg("affinity", "")), 
									(getArg("user", "")), getArg("dependencies", []), (getArg("progress_pattern", "")), (getArg("url", "")))
								State.update ()
								return jod_id

						elif request.method == "GET":
							m = re.match(r"^/api/jobs/(\d+)$", request.path)
							if m:
								return self.getJob (int(m.group (1)))

							m = re.match(r"^/api/jobs/(\d+)/children$", request.path)
							if m:
								return self.getJobChildren (int(m.group (1)))

							m = re.match(r"^/api/jobs/(\d+)/dependencies$", request.path)
							if m:
								return self.getJobDependencies (int(m.group (1)))

							m = re.match(r"^/api/jobs/(\d+)/log$", request.path)
							if m:
								return self.getLog (int(m.group (1)))

							if request.path == "/api/workers":
								return self.getWorkers ()

							if request.path == "/api/events":
								return self.getEvents (getArg ("job", -1), getArg ("worker", ""), getArg ("howlong", -1))

						elif request.method == "POST":
							if request.path == "/api/jobs":
								db.edit (data, {}, {})
								return 1

							if request.path == "/api/workers":
								db.edit ({}, data, {})
								return 1

							m = re.match(r"^/api/jobs/(\d+)/dependencies$", request.path)
							if m:
								db.setJobDependencies (int(m.group (1)), data)
								return 1

							if request.path == "/api/clearjobs":
								return self.clearJobs (data)

							if request.path == "/api/resetjobs":
								return self.resetJobs (data)

							if request.path == "/api/reseterrorjobs":
								return self.resetErrorJobs (data)

							if request.path == "/api/startjobs":
								return self.startJobs (data)

							if request.path == "/api/pausejobs":
								return self.pauseJobs (data)

							if request.path == "/api/clearworkers":
								return self.clearWorkers (data)

							if request.path == "/api/stopworkers":
								return self.stopWorkers (data)

							if request.path == "/api/startworkers":
								return self.startWorkers (data)

					result = api_rest ()
					if result != None:
						# Only JSON right now
						return json.dumps (result)
					else:
						# return server.NOT_DONE_YET
						request.setResponseCode(404)
						return "Web service not found"
			return 'Authorization required!'

	def getJob (self, id):
		job = db.getJob (id)
		if job:
			d = job.__dict__.copy ()
			del d['db']
			del d['_Job__initialized']
			return d

	def getJobChildren (self, id):
		jobs = db.getJobChildren (id)
		r = []
		for job in jobs:
			d = job.__dict__.copy ()
			del d['db']
			del d['_Job__initialized']
			r.append (d)
		return r

	def getJobDependencies (self, id):
		jobs = db.getJobDependencies (id)
		r = []
		for job in jobs:
			d = job.__dict__.copy ()
			del d['db']
			del d['_Job__initialized']
			r.append (d)
		return r

	def clearJobs (self, ids):
		global State
		for jobId in ids:
			State.removeJob (int(jobId))
		State.update ()
		return "1"

	def resetJobs (self, ids):
		global State
		for jobId in ids:
			State.resetJob (int(jobId))
		State.update ()
		return "1"

	def resetErrorJobs (self, ids):
		global State
		for jobId in ids:
			State.resetErrorJob (int(jobId))
		State.update ()
		return "1"

	def startJobs (self, ids):
		global State
		for jobId in ids:
			State.startJob (int(jobId))
		State.update ()
		return "1"

	def pauseJobs (self, ids):
		global State
		for jobId in ids:
			State.pauseJob (int(jobId))
		State.update ()
		return "1"

	def getLog (self, jobId):
		global State
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

	def getWorkers (self):
		workers = db.getWorkers ()
		r = []
		for worker in workers:
			d = worker.__dict__.copy ()
			del d['db']
			del d['_Worker__initialized']
			r.append (d)
		return r

	def clearWorkers (self, names):
		global State
		for name in names:
			DBClearWorkers ()
		State.update ()
		return "1"

	def stopWorkers (self, names):
		global State
		for name in names:
			State.stopWorker (name)
		State.update ()
		return "1"

	def startWorkers (self, names):
		global State
		for name in names:
			State.startWorker (name)
		State.update ()
		return "1"

	def getEvents (self, job, worker, howlong):
		events = db.getEvents (job, worker, howlong)
		r = []
		for event in events:
			d = event.__dict__.copy ()
			del d['db']
			del d['_Event__initialized']
			r.append (d)
		return r

# Unauthenticated connection for workers
class Workers(xmlrpc.XMLRPC):
	"""    """

	def render (self, request):
		with db:
			global State

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
		"""Get infos from the workers."""
		global State
		_time = time.time ()
		vprint ("Heart beat for " + str(jobId) + " " + str(load))
		# Update the worker load and ping time
		worker = State.getWorker (hostname)
		worker.cpu = load
		worker.free_memory = int(free_memory)
		worker.total_memory = int(total_memory)
		worker.ip = str(ip)
		workingJob = None
		jobId = int(jobId)
		try :
			job = db.getJob (jobId)
			if job.state == "WORKING" and job.worker == hostname :
				State.updateWorkerState (worker, "WORKING")
				workingJob = job
				job.ping_time = _time
				if log != "" :
					try:
						logFile = open (getLogFilename (jobId), "a")
						log = base64.decodestring(log)
						
						# Filter the log progression message
						progress = None
						progress_pattern = getattr(job, "progress_pattern", DefaultLocalProgressPattern)
						if progress_pattern != "":
							vprint ("progressPattern : \n" + str(progress_pattern))
							lp = None
							gp = None
							lFilter = getLogFilter (progress_pattern)
							log, lp = lFilter.filterLogs (log)
							if lp != None:
								vprint ("lp : "+ str(lp)+"\n")
								job.progress = lp
						
						logFile.write (log)
						logFile.close ()
					except IOError:
						vprint ("Error in logs")
		except KeyError:
			pass
		State.update ()
		if worker.state == "WORKING" and workingJob != None and workingJob.state == "WORKING":
			return "true"
		# Stop
		vprint ("Error at " + hostname + " heartbeat, set to WAITING")
		State.updateWorkerState (worker, "WAITING")
		if workingJob:
			State.updateJobState (jobId, "WAITING")
		return "false"

	def json_pickjob (self, hostname, load, free_memory, total_memory, ip):
		"""A worker ask for a job."""
		global State
		vprint (hostname + " wants some job" + " " + load)
		worker = State.getWorker (hostname)
		worker.cpu = load
		worker.free_memory = int(free_memory)
		worker.total_memory = int(total_memory)
		worker.ip = str(ip)
		if not worker.active:
			State.updateWorkerState (worker, "WAITING")
			return '-1,"","","",None'
#		affinity = frozenset (re.findall ('([^,]+)', worker.affinity))
		jobId = State.pickJob (0, worker.affinity)
		if jobId != None :
			job = db.getJob (jobId)
			if job.state == "FINISHED":
				vprint (hostname + " picked a finished job!")
			job.worker = hostname
			job.ping_time = time.time()
			job.start_time = job.ping_time
			job.duration = 0
			State.updateJobState (jobId, "WORKING")
			worker.last_job = job.id
			worker.ping_time = job.ping_time
			State.updateWorkerState (worker, "WORKING")
			State.update ()
			vprint (hostname + " picked job " + str (jobId) + " " + worker.state)
			
			# Create the event
			event = db.newEvent (hostname, job.id, job.title, 'WORKING', int(time.time()), 0)
			worker.current_event = event.id

			if job.user != None and job.user != "":
				return repr (job.id)+","+repr (job.command)+","+repr (job.dir)+","+repr (job.user)+","+repr (job.environment)
			else:
				return repr (job.id)+","+repr (job.command)+","+repr (job.dir)+","+'""'+","+repr (job.environment)

		State.updateWorkerState (worker, "WAITING")
		State.update ()
		return '-1,"","","",None'

	def json_endjob (self, hostname, jobId, errorCode, ip):
		"""A worker finished a job."""
		global State
		worker = State.getWorker (hostname)
		worker.ip = str(ip)
		vprint ("End job " + str(jobId) + " with code " + str (errorCode))
		jobId = int(jobId)
		errorCode = int(errorCode)
		try:
			job = db.getJob (jobId)
			if job.state == "WORKING" and job.worker == hostname :
				result = "FINISHED"
				if errorCode != 0 :
					result = "ERROR"
				State.updateJobState (jobId, result)
				State.updateWorkerState (worker, result)
		except KeyError:
			pass
		State.update ()
		return "1"

# Listen to an UDP socket to respond to the workers broadcast
def listenUDP():
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
	# Start the UDP server used for the broadcast
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
	if job.user :
		sendEmail (job.user, 'ERRORS in job ' + job.title + ' (' + str(job.id) + ').')

def notifyFinished (job):
	if job.user :
		sendEmail (job.user, 'The job ' + job.title + ' (' + str(job.id) + ') is FINISHED.')

def notifyFirstFinished (job):
	if job.user :
		sendEmail (job.user, 'The job ' + job.title + ' (' + str(job.id) + ') has finished ' + str(notifyafter) + ' jobs.')

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

