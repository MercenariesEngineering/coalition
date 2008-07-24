
from twisted.web import xmlrpc, server, static
from twisted.internet import defer
import pickle, time

# This module is standard in Python 2.2, otherwise get it from
#   http://www.pythonware.com/products/xmlrpc/
import xmlrpclib

global TimeOut
TimeOut = 10

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

# State of the master
class CState:

	Counter = 0
	Jobs = []

	# Read the state
	def read (self, fo):
		version = pickle.load(fo)
		self.Counter = pickle.load(fo)
		self.Jobs = pickle.load(fo)

	# Write the state
	def write (self, fo):
		version = 1
		pickle.dump(version, fo)
		pickle.dump(self.Counter, fo)
		pickle.dump(self.Jobs, fo)

class Master(xmlrpc.XMLRPC):
	"""    """

	def update (self):
		global TimeOut
		self.saveDb ()
		_time = time.time()

		for job in self.State.Jobs:
			# Check if the job is timeout
			if job.State == "WORKING" and _time - job.PingTime > TimeOut :
				print ("Job " + str(job.ID) + " timeout")
				job.State = "WAITING"

		print ("Jobs:")
		for job in self.State.Jobs:
			# Print the job
			print ("\t"+str(job.ID)+" "+job.Title+" \""+job.Command+"\" "+job.State+" "+job.Worker+" "+str(job.Try)+" try")

	def xmlrpc_addjob(self, title, cmd):
		"""Show the command list."""
		print ("Add job : " + cmd)
		self.State.Jobs.append (Job(self.State.Counter, title, cmd))
		self.State.Counter = self.State.Counter + 1
		self.update ()
		return 1

	def xmlrpc_getjobs(self):
		return self.State.Jobs

	def xmlrpc_log(self, hostname, jobId, log):
		"""Add some logs."""
		print ("Logs for " + str(jobId))
		# Look for a job
		if log != "" :
			for i in range(len(self.State.Jobs)) :
				job = self.State.Jobs[i]
				if job.ID == jobId and job.State == "WORKING" and job.Worker == hostname:
					job.PingTime = time.time()
					logFile = open ("logs/" + str(jobId) + ".log", "a")
					logFile.write (log)
					logFile.close ()
					return 1
		return 1

	def xmlrpc_pickjob(self, hostname):
		"""A worker ask for a job."""
		print (hostname + " wants some job")
		# Look for a job
		for i in range(len(self.State.Jobs)) :
			job = self.State.Jobs[i]
			if job.State == "WAITING":
				job.State =	"WORKING"
				job.Worker = hostname
				job.Try = job.Try + 1
				job.PingTime = time.time()
				self.update ()
				return job.ID, job.Command
		self.update ()
		return -1,""

	def xmlrpc_endjob(self, hostname, jobId, errorCode):
		"""A worker ask for a job."""
		print (hostname + " wants some job")
		# Look for a job
		for i in range(len(self.State.Jobs)) :
			job = self.State.Jobs[i]
			if job.ID == jobId:
				if errorCode == 0:
					job.State =	"FINISHED"
				else:
					job.State =	"ERROR"
				self.update ()
				return 1
		self.update ()
		return ""

	# Write the DB on disk
	def saveDb (self):
		fo = open("master_db", "wb")
		self.State.write (fo)
		fo.close()
		print ("DB saved")

	# Read the DB from disk
	def readDb (self):
		print ("Read DB")
		try:
			fo = open("master_db", "rb")
			try:
				self.State.read (fo)
			except IOError:
				fo.close()
				print ("Error reading master_db, create a new one")
				self.State = self.CState()
		except IOError:
			print ("No db found, create a new one")
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
	reactor.listenTCP(8080, server.Site(root))
	reactor.run()


if __name__ == '__main__':
	main()
