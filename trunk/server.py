
from twisted.web import xmlrpc, server, static
from twisted.internet import defer
import pickle, time, os, getopt, sys

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
	print ("  -p, --port=PORT\tPort used by the server (default: "+str(port)+")")
	print ("  -h, --help\t\tShow this help")
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

class Job:
	"""A farm job"""

	def __init__ (self, id, title, cmd):
		self.ID = id				# Jod ID
		self.Title = title			# Job title
		self.Command = cmd			# Job command to execute
		self.State = "WAITING"			# Job state, can be WAITING, WORKING, FINISHED or ERROR
		self.Worker = ""			# Worker hostname
		self.StartTime = time.time()		# Start working time 
		self.PingTime = self.StartTime		# Last worker ping time
		self.Try = 0				# Number of try

class Worker:
	"""A farm worker"""

	def __init__ (self, name):
		self.Name = name			# Worker name
		self.State = "WAITING"			# Job state, can be WAITING, WORKING, FINISHED or TIMEOUT
		self.PingTime = time.time()		# Last worker ping time
		self.Finished = 0			# Number of finished
		self.Error = 0				# Number of fault
		self.LastJob = -1			# Last job done

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

		for job in self.State.Jobs:
			# Check if the job is timeout
			if job.State == "WORKING" and _time - job.PingTime > TimeOut :
				output ("Job " + str(job.ID) + " timeout")
				job.State = "ERROR"
				worker = self.getWorker (job.Worker)
				worker.State = "TIMEOUT"
				worker.Error = worker.Error+1

#		output ("Jobs:")
#		for job in self.State.Jobs:
#			# output the job
#			output ("\t"+str(job.ID)+" "+job.Title+" \""+job.Command+"\" "+job.State+" "+job.Worker+" "+str(job.Try)+" try")

	def xmlrpc_addjob(self, title, cmd):
		"""Show the command list."""
		output ("Add job : " + cmd)
		self.State.Jobs.append (Job(self.State.Counter, title, cmd))
		self.State.Counter = self.State.Counter + 1
		self.update ()
		return 1

	def xmlrpc_getjobs(self):
		output ("Send jobs")
		self.update ()
		return self.State.Jobs

	def xmlrpc_clearjobs(self):
		output ("Clear jobs")
		self.State.Jobs = []
		self.update ()
		return 1

	def xmlrpc_clearjob(self, jobId):
		output ("Clear job"+str(jobId))
		# Look for the job
		for i in range(len(self.State.Jobs)) :
			job = self.State.Jobs[i]
			if job.ID == jobId :
				self.State.Jobs.pop (i)
				break;
		self.update ()
		return 1

	def xmlrpc_getworkers(self):
		output ("Send workers")
		self.update ()
		return self.State.Workers

	def xmlrpc_clearworkers(self):
		output ("Clear workers")
		self.State.Workers = []
		self.update ()
		return 1

	def xmlrpc_heartbeat(self, hostname, jobId, log):
		"""Add some logs."""
		output ("Heart beat for " + str(jobId))

		# Ping the worker
		worker = self.getWorker (hostname)

		# Look for the job
		for i in range(len(self.State.Jobs)) :
			job = self.State.Jobs[i]
			if job.ID == jobId and job.State == "WORKING" and job.Worker == hostname:
				if log != "" :
					job.PingTime = time.time()
					try:
						logFile = open ("logs/" + str(jobId) + ".log", "a")
						logFile.write (log)
						logFile.close ()
					except IOError:
						output ("Error in logs")
				# Continue
				return True
		# Stop
		worker.State = "WAITING"
		return False

	def xmlrpc_pickjob(self, hostname):
		"""A worker ask for a job."""
		output (hostname + " wants some job")

		# Ping the worker
		worker = self.getWorker (hostname)

		# Look for a job
		for i in range(len(self.State.Jobs)) :
			job = self.State.Jobs[i]
			if job.State == "WAITING":
				job.State = "WORKING"
				job.Worker = hostname
				job.Try = job.Try + 1
				job.PingTime = time.time()
				self.update ()
				worker.State = "WORKING"
				worker.LastJob = job.ID
				return job.ID, job.Command
		self.update ()
		return -1,""

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
					job.State =	"FINISHED"
					worker.Finished = worker.Finished + 1
				else:
					job.State =	"ERROR"
					worker.Error = worker.Error + 1

				self.update ()
				return 1
		self.update ()
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
