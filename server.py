
from twisted.web import xmlrpc, server, static, http
from twisted.internet import defer, reactor
import pickle, time, os, getopt, sys, base64, re, thread, ConfigParser

# This module is standard in Python 2.2, otherwise get it from
#   http://www.pythonware.com/products/xmlrpc/
import xmlrpclib

# Go to the script directory
global installDir, dataDir
if sys.platform=="win32":
	import _winreg
	# under windows, uses the registry setup by the installer
	hKey = _winreg.OpenKey (_winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Mercenaries Engineering\\Coalition", 0, _winreg.KEY_READ)
	installDir, _type = _winreg.QueryValueEx (hKey, "Installdir")
	dataDir, _type = _winreg.QueryValueEx (hKey, "Datadir")
else:
	installDir = "."
	dataDir = "."
os.chdir (installDir)

# Create the logs/ directory
try:
	os.mkdir (dataDir + "/logs", 755);
except OSError:
	pass

global TimeOut, port, verbose, config
config = ConfigParser.SafeConfigParser()
config.read ("coalition.ini")
TimeOut = 10
port = 19211
if config.has_option('server', 'port'):
	try:
		port = int (config.get('server', 'port'))
	except ValueError:
		pass
verbose = False
LDAPServer = ""
LDAPTemplate = ""
JobId2StateId = {}

def usage():
	print ("Usage: server [OPTIONS]")
	print ("Start a Coalition server.\n")
	print ("Options:")
	print ("  -h, --help\t\tShow this help")
	print ("  -p, --port=PORT\tPort used by the server (default: "+str(port)+")")
	print ("  -v, --verbose\t\tIncrease verbosity")
	print ("  --ldaphost=HOSTNAME\tLDAP server to use for authentication")
	print ("  --ldaptemplate=TEMPLATE\tLDAP template used to validate the user, like uid=%login,ou=people,dc=exemple,dc=com")
	print ("\nExample : server -p 1234")

if sys.platform!="win32":
	# Parse the options
	try:
		opts, args = getopt.getopt(sys.argv[1:], "hp:v", ["help", "port=", "verbose", "ldaphost=", "ldaptemplate="])
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
			port = float(a)
		elif o in ("-lh", "--ldaphost"):
			LDAPServer = a
		elif o in ("-lt", "--ldaptemplate"):
			LDAPTemplate = a
		else:
			assert False, "unhandled option " + o

	if LDAPServer != "":
		import ldap

# Log function
def output (str):
	if verbose:
		print (str)

def getLogFilename (jobId):
	global dataDir
	return dataDir + "/logs/" + str(jobId) + ".log"

# strip all 
def strToInt (s):
	try:
		return int(s)
	except:
		return 0

class Job:
	"""A farm job"""

	def __init__ (self, id, title, cmd, dir, priority, retry, affinity, user, dependencies):
		self.ID = id				# Jod ID
		self.Title = title			# Job title
		self.Command = cmd			# Job command to execute
		self.Dir = dir				# Jod working directory
		self.State = "WAITING"			# Job state, can be WAITING, WORKING, FINISHED or ERROR
		self.Worker = ""			# Worker hostname
		self.StartTime = time.time()		# Start working time 
		self.Duration = 0			# Duration of the process
		self.PingTime = self.StartTime		# Last worker ping time
		self.Try = 0				# Number of try
		self.Retry = strToInt (retry)		# Number of try max
		self.Priority = strToInt (priority)	# Job priority
		self.Affinity = affinity		# Job affinity
		self.User = user			# Job user
		self.Order = 0				# Job order
		self.Dependencies = dependencies	# Job dependencies

def compareJobs (self, other):
	if self.Priority < other.Priority:
		return 1
	if self.Priority > other.Priority:
		return -1
	if self.ID > other.ID:
		return 1
	if self.ID < other.ID:
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

class Worker:
	"""A farm worker"""

	def __init__ (self, name):
		self.Name = name			# Worker name
		self.Affinity = ""			# Worker affinity
		self.State = "WAITING"			# Job state, can be WAITING, WORKING, FINISHED or TIMEOUT
		self.PingTime = time.time()		# Last worker ping time
		self.Finished = 0			# Number of finished
		self.Error = 0				# Number of fault
		self.LastJob = -1			# Last job done
		self.Load = 0				# Load of the worker
		self.Active = True				# Is the worker enabled

# State of the master
DBVersion = 4
class CState:

	Counter = 0
	Jobs = []
	Workers = []

	# Read the state
	def read (self, fo):
		version = pickle.load(fo)
		if version == DBVersion:
			self.Counter = pickle.load(fo)
			self.Jobs = pickle.load(fo)
			self.Workers = pickle.load(fo)
		else:
			raise Exception ("Database too old, erase the master_db file")
			self.Jobs = []
			self.Workers = []

	# Write the state
	def write (self, fo):
		version = DBVersion
		pickle.dump(version, fo)
		pickle.dump(self.Counter, fo)
		pickle.dump(self.Jobs, fo)
		pickle.dump(self.Workers, fo)

	def doesJobDependOn (self, id0, id1):
		global JobId2StateId
		if id0 == id1:
			return True
		try:
			_job0 = JobId2StateId[id0]
			job0 = self.Jobs[_job0]
			for i in job0.Dependencies:
				if self.doesJobDependOn (i, id1):
					return True
		except KeyError:
			pass
		return False

State = CState()

# Authenticate the user
def authenticate (request):
	if LDAPServer != "":
		username = request.getUser ()
		password = request.getPassword ()
		if username != "" or password != "":
			l = ldap.open(LDAPServer)
			output ("Authenticate "+username+" with LDAP")
			username = LDAPTemplate.replace ("%login", username)
			try:
				if l.bind_s(username, password, ldap.AUTH_SIMPLE):
					output ("Authentication OK")
					return True
			except ldap.LDAPError:
				output ("Authentication Failed")
				pass
		else:
			output ("Authentication Required")
		request.setHeader ("WWW-Authenticate", "Basic realm=\"Coalition Login\"")
		request.setResponseCode(http.UNAUTHORIZED)
		return False
	return True

class Root(static.File):
	def __init__ (self, path, defaultType='text/html', ignoredExts=(), registry=None, allowExt=0):
		static.File.__init__(self, path, defaultType, ignoredExts, registry, allowExt)

	def render (self, request):
		if authenticate (request):
			return static.File.render (self, request)
		return 'Authorization required!'

class Master(xmlrpc.XMLRPC):
	"""    """

	User = ""

	def render(self, request):
		global State
		if authenticate (request):
			self.User = request.getUser ()
			# Addjob
			if request.path == "/xmlrpc/addjob":
				title = request.args.get ("title", ["New job"])
				cmd = request.args.get ("cmd", [""])
				dir = request.args.get ("dir", ["."])
				priority = request.args.get ("priority", ["1000	"])
				retry = request.args.get ("retry", ["10"])
				affinity = request.args.get ("affinity", [""])
				dependenciesStr = request.args.get ("dependencies", [""])

				id = self.xmlrpc_addjob(title[0], cmd[0], dir[0], int(priority[0]), int(retry[0]), affinity[0], dependenciesStr[0])
				return str(id);
			else:
				# return server.NOT_DONE_YET
				return xmlrpc.XMLRPC.render (self, request)
		return 'Authorization required!'

	def xmlrpc_addjob(self, title, cmd, dir, priority, retry, affinity, dependencies):
		"""Show the command list."""
		global State
		output ("Add job : " + cmd)

		if type(dependencies) is str:
			# Parse the dependencies string
			dependencies = re.findall ('(\d+)', dependencies)

		for i in range(len(dependencies)) :
			dependencies[i] = int (dependencies[i])

		# Check for cycling referencies
		_id = State.Counter
		for dependency in dependencies:
			if State.doesJobDependOn (dependency, _id):
				print ("Error : cycle in dependencies detected.")
				return -1

		State.Jobs.append (Job(_id, title, cmd, dir, priority, retry, affinity, self.User, dependencies))
		State.Counter = _id + 1
		return _id

	def xmlrpc_getjobs(self):
		global State
		output ("Send jobs")
		update (True)
		return State.Jobs

	def xmlrpc_clearjobs(self):
		global State
		output ("Clear jobs")
		while (len(State.Jobs) > 0):
			clearJob (State.Jobs[0].ID)
		return 1

	def xmlrpc_clearjob(self, jobId):
		global State
		output ("Clear job"+str(jobId))
		clearJob (jobId)
		return 1

	def xmlrpc_resetjob(self, jobId):
		global State
		output ("Reset job"+str(jobId))
		resetJob (jobId)
		return 1

	def xmlrpc_setjobpriority(self, jobId, priority):
		global State
		output ("Set job "+str(jobId)+" priority to "+str(priority))
		for job in State.Jobs:
			if job.ID == jobId:
				job.Priority = int(priority)
		return 1

	def xmlrpc_getlog(self, jobId):
		global State
		output ("Send log "+str(jobId))
		# Look for the job
		log = ""
		try:
			logFile = open (getLogFilename(jobId), "r")
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

	def xmlrpc_getworkers(self):
		global State
		output ("Send workers")
		update (False)
		return State.Workers

	def xmlrpc_clearworkers(self):
		global State
		output ("Clear workers")
		State.Workers = []
		return 1

	def xmlrpc_stopworker(self, workerName):
		global State
		output ("Stop worker " + workerName)
		for worker in State.Workers:
			if worker.Name == workerName:
				worker.Active = False

		# Try to stop the worker's jobs
		for job in State.Jobs:
			if job.Worker == workerName and job.State == "WORKING":
				job.State = "WAITING"

		return 1

	def xmlrpc_startworker(self, workerName):
		global State
		output ("Start worker " + workerName)
		for worker in State.Workers:
			if worker.Name == workerName:
				worker.Active = True
		return 1

# Unauthenticated connection for workers
class Workers(xmlrpc.XMLRPC):
	"""    """

	def xmlrpc_heartbeat(self, hostname, jobId, log, load):
		"""Add some logs."""
		global State
		output ("Heart beat for " + str(jobId))

		# Ping the worker
		worker = getWorker (hostname)

		# Update the worker load
		worker.Load = load

		# Look for the job
		for i in range(len(State.Jobs)) :
			job = State.Jobs[i]
			if job.ID == jobId and job.State == "WORKING" and job.Worker == hostname:
				job.PingTime = time.time()
				if log != "" :
					try:
						logFile = open (getLogFilename (jobId), "a")
						logFile.write (base64.decodestring(log))
						logFile.close ()
					except IOError:
						output ("Error in logs")
				# Continue
				return True
		# Stop
		output ("Job " + str(jobId) + " not found for " + hostname)
		worker.State = "WAITING"
		return False

	def xmlrpc_pickjobwithaffinity(self, hostname, load, affinity):
		"""A worker ask for a job."""
		global State
		output (hostname + " wants some job")
		update (False)
		# Ping the worker
		worker = getWorker (hostname)
		worker.Load = load

		if not worker.Active:
			return -1,"","",""

		# Look for a job
		for i in range(len(State.Jobs)) :
			job = State.Jobs[i]
			if compareAffinities (job.Affinity, affinity) and (job.State == "WAITING" or (job.State == "ERROR" and job.Try < job.Retry)) and allDependsDone (job):
				job.State = "WORKING"
				job.Worker = hostname
				job.Try = job.Try + 1
				job.PingTime = time.time()
				job.StartTime = job.PingTime
				job.Duration = 0
				worker.State = "WORKING"
				worker.Affinity = affinity
				worker.LastJob = job.ID
				if LDAPServer != "":
					return job.ID, job.Command, job.Dir, job.User
				else:
					return job.ID, job.Command, job.Dir, ""
		worker.State = "WAITING"
		return -1,"","",""

	def xmlrpc_pickjob(self, hostname, load):
		"""A worker ask for a job."""
		return self.xmlrpc_pickjobwithaffinity(hostname, load, "")

	def xmlrpc_endjob(self, hostname, jobId, errorCode):
		"""A worker ask for a job."""
		global State
		output ("End job " + str(jobId) + " with code " + str(errorCode))

		# Ping the worker
		worker = getWorker (hostname)
		worker.State = "WAITING"

		# Look for a job
		for i in range(len(State.Jobs)) :
			job = State.Jobs[i]
			if job.ID == jobId and job.Worker == hostname and job.State == "WORKING":
				if errorCode == 0:
					job.State = "FINISHED"
					worker.Finished = worker.Finished + 1
				else:
					job.State = "ERROR"
					worker.Error = worker.Error + 1
					job.Priority = int(job.Priority)-1
				job.Duration = time.time() - job.StartTime
				sortJobs ()
				return 1
		return 1

def sortJobs ():
	global State
	global JobId2StateId

	JobId2StateId = {}
	for i in range(len(State.Jobs)) :
		# Build the map jobId -> Jobs index
		JobId2StateId[State.Jobs[i].ID] = i

	State.Jobs.sort (compareJobs)
	# Set job order
	id = 1
	for i in range(len(State.Jobs)) :
		State.Jobs[i].Order = id
		id += 1

# Returns True if all the job dependencies are in the finished state
def allDependsDone (job):
	global State

	def checkDeps (job):
		if job.State != "FINISHED":
			return False
		for i in job.Dependencies:
			try:
				depjob = State.Jobs[JobId2StateId[i]]
				if not checkDeps (depjob):
					return False
			except KeyError:
				return False
		return True

	for i in job.Dependencies:
		try:
			depjob = State.Jobs[JobId2StateId[i]]
			if not checkDeps (depjob):
				return False
		except KeyError:
			return False
	return True

# Clear a job
def clearJob (jobId):
	global State
	# Look for the job
	for i in range(len(State.Jobs)) :
		job = State.Jobs[i]
		if job.ID == jobId :
			State.Jobs.pop (i)
			break;
	# Clear the log	
	try:
		os.remove (getLogFilename(jobId))
	except OSError:
		pass

# Reset a job
def resetJob (jobId):
	global State
	# Look for the job
	for i in range(len(State.Jobs)) :
		job = State.Jobs[i]
		if job.ID == jobId :
			job.Try = 0
			job.State = "WAITING"
			break;

def getWorker (name):
	global State
	found = False
	for i in range(len(State.Workers)) :
		worker = State.Workers[i]
		if worker.Name == name :
			worker.PingTime = time.time()
			found = True
			return worker
	
	# Job not found, add it
	if not found:
		output ("Add worker " + name)
		worker = Worker (name)
		worker.PingTime = time.time()
		State.Workers.append (worker)
		return worker

def update (forceResort):
	global TimeOut
	global State
	saveDb ()
	_time = time.time()
	resort = forceResort
	for job in State.Jobs:
		if job.State == "WORKING":
			# Check if the job is timeout
			if _time - job.PingTime > TimeOut :
				output ("Job " + str(job.ID) + " timeout")
				job.State = "ERROR"
				worker = getWorker (job.Worker)
				worker.State = "TIMEOUT"
				worker.Error = worker.Error+1
				job.Priority = int(job.Priority)-1
				resort = True
			job.Duration = _time - job.StartTime
	if resort:
		sortJobs ()

	# Timeout workers
	for worker in State.Workers:
		if worker.State != "TIMEOUT" and _time - worker.PingTime > TimeOut:
			worker.State = "TIMEOUT"

# Write the DB on disk
def saveDb ():
	global State, dataDir
	fo = open(dataDir + "/master_db", "wb")
	State.write (fo)
	fo.close()
	output ("DB saved")

# Read the DB from disk
def readDb ():
	global State, dataDir
	output ("Read DB")
	try:
		fo = open(dataDir + "/master_db", "rb")
		try:
			State.read (fo)
		except IOError:
			fo.close()
			print ("Error reading master_db, create a new one")
			State = CState()
	except IOError:
		output ("No db found, create a new one")
		return
	# Touch every working job
	_time = time.time()
	for i in range(len(State.Jobs)) :
		job = State.Jobs[i]
		if job.State == "WORKING":
			job.PingTime = _time
	
# Listen to an UDP socket to respond to workers broadcasts
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
	xmlrpc = Master()
	readDb ()
	update (True)
	workers = Workers()
	root.putChild('xmlrpc', xmlrpc)
	root.putChild('workers', workers)
	output ("Listen on port " + str (port))
	reactor.listenTCP(port, server.Site(root))
	reactor.run()

if sys.platform=="win32":

	# Windows Service
	import win32serviceutil
	import win32service
	import win32event

	class WindowsService(win32serviceutil.ServiceFramework):
		_svc_name_ = "CoalitionServer"
		_svc_display_name_ = "Coalition Server"

		def __init__(self, args):
			win32serviceutil.ServiceFramework.__init__(self, args)
			self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

		def SvcStop(self):
			self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
			win32event.SetEvent(self.hWaitStop)

		def SvcDoRun(self):
			import servicemanager

			self.CheckForQuit()
			main()


		def CheckForQuit(self):
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

