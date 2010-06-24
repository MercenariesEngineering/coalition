from twisted.web import xmlrpc, server, static, http
from twisted.internet import defer, reactor
import pickle, time, os, getopt, sys, base64, re, thread, ConfigParser, random

# This module is standard in Python 2.2, otherwise get it from
#   http://www.pythonware.com/products/xmlrpc/
import xmlrpclib

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
	if config.has_option('server', 'port'):
		try:
			return int (config.get('server', name))
		except:
			pass
	return defvalue

def cfgBool (name, defvalue):
	global config
	if config.has_option('server', 'port'):
		try:
			return int (config.get('server', name)) != 0
		except:
			pass
	return defvalue

port = cfgInt ('port', 19211)
TimeOut = cfgInt ('timeout', 10)
verbose = cfgBool ('verbose', False)
service = cfgBool ('service', False)

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

if sys.platform!="win32" or not service:
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
	except:
		pass

# Log function
def output (str):
	if verbose:
		print (str)

output ("--- Start ------------------------------------------------------------")

if sys.platform!="win32" and service:
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

class Job:
	"""A farm job"""

	def __init__ (self, title, cmd = "", dir = "", priority = 1000, retry = 10, timeout = 0, affinity = "", user = "", dependencies = []):
		self.ID = None						# Jod ID
		self.Parent = None					# Parent Job ID
		self.Children = []					# Children Jobs IDs
		self.Title = title					# Job title
		self.Command = cmd					# Job command to execute
		self.Dir = dir						# Jod working directory
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
		self.Order = 0						# Job order
		self.Finished = 0					# Number of finished children
		self.Errors = 0						# Number of error children
		self.Total = 0						# Total number of (grand)children
		self.TotalFinished = 0				# Total number of (grand)children finished
		self.TotalErrors = 0				# Total number of (grand)children in error
		self.Dependencies = dependencies	# Job dependencies

	# Has this job some children
	def hasChildren (self) :
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
		self.Load = 0					# Load of the worker
		self.Active = True				# Is the worker enabled

# State of the master
# Rules for picking a job:
# If the job has children, they must be finished before
# If no child can be ran (exceeded retries count), then the job cannot be ran
# Children are picked according to their priority
DBVersion = 5
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
		self._UpdatedDb = True
		self._StAffinity = {}			# static affinity
		self._DynAffinity = {}			# dynamic affinity, job affinity concatened to the children jobs affinity

	# Read the state
	def read (self, fo):
		version = pickle.load(fo)
		if version == DBVersion:
			self.Counter = pickle.load (fo)
			self.Jobs = pickle.load (fo)
			self.Workers = pickle.load (fo)
			self._refresh ()
			#self.dump ()
		else:
			raise Exception ("Database too old, erase the master_db file")
			self.clear ()

	# Write the state
	def write (self, fo):
		version = DBVersion
		pickle.dump (version, fo)
		pickle.dump (self.Counter, fo)
		pickle.dump (self.Jobs, fo)
		pickle.dump (self.Workers, fo)
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
					elif job.TimeOut > 0 and _time - job.StartTime > job.TimeOut:
						# job exceeded run time
						output ("Job " + str(job.ID) + " timeout, exceeded run time")
						self.updateJobState (id, "ERROR")
						self.updateWorkerState (job.Worker, "ERROR")
					job.Duration = _time - job.StartTime
			except KeyError:
				refreshActive = True
		if refreshActive :
			self._refresh ()
		# Timeout workers
		for name, worker in State.Workers.iteritems ():
			if worker.State != "TIMEOUT" and _time - worker.PingTime > TimeOut:
				self.updateWorkerState (name, "TIMEOUT")
		if self._UpdatedDb or forceSaveDb:
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

	# Reset a job
	def resetJob (self, id) :
		try:
			job = self.Jobs[id]
			job.State = "WAITING"
			job.Try = 0
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

	# Change a job priority
	def setPriority (self, id, priority) :
		try:
			job = self.Jobs[id]
			job.Priority = priority
			self._UpdatedDb = True
		except KeyError:
			pass

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
			finished = 0
			errors = 0
			for childId in job.Children :
				if self.canExecute (childId):
					jobsToDo = True
				child = self.Jobs[childId]
				state = child.State
				total += child.Total or 0
				totalerrors += child.TotalErrors or 0
				totalfinished += child.TotalFinished or 0
				if state == "ERROR":
					errors += 1
				elif state == "FINISHED":
					finished += 1
			total += len (job.Children)
			totalerrors += errors
			totalfinished += finished
			newState = "WAITING"
			job.Finished = finished
			job.Errors = errors
			job.Total = total
			job.TotalErrors = totalerrors
			job.TotalFinished = totalfinished
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
		for cid in job.Children :
			child = self.Jobs[cid]
			if child.State != "FINISHED" :
				allFinished = False
			if self.canExecute (cid):
				cdyn = self._DynAffinity[cid]
				for aff in cdyn:
					if static:
						dyn.add (aff | static)
					else:
						dyn.add (aff)
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
					totalerror += 1
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
			if request.path == "/xmlrpc/addjob":
				parent = request.args.get ("parent", ["0"])
				title = request.args.get ("title", ["New job"])
				cmd = request.args.get ("cmd", [""])
				dir = request.args.get ("dir", ["."])
				priority = request.args.get ("priority", ["1000"])
				retry = request.args.get ("retry", ["10"])
				timeout = request.args.get ("timeout", ["0"])
				affinity = request.args.get ("affinity", [""])
				dependenciesStr = request.args.get ("dependencies", [""])
				id = self.xmlrpc_addjob(parent[0], title[0], cmd[0], dir[0], int(priority[0]), int(retry[0]), int(timeout[0])*60, affinity[0], dependenciesStr[0])
				return str(id);
			else:
				# return server.NOT_DONE_YET
				return xmlrpc.XMLRPC.render (self, request)
		return 'Authorization required!'

	def xmlrpc_addjob (self, parent, title, cmd, dir, priority, retry, timeout, affinity, dependencies):
		"""Show the command list."""
		global State
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
		id = State.addJob (parent, Job (str (title), str (cmd), str (dir), int (priority), int (retry), int (timeout), str (affinity), str (self.User), dependencies))
		State.update ()
		return id

	def xmlrpc_getjobs (self, id):
		global State
		output ("Send jobs")
		jobs = []
		parents = []
		try:
			job = State.Jobs[id]
			for childId in job.Children :
				try:
					child = State.Jobs[childId]
					jobs.append (child)
				except KeyError:
					pass
			while True:
				parents.insert (0, { "ID":job.ID, "Title":job.Title })
				if job.ID == 0:
					break
				job = State.Jobs[job.Parent]
		except KeyError:
			if len (parents) == 0 or parents[0].ID != 0:
				parents.insert (0, { "ID":0, "Title":"Root" })
		return { "Jobs":jobs, "Parents":parents }

	def xmlrpc_clearjobs (self, id):
		global State
		output ("Clear jobs in " + str (id))
		State.removeChildren (id)
		State.update ()
		return 1

	def xmlrpc_clearjob (self, jobId):
		global State
		output ("Clear job "+str (jobId))
		State.removeJob (jobId)
		State.update ()
		return 1

	def xmlrpc_resetjob (self, jobId):
		global State
		output ("Reset job "+str (jobId))
		State.resetJob (jobId)
		State.update ()
		return 1

	def xmlrpc_pausejob (self, jobId):
		global State
		output ("Pause job "+str (jobId))
		State.pauseJob (jobId)
		State.update ()
		return 1

	# update several jobs props at once
	def xmlrpc_updatejobs (self, ids, prop, value):
		global State
		try:
			output ("Update job "+str (ids)+" "+prop+" "+str(value))
		except:
			pass
		for id in ids:
			try:
				job = State.Jobs[id]
				try:
					if prop == "Command":
						job.Command = str (value)
						State._UpdatedDb = True
					elif prop == "Dir":
						job.Dir = str (value)
						State._UpdatedDb = True
					elif prop == "Priority":
						job.Priority = int (value)
						State._UpdatedDb = True
					elif prop == "Affinity":
						State.setAffinity (id, str (value))
					elif prop == "TimeOut":
						job.TimeOut = int (value)
						State._UpdatedDb = True
				except ValueError:
					pass
			except KeyError:
				pass
		State.update ()
		return 1

	def xmlrpc_setjobpriority (self, jobId, priority):
		global State
		output ("Set job "+str (jobId)+" priority to "+str (priority))
		State.setPriority (jobId, priority)
		State.update ()
		return 1

	def xmlrpc_setjobaffinity (self, jobId, affinity):
		global State
		output ("Set job "+str (jobId)+" affinity to "+str (priority))
		State.setAffinity (jobId, affinity)
		State.update ()
		return 1

	def xmlrpc_getlog (self, jobId):
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
		return log

	def xmlrpc_getworkers (self):
		global State
		output ("Send workers")
		workers = []
		for name, worker in State.Workers.iteritems () :
			workers.append (worker)
		return workers

	def xmlrpc_clearworkers (self):
		global State
		output ("Clear workers")
		State.Workers = {}
		State.update ()
		return 1

	def xmlrpc_stopworker (self, workerName):
		global State
		State.stopWorker (workerName)
		State.update ()
		return 1

	def xmlrpc_startworker (self, workerName):
		global State
		State.startWorker (workerName)
		State.update ()
		return 1

	# update several workers props at once
	def xmlrpc_updateworkers (self, names, prop, value):
		global State
		try:
			output ("Update name "+str (names)+" "+prop+" "+str(value))
		except:
			pass
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
		return 1




# Unauthenticated connection for workers
class Workers(xmlrpc.XMLRPC):
	"""    """

	def xmlrpc_heartbeat(self, hostname, jobId, log, load):
		"""Add some logs."""
		global State
		_time = time.time ()
		output ("Heart beat for " + str(jobId))
		# Update the worker load and ping time
		worker = State.getWorker (hostname)
		worker.Load = load
		workingJob = None
		try :
			job = State.Jobs[jobId]
			if job.State == "WORKING" and job.Worker == hostname :
				State.updateWorkerState (hostname, "WORKING")
				workingJob = job
				job.PingTime = _time
				if log != "" :
					try:
						logFile = open (getLogFilename (jobId), "a")
						logFile.write (base64.decodestring(log))
						logFile.close ()
					except IOError:
						output ("Error in logs")
		except KeyError:
			pass
		State.update ()
		if worker.State == "WORKING" and workingJob != None and workingJob.State == "WORKING":
			return True
		# Stop
		output ("Error at " + hostname + " heartbeat, set to WAITING")
		State.updateWorkerState (hostname, "WAITING")
		if workingJob:
			State.updateJobState (jobId, "WAITING")
		return False

	def xmlrpc_pickjobwithaffinity(self, hostname, load, affinity):
		"""A worker ask for a job."""
		global State
		output (hostname + " wants some job")
		worker = State.getWorker (hostname)
		if not worker.Active:
			State.updateWorkerState (hostname, "WAITING")
			return -1,"","",""
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
			if LDAPServer != "":
				return job.ID, job.Command, job.Dir, job.User
			else:
				return job.ID, job.Command, job.Dir, ""

		State.updateWorkerState (hostname, "WAITING")
		State.update ()
		return -1,"","",""

	def xmlrpc_pickjob(self, hostname, load):
		"""A worker ask for a job."""
		return self.xmlrpc_pickjobwithaffinity(hostname, load, None)

	def xmlrpc_endjob(self, hostname, jobId, errorCode):
		"""A worker finished a job."""
		global State
		worker = State.getWorker (hostname)
		output ("End job " + str(jobId) + " with code " + str (errorCode))
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
		return 1




# Write the DB on disk
def saveDb ():
	global State, dataDir
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

# Read the DB from disk
def readDb ():
	global State, dataDir
	output ("Read DB")
	try:
		fo = open(dataDir + "/master_db", "rb")
		try:
			State.read (fo)
		except:
			fo.close()
			print ("Error reading master_db, create a new one")
			State = CState()
	except:
		output ("No db found, create a new one")
		State = CState()
		return
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
	xmlrpc = Master()
	readDb ()
	workers = Workers()
	root.putChild('xmlrpc', xmlrpc)
	root.putChild('workers', workers)
	output ("Listen on port " + str (port))
	reactor.listenTCP(port, server.Site(root))
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
