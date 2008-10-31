
from twisted.web import xmlrpc, server, static
from twisted.internet import defer
import pickle, time, os, getopt, sys, base64

# This module is standard in Python 2.2, otherwise get it from
#   http://www.pythonware.com/products/xmlrpc/
import xmlrpclib

# Create the logs/ directory
try:
	os.mkdir ("logs", 755);
except OSError:
	pass

global TimeOut, port, verbose
TimeOut = 10
port = 8080
verbose = False

def usage():
	print ("Usage: server [OPTIONS]")
	print ("Start a Coalition server.\n")
	print ("Options:")
	print ("  -h, --help\t\tShow this help")
	print ("  -p, --port=PORT\tPort used by the server (default: "+str(port)+")")
	print ("  -v, --verbose\t\tIncrease verbosity")
	print ("\nExample : server -p 1234")

# Parse the options
try:
	opts, args = getopt.getopt(sys.argv[1:], "hp:v", ["help", "port=", "verbose"])
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
	else:
		assert False, "unhandled option " + o

# Log function
def output (str):
	if verbose:
		print (str)

def getLogFilename (jobId):
	return "logs/" + str(jobId) + ".log"

class Job:
	"""A farm job"""

	def __init__ (self, id, title, cmd, dir, priority, retry, affinity):
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
		self.Retry = retry			# Number of try max
		self.Priority = priority		# Job priority
		self.Affinity = affinity	# Job affinity

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
			if workerWord == jobWord then
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

# State of the master
class CState:

	Counter = 0
	Jobs = []
	Workers = []

	# Read the state
	def read (self, fo):
		version = pickle.load(fo)
		self.Counter = pickle.load(fo)
		self.Jobs = pickle.load(fo)
		self.Workers = pickle.load(fo)

	# Write the state
	def write (self, fo):
		version = 1
		pickle.dump(version, fo)
		pickle.dump(self.Counter, fo)
		pickle.dump(self.Jobs, fo)
		pickle.dump(self.Workers, fo)

class Master(xmlrpc.XMLRPC):
	"""    """
	
	def sortJobs (self):
		self.State.Jobs.sort (compareJobs)

	# Clear a job
	def clearJob (self, jobId):
		# Look for the job
		for i in range(len(self.State.Jobs)) :
			job = self.State.Jobs[i]
			if job.ID == jobId :
				self.State.Jobs.pop (i)
				break;
		# Clear the log	
		try:
			os.remove (getLogFilename(jobId))
		except OSError:
			pass

	def getWorker (self, name):
		found = False
		for i in range(len(self.State.Workers)) :
			worker = self.State.Workers[i]
			if worker.Name == name :
				worker.PingTime = time.time()
				found = True
				return worker
		
		# Job not found, add it
		if not found:
			output ("Add worker " + name)
			worker = Worker (name)
			worker.PingTime = time.time()
			self.State.Workers.append (worker)
			return worker

	def update (self):
		global TimeOut
		self.saveDb ()
		_time = time.time()
		resort = False
		for job in self.State.Jobs:
			if job.State == "WORKING":
				# Check if the job is timeout
				if _time - job.PingTime > TimeOut :
					output ("Job " + str(job.ID) + " timeout")
					job.State = "ERROR"
					worker = self.getWorker (job.Worker)
					worker.State = "TIMEOUT"
					worker.Error = worker.Error+1
					job.Priority = job.Priority-1
					resort = True
				job.Duration = _time - job.StartTime
		if resort:
			self.sortJobs ()

		# Timeout workers
		for worker in self.State.Workers:
			if worker.State != "TIMEOUT" and _time - worker.PingTime > TimeOut:
				worker.State = "TIMEOUT"

	def xmlrpc_addjobwithaffinity(self, title, cmd, dir, priority, retry, affinity):
		"""Show the command list."""
		output ("Add job : " + cmd)
		self.State.Jobs.append (Job(self.State.Counter, title, cmd, dir, priority, retry, affinity))
		self.State.Counter = self.State.Counter + 1
		return 1

	def xmlrpc_addjob(self, title, cmd, dir, priority, retry):
		"""Add a job to job list."""
		return self.xmlrpc_addjobwithaffinity(title, cmd, dir, priority, retry, "")

	def xmlrpc_getjobs(self):
		output ("Send jobs")
		self.update ()
		return self.State.Jobs

	def xmlrpc_clearjobs(self):
		output ("Clear jobs")
		while (len(self.State.Jobs) > 0):
			self.clearJob (self.State.Jobs[0].ID)
		return 1

	def xmlrpc_clearjob(self, jobId):
		output ("Clear job"+str(jobId))
		self.clearJob (jobId)
		return 1

	def xmlrpc_getlog(self, jobId):
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
		output ("Send workers")
		self.update ()
		return self.State.Workers

	def xmlrpc_clearworkers(self):
		output ("Clear workers")
		self.State.Workers = []
		return 1

	def xmlrpc_heartbeat(self, hostname, jobId, log, load):
		"""Add some logs."""
		output ("Heart beat for " + str(jobId))

		# Ping the worker
		worker = self.getWorker (hostname)

		# Update the worker load
		worker.Load = load

		# Look for the job
		for i in range(len(self.State.Jobs)) :
			job = self.State.Jobs[i]
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

	def xmlrpc_pickjobwithaffinity(self, hostname, load, affinity)
		"""A worker ask for a job."""
		output (hostname + " wants some job")
		self.update ()
		# Ping the worker
		worker = self.getWorker (hostname)
		worker.Load = load

		# Look for a job
		for i in range(len(self.State.Jobs)) :
			job = self.State.Jobs[i]
			if compareAffinities (job.Affinity, affinity) and (job.State == "WAITING" or (job.State == "ERROR" and job.Try < job.Retry)):
				job.State = "WORKING"
				job.Worker = hostname
				job.Try = job.Try + 1
				job.PingTime = time.time()
				job.StartTime = job.PingTime
				job.Duration = 0
				worker.State = "WORKING"
				worker.Affinity = affinity
				worker.LastJob = job.ID
				return job.ID, job.Command, job.Dir
		worker.State = "WAITING"
		return -1,"",""

	def xmlrpc_pickjob(self, hostname, load):
		"""A worker ask for a job."""
		return self.xmlrpc_pickjobwithaffinity(hostname, load, "")

	def xmlrpc_endjob(self, hostname, jobId, errorCode):
		"""A worker ask for a job."""
		output ("End job " + str(jobId) + " with code " + str(errorCode))

		# Ping the worker
		worker = self.getWorker (hostname)
		worker.State = "WAITING"

		# Look for a job
		for i in range(len(self.State.Jobs)) :
			job = self.State.Jobs[i]
			if job.ID == jobId:
				if errorCode == 0:
					job.State = "FINISHED"
					worker.Finished = worker.Finished + 1
				else:
					job.State = "ERROR"
					worker.Error = worker.Error + 1
					job.Priority = job.Priority-1
				job.Duration = time.time() - job.StartTime
				self.sortJobs ()
				return 1
		return 1

	# Write the DB on disk
	def saveDb (self):
		fo = open("master_db", "wb")
		self.State.write (fo)
		fo.close()
		output ("DB saved")

	# Read the DB from disk
	def readDb (self):
		output ("Read DB")
		try:
			fo = open("master_db", "rb")
			try:
				self.State.read (fo)
			except IOError:
				fo.close()
				print ("Error reading master_db, create a new one")
				self.State = self.CState()
		except IOError:
			output ("No db found, create a new one")
			return
		# Touch every working job
		_time = time.time()
		for i in range(len(self.State.Jobs)) :
			job = self.State.Jobs[i]
			if job.State == "WORKING":
				job.PingTime = _time
		

	State = CState()

def main():
	from twisted.internet import reactor
	from twisted.web import server
	root = static.File("public_html")
	xmlrpc = Master()
	xmlrpc.readDb ()
	xmlrpc.update ()
	root.putChild('xmlrpc', xmlrpc)
	reactor.listenTCP(port, server.Site(root))
	reactor.run()


if __name__ == '__main__':
	main()
