from twisted.web import xmlrpc, server, static, http
from twisted.internet import defer, reactor
import cPickle, time, os, getopt, sys, base64, re, thread, ConfigParser, random
import atexit, json

GErr=0
GOk=0

print (time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(time.time ())))

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

port = cfgInt ('port', 19211)
TimeOut = cfgInt ('timeout', 10)
verbose = cfgBool ('verbose', False)
service = cfgBool ('service', True)

BackupTime = cfgInt ('backuptime', 60*60)	# Backup timing in secondes, 1H
BackupMax = cfgInt ('backupmax', 24)		# Maximum backup files, 24
BackupLastTime = time.time ()	# Last backup date

LDAPServer = ""
LDAPTemplate = ""

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

# Service only on Windows
service = service and sys.platform == "win32"

if not service:
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

if not verbose or service:
	try:
		outfile = open(dataDir + '/server.log', 'a')
		sys.stdout = outfile
		sys.stderr = outfile
		def exit ():
			print ("exit")
			outfile.close ()
		atexit.register (exit)
	except:
		pass


# Log function
def output (str):
	if verbose:
		print (str)

output ("--- Start ------------------------------------------------------------")

if service:
	output ("Running service")
else:
	output ("Running standard console")

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
			progress = float(capture) / (self.IsPercent and 100.0 or 1.0)
		return self.RE.sub ("", log), progress
		
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

class Job:
	"""A farm job"""

	def __init__ (self, title, cmd = "", dir = "", priority = 1000, retry = 10, timeout = 0, affinity = "", user = "", dependencies = [], localprogress = None, globalprogress = None):
		self.ID = None						# Job ID
		self.Parent = None					# Parent Job ID
		self.Children = []					# Children Jobs IDs
		self.Title = title					# Job title
		self.Command = cmd					# Job command to execute
		self.Dir = dir						# Job working directory
		self.State = "WAITING"				# Job state, can be WAITING, WORKING, FINISHED or ERROR
		self.Worker = ""					# Worker hostname
		self.StartTime = time.time()		# Start working time 
		self.Duration = 0					# Duration of the process
		self.PingTime = self.StartTime		# Last worker ping time
		self.Try = 0						# Number of try
		self.Retry = strToInt (retry)		# Number of try max
		self.TimeOut = strToInt (timeout)	# Timeout in seconds
		self.Priority = strToInt (priority)	# Job priority
		self.Affinity = affinity			# Job affinity
		self.User = user					# Job user
		self.Finished = 0					# Number of finished children
		self.Errors = 0						# Number of error children
		self.Working = 0					# Number of children working
		self.Total = 0						# Total number of (grand)children
		self.TotalFinished = 0				# Total number of (grand)children finished
		self.TotalErrors = 0				# Total number of (grand)children in error
		self.TotalWorking = 0				# Total number of children working
		self.Dependencies = dependencies	# Job dependencies
		if localprogress != None:
			self.LocalProgressPattern = localprogress
		if globalprogress != None:
			self.GlobalProgressPattern = globalprogress
		# self.LocalProgress				# Progress of the job
		# self.GlobalProgress				# Progress of the job

	# Has this job some children
	def hasChildren (self):
		return len (self.Children) > 0

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
		self.Name = name				# Worker name
		self.Affinity = ""				# Worker affinity
		self.State = "WAITING"			# Worker state, can be WAITING, WORKING, FINISHED or TIMEOUT
		self.PingTime = time.time()		# Last worker ping time
		self.Finished = 0				# Number of finished
		self.Error = 0					# Number of fault
		self.LastJob = -1				# Last job done
		self.Load = []					# Load of the worker
		self.FreeMemory = 0				# Free memory of the worker system
		self.TotalMemory = 0			# Total memory of the worker system
		self.Active = True				# Is the worker enabled

def writeJobLog (jobId, log):
	logFile = open (getLogFilename (jobId), "a")
	logFile.write (log)
	logFile.close ()	
			
# State of the master
# Rules for picking a job:
# If the job has children, they must be finished before
# If no child can be ran (exceeded retries count), then the job cannot be ran
# Children are picked according to their priority
DBVersion = 6
class CState:

	def __init__ (self):
		self.clear ()

	# Clear the whole database
	def clear (self) :
		self.Counter = 0
		self.Jobs = {}
		self.Workers = {}
		self._ActiveJobs = set ()
		self.addJob (0, Job ("Root", priority=1, retry=0))
		self._UpdatedDb = False
		self._StAffinity = {}			# static affinity
		self._DynAffinity = {}			# dynamic affinity, job affinity concatened to the children jobs affinity

	# Read the state
	def read (self, fo):
		version = cPickle.load(fo)
		if version == DBVersion or version == 5:
			self.Counter = cPickle.load (fo)
			self.Jobs = cPickle.load (fo)
			self.Workers = cPickle.load (fo)
			self._refresh ()
			if version <= 5:
				# Add Working, TotalWorking
				print ("Translate DB to version 6")
				for id, job in self.Jobs.iteritems () :
					job.Working = 0
					job.TotalWorking = 0				
			#self.dump ()
		else:
			raise Exception ("Database too old, erase the master_db file")
			self.clear ()

	# Write the state
	def write (self, fo):
		version = DBVersion
		cPickle.dump (version, fo)
		cPickle.dump (self.Counter, fo)
		cPickle.dump (self.Jobs, fo)
		cPickle.dump (self.Workers, fo)
		self._UpdatedDb = False
		#self.dump ()

	def update (self, forceSaveDb = False) :
		global	TimeOut
		_time = time.time ()
		refreshActive = False
		for id in State._ActiveJobs.copy () :
			try:
				job = self.Jobs[id]
				if job.State == "WORKING":
					if _time - job.PingTime > TimeOut :
						# Job times out, no heartbeat received for too long
						output ("Job " + str(job.ID) + " is AWOL")
						self.updateJobState (id, "ERROR")
						self.updateWorkerState (job.Worker, "TIMEOUT")
						writeJobLog (job.ID, "SERVER: Worker "+job.Worker+" doesn't respond, timeout.")
					elif job.TimeOut > 0 and _time - job.StartTime > job.TimeOut:
						# job exceeded run time
						output ("Job " + str(job.ID) + " timeout, exceeded run time")
						self.updateJobState (id, "ERROR")
						self.updateWorkerState (job.Worker, "ERROR")
						writeJobLog (job.ID, "SERVER: Job " + str(job.ID) + " timeout, exceeded run time")
					job.Duration = _time - job.StartTime
			except KeyError:
				refreshActive = True
		if refreshActive :
			self._refresh ()
		# Timeout workers
		for name, worker in State.Workers.iteritems ():
			if worker.State != "TIMEOUT" and _time - worker.PingTime > TimeOut:
				self.updateWorkerState (name, "TIMEOUT")
		if forceSaveDb:
			saveDb ()

	# -----------------------------------------------------------------------
	# job handling

	# Is job dependent on another
	def doesJobDependOn (self, id0, id1):
		if id0 == id1:
			return True
		try:
			job0 = self.Jobs[id0]
			for i in job0.Dependencies:
				if self.doesJobDependOn (i, id1):
					return True
		except KeyError:
			pass
		return False

	# Find a job by its title
	def findJobByTitle (self, title):
		for id, job in self.Jobs.iteritems ():
			if job.Title == title:
				return id

	# Find a job by its path, job path atoms are separated by pipe '|'
	def findJobByPath (self, path):
		job = self.Jobs[0]
		atoms = re.findall ('([^|]+)', path)
		for atom in atoms :
			found = False
			for id in job.Children :
				try :
					child = self.Jobs[id]
					if child.Title == atom :
						job = child
						found = True
						break
				except KeyError:
					pass
			if not found :
				return None
		return job.ID

	# Add a job
	def addJob (self, parent, job):
		try:
			parentJob = None
			job.ID = self.Counter
			if job.ID != 0:
				parentJob = self.Jobs[parent]
			self.Counter = job.ID + 1
			self.Jobs[job.ID] = job
			self._UpdatedDb = True
			if job.ID != 0:
				job.Parent = parent
				parentJob.Children.append (job.ID)
				self._updateAffinity (job.ID)
				self._updateParentState (parent)
			return job.ID
		except KeyError:
			print ("Can't add job to parent " + str (parent) + " type", type (parent))

	# Remove a job
	def removeJob (self, id, updateParentState = True):
		if id != 0:
			try:
				job = self.Jobs[id]
				self._UpdatedDb = True
				# remove children first
				while (len (job.Children) > 0) :
					self.removeJob (job.Children[0])
				# remove self from parent
				parent = self.Jobs[job.Parent]
				for k, childid in enumerate (parent.Children) :
					if childid == id :
						parent.Children.pop (k)
						break
				# and unmap
				try:
					del self.Jobs[id]
				except KeyError:
					pass
				try:
					del self._StAffinity[id]
				except KeyError:
					pass
				try:
					del self._DynAffinity[id]
				except KeyError:
					pass
				try:
					self._ActiveJobs.remove (id)
				except KeyError:
					pass
				# only update parent's state when required (for instance in removeChildren, it is done after removing all children)
				if updateParentState:
					self._updateParentState (parent.ID)
			except KeyError:
				pass

	# Remove children jobs
	def removeChildren (self, id) :
		job = self.Jobs[id]
		while (len (job.Children) > 0) :
			self.removeJob (job.Children[0], False)
		self._updateParentState (id)

	# Change job affinity
	def setAffinity (self, id, affinity) :
		try:
			job = self.Jobs[id]
			job.Affinity = affinity
			try:
				del self._StAffinity[id]
			except KeyError:
				pass
			self._UpdatedDb = True
			self._updateParentState (id)
		except:
			pass

	# Reset a job
	def resetJob (self, id) :
		try:
			job = self.Jobs[id]
			job.State = "WAITING"
			job.Try = 0
			job.Worker = ""
			if getattr(job, "LocalProgress", False):
				job.LocalProgress = 0
			if getattr(job, "GlobalProgress", False):
				job.GlobalProgress = 0
			try:
				self._ActiveJobs.remove (id)
			except KeyError:
				pass
			self._UpdatedDb = True
			self._updateParentState (id)
		except KeyError:
			pass

	# Reset a job
	def pauseJob (self, id) :
		try:
			job = self.Jobs[id]
			if job.State != "FINISHED":
				job.State = "PAUSED"
				try:
					self._ActiveJobs.remove (id)
				except KeyError:
					pass
				self._UpdatedDb = True
				self._updateParentState (id)
		except KeyError:
			pass

	# Can be executed
	def canExecute (self, id) :
		if id == 0:
			return False
		job = self.Jobs[id]
		if job.State == "FINISHED" or job.State == "WORKING" or job.State == "PAUSED" :
			# Don't execute a finished job or a working job
			return False
		else:
			# Waiting jobs can be executed only if all dependencies are finished
			# Error jobs can be ran only if they have no children and tries left
			for depId in job.Dependencies :
				dep = self.Jobs[depId]
				if dep.State != "FINISHED" :
					return False
			return (job.State == "WAITING") or (not job.hasChildren () and job.Try < job.Retry)

	# Can be executed
	def compatibleAffinities (self, job, worker) :
		if len (job) == 0:
			return True
		for affinity in job:
			if worker >= affinity:
				return True
		return False

	# Pick a job
	def pickJob (self, id, affinity) :
		try:
			job = self.Jobs[id]
			sumpriority = 0
			jobs = []
			# sum all children priorities
			allFinished = True
			for childId in job.Children :
				child = self.Jobs[childId]
				if child.State != "FINISHED" :
					allFinised = False
				# if job can be executed and worker affinity is compatible, add this job as a potential one
				if self.canExecute (childId):
					if self.compatibleAffinities (self._DynAffinity[childId], affinity):
						#output ("++ worker "+str (affinity)+" compatible with job "+str (childId)+" "+str (self._DynAffinity[childId]))
						sumpriority += child.Priority
						jobs.append (child)
					else:
						#output ("-- worker "+str (affinity)+" NOT compatible with job "+str (childId)+" "+str (self._DynAffinity[childId]))
						pass
			if sumpriority > 0 :
				# there are some children that need execution
				pick = random.randint (0, sumpriority-1)
				sumpriority = 0
				for child in jobs :
					if pick >= sumpriority and pick < sumpriority+child.Priority :
						if child.hasChildren () :
							return self.pickJob (child.ID, affinity)
						else:
							return child.ID
					sumpriority += child.Priority
			elif allFinished and State.canExecute (id) :
				# all children were successfully executed, execute this job
				return id
		except KeyError:
			pass

	# Update job state
	def updateJobState (self, id, state) :
		global GErr, GOk
		if state == "ERROR" :
			GErr += 1
		if state == "FINISHED" :
			GOk += 1
		try :
			job = self.Jobs[id]
			if job.State != state :
				self._UpdatedDb = True
				job.State = state
				if state == "WORKING" :
					job.Try += 1
					job.StartTime = time.time ()
					self._ActiveJobs.add (id)
				elif state == "ERROR" or state == "FINISHED":
					if state == "ERROR":
						job.Priority = max (job.Priority-1, 0)
					job.Duration = time.time() - job.StartTime
					try:
						self._ActiveJobs.remove (id)
					except KeyError:
						pass
				self._updateParentState (job.Parent)
		except KeyError:
			pass

	# Update parent state
	def _updateParentState (self, id) :																																			
		try:
			job = self.Jobs[id]
			jobsToDo = False
			hasError = False
			total = 0
			totalfinished = 0
			totalerrors = 0
			totalworking = 0
			finished = 0
			errors = 0
			working = 0
			for childId in job.Children :
				if self.canExecute (childId):
					jobsToDo = True
				child = self.Jobs[childId]
				state = child.State
				total += child.Total or 0
				totalerrors += child.TotalErrors or 0
				totalfinished += child.TotalFinished or 0
				totalworking += child.TotalWorking or 0
				if state == "ERROR":
					errors += 1
				elif state == "FINISHED":
					finished += 1
				elif state == "WORKING":
					working += 1
			total += len (job.Children)
			totalerrors += errors
			totalfinished += finished
			totalworking += working
			newState = "WAITING"
			job.Finished = finished
			job.Errors = errors
			job.Working = working
			job.Total = total
			job.TotalErrors = totalerrors
			job.TotalFinished = totalfinished
			job.TotalWorking = totalworking
			if not jobsToDo and errors > 0 :
				newState = "ERROR"
			if job.State != "PAUSED" and newState != job.State:
				job.State = newState
				self._UpdatedDb = True
			self._updateAffinity (id)
			if id != 0:
				self._updateParentState (job.Parent)
		except KeyError:
			pass

	# Update job affinity
	def _updateAffinity (self, id) :
		job = self.Jobs[id]
		if id not in self._StAffinity:
			if job.Affinity != "" :
				self._StAffinity[id] = frozenset (re.findall ('([^,]+)', job.Affinity))
			else:
				self._StAffinity[id] = None
		static = self._StAffinity[id]
		# compute dynamic affinity from all waiting children dynamic affinity
		# dynamic affinity is a set of children dynamic affinities
		dyn = set ()
		allFinished = True
		someChildrenEmpty = False
		for cid in job.Children :
			child = self.Jobs[cid]
			if child.State != "FINISHED" :
				allFinished = False
			if self.canExecute (cid):
				cdyn = self._DynAffinity[cid]
				empty = True
				for aff in cdyn:
					dynIsEmpty = False
					empty = False
					if static:
						dyn.add (aff | static)
					else:
						dyn.add (aff)

				# One child without affinity
				someChildrenEmpty |= len(cdyn) == 0
		
		# If some children are empty, but the set is not empty, add an empty set
		if someChildrenEmpty and len(dyn) > 0:
			dyn.add (frozenset ())
			
		if len (dyn) == 0 and static :
			# no affinity set yet, add default
			dyn.add (static)
		self._DynAffinity[id] = dyn

	# Refresh active jobs count
	def _refresh (self) :
		def safeInt (v, defvalue):
			try:
				return int (v)
			except:
				return defvalue
		def safeStr (v, defvalue):
			try:
				return str (v)
			except:
				return defvalue
		active = set ()
		for id, job in self.Jobs.iteritems ():
			if job.State == "WORKING":
				active.add (id)
			job.Parent = safeInt (job.Parent, 0)
			job.Command = safeStr (job.Command, "")
			job.Dir = safeStr (job.Dir, "")
			job.State = safeStr (job.State, "ERROR")
			job.Worker = safeStr (job.Worker, "")
			job.StartTime = safeInt (job.StartTime, time.time ())
			job.Duration = safeInt (job.Duration, 0)
			job.PingTime = safeInt (job.PingTime, time.time ())
			job.Try = safeInt (job.Try, 0)
			job.Retry = safeInt (job.Retry, 10)
			job.TimeOut = safeInt (job.TimeOut, 0)
			job.Priority = safeInt (job.Priority, 1000)
			job.Affinity = safeStr (job.Affinity, "")
			job.User = safeStr (job.User, "")

		self._ActiveJobs = active
		def _upChildren (job) :
			total = 0
			totalerrors = 0
			totalfinished = 0
			for cid in job.Children :
				child = self.Jobs[cid]
				_upChildren (child)
				total += child.Total
				totalerrors += child.TotalErrors
				totalfinished += child.TotalFinished
				if child.State == "ERROR":
					totalerrors += 1
				elif child.State == "FINISHED":
					totalfinished += 1
			self._updateAffinity (job.ID)
			job.Total = total+len (job.Children)
			job.TotalFinished = totalfinished
			job.TotalErrors = totalerrors
		_upChildren (self.Jobs[0])

	# -----------------------------------------------------------------------
	# worker handling

	# get a worker
	def getWorker (self, name) :
		try :
			worker = self.Workers[name]
			worker.PingTime = time.time()
			return worker
		except KeyError:
			# Worker not found, add it
			self._UpdatedDb = True
			output ("Add worker " + name)
			worker = Worker (name)
			worker.PingTime = time.time()
			self.Workers[name] = worker
			return worker

	def stopWorker (self, name):
		output ("Stop worker " + name)
		try :
			self.Workers[name].Active = False
			self._UpdatedDb = True
		except KeyError:
			pass
		# Try to stop the worker's jobs
		for id, job in self.Jobs.iteritems ():
			if job.Worker == name and job.State == "WORKING":
				job.State = "WAITING"
				self._UpdatedDb = True

	def startWorker (self, name):
		output ("Start worker " + name)
		try :
			self.Workers[name].Active = True
			self._UpdatedDb = True
		except KeyError:
			pass

	def updateWorkerState (self, name, state) :
		try:
			worker = self.Workers[name]
			if state != worker.State:
				self._UpdatedDb = True
				if state == "ERROR" :
					worker.Error += 1
					worker.State = "WAITING"
				elif state == "FINISHED" :
					worker.Finished += 1
					worker.State = "WAITING"
				elif state == "TIMEOUT" :
					worker.Error += 1
					worker.State = "TIMEOUT"
				else:
					worker.State = state
		except KeyError:
			pass

	# -----------------------------------------------------------------------
	# debug/dump

	def dump (self) :
		def dumpJob (id, depth) :
			try:
				job = self.Jobs[id]
				print (" "*(depth*2)) + str (job.ID) + " " + job.Title + " " + job.State + " cmd='" + job.Dir + "/" + job.Command + "' prio=" + str (job.Priority) + " retry=" + str (job.Try) + "/" + str (job.Retry)
				try:
					static = self._StAffinity[id]
					dyn = self._DynAffinity[id]
					print (" "*(depth*2+1)), "Static:", static
					print (" "*(depth*2+1)), "Dyn:", dyn
				except:
					pass
				for childId in job.Children :
					dumpJob (childId, depth+1)
			except KeyError:
				print (" "*(depth*2)) + "<<< Unknown job " + str (id) + " >>>"
		dumpJob (0, 0)

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




class Root (static.File):
	def __init__ (self, path, defaultType='text/html', ignoredExts=(), registry=None, allowExt=0):
		static.File.__init__(self, path, defaultType, ignoredExts, registry, allowExt)

	def render (self, request):
		if authenticate (request):
			return static.File.render (self, request)
		return 'Authorization required!'

class Master (xmlrpc.XMLRPC):
	"""    """

	User = ""

	def render (self, request):
		global State
		if authenticate (request):
			self.User = request.getUser ()
			# Addjob

			def getArg (name, default):
				value = request.args.get (name, [default])
				return value[0]

			if request.path == "/xmlrpc/addjob" or request.path == "/json/addjob":

				parent = getArg ("parent", "0")
				title = getArg ("title", "New job")
				cmd = getArg ("cmd", "")
				dir = getArg ("dir", ".")
				priority = getArg ("priority", "1000")
				retry = getArg ("retry", "10")
				timeout = getArg ("timeout", "0")
				affinity = getArg ("affinity", "")
				dependencies = getArg ("dependencies", "")
				localprogress = getArg ("localprogress", None)
				globalprogress = getArg ("globalprogress", None)

				output ("Add job : " + cmd)
				if isinstance (parent, str):
					try:
						# try as an int
						parent = int (parent)
					except ValueError:
						bypath = State.findJobByPath (parent)
						if bypath:
							parent = bypath
						else:
							parenttitle = parent
							parent = State.findJobByTitle (parent)
							if parent == None:
								print ("Error : can't find job " + str (parenttitle))
								return -1
				if type(dependencies) is str:
					# Parse the dependencies string
					dependencies = re.findall ('(\d+)', dependencies)
				for i, dep in enumerate (dependencies) :
					dependencies[i] = int (dep)
				
				id = State.addJob (parent, Job (str (title), str (cmd), str (dir), int (priority), int (retry), int (timeout), str (affinity), str (self.User), dependencies, localprogress, globalprogress))
				
				State.update ()
				return str(id)
			elif request.path == "/json/getjobs":
				return self.json_getjobs (int(getArg ("id", 0)), getArg ("filter", ""))
			elif request.path == "/json/clearjobs":
				return self.json_clearjobs (request.args.get ("id"))
			elif request.path == "/json/resetjobs":
				return self.json_resetjobs (request.args.get ("id"))
			elif request.path == "/json/pausejobs":
				return self.json_pausejobs (request.args.get ("id"))
			elif request.path == "/json/updatejobs":
				return self.json_updatejobs (request.args.get ("id"), request.args.get ("prop"),request.args.get ("value"))
			elif request.path == "/json/getlog":
				return self.json_getlog (int(getArg ("id", 0)))
			elif request.path == "/json/getworkers":
				return self.json_getworkers ()
			elif request.path == "/json/clearworkers":
				return self.json_clearworkers (request.args.get ("id"))
			elif request.path == "/json/stopworkers":
				return self.json_stopworkers (request.args.get ("id"))
			elif request.path == "/json/startworkers":
				return self.json_startworkers (request.args.get ("id"))
			elif request.path == "/json/updateworkers":
				return self.json_updateworkers (request.args.get ("id"), request.args.get ("prop"),request.args.get ("value"))
			else:
				# return server.NOT_DONE_YET
				return xmlrpc.XMLRPC.render (self, request)
		return 'Authorization required!'

	def json_getjobs (self, id, filter):
		global State
		output ("Send jobs")

		State.update ()
		
		vars = ["ID","Title","Command","Dir","State","Worker","StartTime","Duration","Try","Retry","TimeOut","Priority","Affinity","User","Finished","Errors","Working","Total","TotalFinished","TotalErrors","TotalWorking","Dependencies","LocalProgress","GlobalProgress"];

		# Get the job
		try:
			job = State.Jobs[id]
		except KeyError:
			job = State.Jobs[0]
			
		# Build the children
		jobs = "["
		for childId in job.Children :
			try:
				child = State.Jobs[childId]
				if filter == "" or child.State == filter:
					childparams = "["
					for var in vars:
						try:
							childparams += json.dumps (getattr (child, var)) + ','
						except AttributeError:
							pass
					childparams += "],\n"
					jobs += childparams
			except KeyError:
				pass
		jobs += "]"

		parents = []
		# Build the parents
		while True:
			parents.insert (0, { "ID":job.ID, "Title":job.Title })
			if job.ID == 0:
				break
			job = State.Jobs[job.Parent]
		
		return '{ "Vars":'+repr(vars)+', "Jobs":'+jobs+', "Parents":'+repr(parents)+' }'

	def json_clearjobs (self, ids):
		global State
		for jobId in ids:
			output ("Clear job "+str (jobId))
			State.removeJob (int(jobId))
		State.update ()
		return "1"

	def json_resetjobs (self, ids):
		global State
		for jobId in ids:
			output ("Reset job "+str (jobId))
			State.resetJob (int(jobId))
		State.update ()
		return "1"

	def json_pausejobs (self, ids):
		global State
		for jobId in ids:
			output ("Pause job "+str (jobId))
			State.pauseJob (int(jobId))
		State.update ()
		return "1"

	def json_updatejobs (self, ids, props, values):
		global State
		output ("Update job "+str (ids)+" "+str(props)+" "+str(values))
		if props == None or values == None or len(props) != len(values):
			return "0"
		for i in range(0,len(props)):
			prop = props[i]
			value = values[i]
			for id in ids:
				id = int(id)
				try:
					job = State.Jobs[id]
					try:
						if prop == "Command":
							job.Command = str (value)
						elif prop == "Dir":
							job.Dir = str (value)
						elif prop == "Priority":
							job.Priority = int (value)
						elif prop == "Affinity":
							State.setAffinity (job.ID, str (value))
						elif prop == "TimeOut":
							job.TimeOut = int (value)
						elif prop == "Title":
							job.Title = str (value)
						elif prop == "Retry":
							job.Retry = int (value)
						elif prop == "Dependencies":
							job.Dependencies = str (value)
						State._UpdatedDb = True
					except ValueError:
						pass
				except KeyError:
					pass
		State.update ()
		return "1"

	def json_getlog (self, jobId):
		global State
		output ("Send log "+str (jobId))
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
		return repr (log)

	def json_getworkers (self):
		global State
		output ("Send workers")

		State.update ()

		vars = ["Name","Affinity","State","Finished","Error","LastJob","Load","FreeMemory","TotalMemory","Active"]

		# Build the children
		workers = "["
		for name, worker in State.Workers.iteritems () :
			childparams = "["
			for var in vars:
				childparams += json.dumps (getattr (worker, var)) + ','
			childparams += "],\n"
			workers += childparams
		workers += "]"
		
		result = ('{ "Vars":'+repr(vars)+', "Workers":'+workers+'}')
		return result

	def json_clearworkers (self, names):
		global State
		for name in names:
			output ("Clear worker "+str (name))
			try:
				State.Workers.pop (name)
				State._UpdatedDb = True
			except KeyError:
				pass
		State.update ()
		return "1"

	def json_stopworkers (self, names):
		global State
		for name in names:
			State.stopWorker (name)
		State.update ()
		return "1"

	def json_startworkers (self, names):
		global State
		for name in names:
			State.startWorker (name)
		State.update ()
		return "1"

	# update several workers props at once
	def json_updateworkers (self, names, props, values):
		global State
		try:
			output ("Update workers "+str (names)+" "+str(props)+" "+str(values))
		except:
			pass
		if len(props) != len(values):
			return "0"
		for i in range(0,len(props)):
			prop = props[i]
			value = values[i]
			for name in names:
				try:
					worker = State.Workers[name]
					try:
						if prop == "Affinity":
							worker.Affinity = str (value)
						State._UpdatedDb = True
					except ValueError:
						pass
				except KeyError:
					pass
		State.update ()
		return "1"

# Unauthenticated connection for workers
class Workers(xmlrpc.XMLRPC):
	"""    """

	def render (self, request):
		global State

		def getArg (name, default):
			value = request.args.get (name, [default])
			return value[0]

		if request.path == "/workers/heartbeat":
			return self.json_heartbeat (getArg ('hostname', ''), getArg ('jobId', '-1'), getArg ('log', ''), getArg ('load', '[0]'), getArg ('freeMemory', '0'), getArg ('totalMemory', '0'))
		elif request.path == "/workers/pickjob":
			return self.json_pickjob (getArg ('hostname', ''), getArg ('load', '[0]'), getArg ('freeMemory', '0'), getArg ('totalMemory', '0'))
		elif request.path == "/workers/endjob":
			return self.json_endjob (getArg ('hostname', ''), getArg ('jobId', '1'), getArg ('errorCode', '0'))
		else:
			# return server.NOT_DONE_YET
			return xmlrpc.XMLRPC.render (self, request)

	def json_heartbeat (self, hostname, jobId, log, load, freeMemory, totalMemory):
		"""Get infos from the workers."""
		global State
		_time = time.time ()
		output ("Heart beat for " + str(jobId) + " " + str(load))
		# Update the worker load and ping time
		worker = State.getWorker (hostname)
		try:
			worker.Load = eval (load)
		except SyntaxError:
			worker.Load = [0]
		worker.FreeMemory = int(freeMemory)
		worker.TotalMemory = int(totalMemory)
		workingJob = None
		jobId = int(jobId)
		try :
			job = State.Jobs[jobId]
			if job.State == "WORKING" and job.Worker == hostname :
				State.updateWorkerState (hostname, "WORKING")
				workingJob = job
				job.PingTime = _time
				if log != "" :
					try:
						logFile = open (getLogFilename (jobId), "a")
						log = base64.decodestring(log)
						
						# Filter the log progression message
						progress = None
						localProgress = getattr(job, "LocalProgressPattern", None)
						globalProgress = getattr(job, "GlobalProgressPattern", None)
						if localProgress or globalProgress:
							output ("progressPattern : \n" + str(localProgress) + " " + str(globalProgress))
							lp = None
							gp = None
							if localProgress:
								lFilter = getLogFilter (localProgress)
								log, lp = lFilter.filterLogs (log)
							if globalProgress:
								gFilter = getLogFilter (globalProgress)
								log, gp = gFilter.filterLogs (log)
							if lp != None:
								output ("lp : "+ str(lp)+"\n")
								job.LocalProgress = lp
							if gp != None:
								output ("gp : "+ str(gp)+"\n")
								job.GlobalProgress = gp
						
						logFile.write (log)
						logFile.close ()
					except IOError:
						output ("Error in logs")
		except KeyError:
			pass
		State.update ()
		if worker.State == "WORKING" and workingJob != None and workingJob.State == "WORKING":
			return "true"
		# Stop
		output ("Error at " + hostname + " heartbeat, set to WAITING")
		State.updateWorkerState (hostname, "WAITING")
		if workingJob:
			State.updateJobState (jobId, "WAITING")
		return "false"

	def json_pickjob (self, hostname, load, freeMemory, totalMemory):
		"""A worker ask for a job."""
		global State
		output (hostname + " wants some job" + " " + load)
		worker = State.getWorker (hostname)
		try:
			worker.Load = eval (load)
		except SyntaxError:
			worker.Load = [0]
		worker.FreeMemory = int(freeMemory)
		worker.TotalMemory = int(totalMemory)
		if not worker.Active:
			State.updateWorkerState (hostname, "WAITING")
			return '-1,"","",""'
		affinity = frozenset (re.findall ('([^,]+)', worker.Affinity))
		jobId = State.pickJob (0, affinity)
		if jobId != None :
			job = State.Jobs[jobId]
			if job.State == "FINISHED":
				output (hostname + " picked a finished job!")
			job.Worker = hostname
			job.PingTime = time.time()
			job.StartTime = job.PingTime
			job.Duration = 0
			State.updateJobState (jobId, "WORKING")
			worker.LastJob = job.ID
			worker.PingTime = job.PingTime
			State.updateWorkerState (hostname, "WORKING")
			State.update ()
			output (hostname + " picked job " + str (jobId) + " " + worker.State)
			if job.User != None and job.User != "":
				return repr (job.ID)+","+repr (job.Command)+","+repr (job.Dir)+","+repr (job.User)
			else:
				return repr (job.ID)+","+repr (job.Command)+","+repr (job.Dir)+","+'""'

		State.updateWorkerState (hostname, "WAITING")
		State.update ()
		return '-1,"","",""'

	def json_endjob (self, hostname, jobId, errorCode):
		"""A worker finished a job."""
		global State
		worker = State.getWorker (hostname)
		output ("End job " + str(jobId) + " with code " + str (errorCode))
		jobId = int(jobId)
		errorCode = int(errorCode)
		try:
			job = State.Jobs[jobId]
			if job.State == "WORKING" and job.Worker == hostname :
				result = "FINISHED"
				if errorCode != 0 :
					result = "ERROR"
				State.updateJobState (jobId, result)
				State.updateWorkerState (hostname, result)
		except KeyError:
			pass
		State.update ()
		return "1"

# Backup the DB
# Erase master_db.maxBackup
# Rename master_db.N in master_db.N+1
# Copy master_db in master_db.1
def backup ():
	global BackupTime, BackupLastTime, BackupMax
	if time.time() - BackupLastTime > BackupTime:
		# Remove the last backup
		try:
			os.remove (dataDir + "/master_db." + str(BackupMax))
			output ('remove ' + dataDir + "/master_db." + str(BackupMax))
		except OSError:
			pass

		# Rename the backups
		for i in range (BackupMax,1,-1):
			try:
				os.rename (dataDir + "/master_db." + str(i-1), dataDir + "/master_db." + str(i))
				output ('rename ' + dataDir + "/master_db." + str(i-1) + ' in ' + dataDir + "/master_db." + str(i))
			except OSError:
				pass

		# Copy the last db
		try:
			os.rename (dataDir + "/master_db", dataDir + "/master_db.1")
			output ('rename ' + dataDir + "/master_db in " + dataDir + "/master_db.1")
		except OSError:	
			pass
		BackupLastTime = time.time()

# Write the DB on disk
def saveDb ():
	global State, dataDir
	global GErr, GOk
#	print ("Error : " + str(GErr) + " OK : " + str(GOk))
	if State._UpdatedDb:
		backup ()
		fo = open(dataDir + "/master_db.part", "wb")
		try:
			State.write (fo)
			fo.close()
			try:
				os.remove (dataDir + '/master_db')
			except OSError:
				pass
			os.rename (dataDir + '/master_db.part', dataDir + '/master_db')
		except IOError:
			fo.close()		
		output ("DB saved")
	reactor.callLater(5, saveDb)

# Read the DB from disk
def readDb ():
	global State, dataDir
	output ("Read DB")
	try:
		try:
			fo = open(dataDir + "/master_db", "rb")
		except IOError:
			output ("No db found, create a new one")
			State = CState()
			return
		State.read (fo)
	except:
		print ("Error reading " + dataDir + "/master_db" + " ! Quit !")
		sys.exit (1)
	output ("DB is OK")
	# Touch every working job
	_time = time.time()
	for id, job in State.Jobs.iteritems () :
		if job.State == "WORKING":
			job.PingTime = _time
	output ("DB is OK")
	
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
	webService = Master()
	readDb ()
	workers = Workers()
	root.putChild('xmlrpc', webService)
	root.putChild('json', webService)
	root.putChild('workers', workers)
	output ("Listen on port " + str (port))
	reactor.listenTCP(port, server.Site(root))
	reactor.callLater(5, saveDb)
	reactor.run()

if sys.platform=="win32" and service:

	# Windows Service
	import win32serviceutil
	import win32service
	import win32event

	class WindowsService(win32serviceutil.ServiceFramework):
		_svc_name_ = "CoalitionServer"
		_svc_display_name_ = "Coalition Server"

		def __init__(self, args):
			output ("Service init")
			win32serviceutil.ServiceFramework.__init__(self, args)
			self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

		def SvcStop(self):
			output ("Service stop")
			self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
			win32event.SetEvent(self.hWaitStop)

		def SvcDoRun(self):
			output ("Service running")
			import servicemanager
			self.CheckForQuit()
			main()
			output ("Service quitting")

		def CheckForQuit(self):
			output ("Checking for quit...")
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
