from __future__ import with_statement
import xmlrpclib, socket, time, popen2, thread, getopt, sys, os, base64, signal
from select import select

# Options
global serverUrl, debug, verbose, sleepTime
serverUrl = ""
debug = False
verbose = False
sleepTime = 2
name = socket.gethostname()

def usage():
	print ("Usage: worker [OPTIONS] SERVER_URL")
	print ("Start a Coalition worker using the server located at SERVER_URL.\n")
	print ("Options:")
	print ("  -d, --debug\t\tRun without the main try/catch")
	print ("  -h, --help\t\tShow this help")
	print ("  -n, --name=NAME\tWorker name (default: "+name+")")
	print ("  -s, --sleep=SLEEPTIME\tSleep time between two heart beats (default: "+str(sleepTime)+"s)")
	print ("  -v, --verbose\t\tIncrease verbosity")
	print ("\nExample : worker -s 30 -v http://localhost:8080")

# Parse the options
try:
	opts, args = getopt.getopt(sys.argv[1:], "dhn:s:v", ["debug", "help", "name=", "sleep=", "verbose"])
	if len(args) != 1 :
		usage()
		sys.exit(2)
	serverUrl = args[0]
except getopt.GetoptError, err:
	# print help information and exit:
	print str(err) # will print something like "option -a not recognized"
	usage()
	sys.exit(2)
for o, a in opts:
	if o in ("-d", "--debug"):
		debug = True
	elif o in ("-h", "--help"):
		usage()
		sys.exit(2)
	elif o in ("-n", "--name"):
		name = a
	elif o in ("-v", "--verbose"):
		verbose = True
	elif o in ("-s", "--sleep"):
		sleepTime = float(a)
	else:
		assert False, "unhandled option " + o

# Log for debugging
def debug (str):
	if verbose:
		print (str)

# Log for debugging
def debugRaw (str):
	if verbose:
		print (str),

# Add to the logs
def info (str):
	global gLog, gLogLock
	with gLogLock:
		gLog = gLog + "WORKER: " + str + "\n";
	if verbose:
		print (str)
	

server = xmlrpclib.ServerProxy(serverUrl+"/xmlrpc")

global working, pid
working = False
pid = 0
global errorCode
errorCode = 0

# Lock for mutual exclusion on the logs
global gLogLock
gLogLock = thread.allocate_lock()

# Current log
global gLog
gLog = ""

#global lock
#lock = thread.allocate_lock ()

# Thread function to execute the job process
def execProcess (cmd,dir):
	global working,  errorCode, gLog, pid

	# Set the working directory
	try:
		os.chdir (dir)
	except OSError:
		info ("Can't set the directory to: " + dir)

	# Run the job
	info ("exec " + cmd)
	process = popen2.Popen4 ("exec "+cmd)

	# Get the pid
	pid = int(process.pid)
	while (1):
		# Read some lines of logs
		line = process.fromchild.readline()
		
		# "" means EOF
		if line == "":
			print ("end")
			break

		debugRaw (line)
		with gLogLock:
			gLog = gLog + line

	# Get the error code of the job
	errorCode = process.wait ()
	info ("Job returns code: " + str(errorCode))

	# Signal to the main process the job is finished
	working = False

# Safe method to run a command on the server, if retry is true, the function won't return until the message is passed
def run (func, retry):
	while (True):
		try:
			return func ()
		except socket.error:
			pass
		if not retry:
			debug ("Server down, continue...")
			break
		debug ("No server")
		time.sleep (sleepTime)

# Flush the logs to the server
def heartbeat (jobId, retry):
	global gLog, pid, gLogLock
	debug ("Flush logs (" + str(len(gLog)) + " bytes)")
	def func ():
		global gLog
		result = True
		with gLogLock:
			result = server.heartbeat (name, jobId, base64.encodestring(gLog), os.getloadavg())
			gLog = ""
		if not result:
			debug ("Server ask to stop the jod " + str(jobId))

			# Send the kill signal to the process
			if pid != 0:
				debug ("kill "+str(pid)+" "+str(signal.SIGKILL))
				try:
					os.kill (pid, signal.SIGKILL)
				except OSError:
					pass
	run (func, retry)

# Application main loop
def mainLoop ():
	global working, errorCode, gLog, pid

	debug ("Ask for a job")
	# Function to ask a job to the server
	def startFunc ():
		return server.pickjob (name, os.getloadavg())

	# Block until this message to handled by the server
	jobId, cmd, dir = run (startFunc, True)

	if jobId != -1:
		debug ("Start jod " + str(jobId) + " : " + cmd)

		# Reset the globals
		working = True
		stop = False
		pid = 0

		# Launch a new thread to run the process
		gLog = ""
		thread.start_new_thread ( execProcess, (cmd,dir,))

		# Flush the logs
		while (working):
			heartbeat (jobId, False)
			time.sleep (sleepTime)

		# Flush for real for the last time
		heartbeat (jobId, True)

		debug ("Finished jod " + str(jobId) + " (code " + str(errorCode) + ") : " + cmd)

		# Function to end the job
		def endFunc ():
			server.endjob (name, jobId, errorCode)

		# Block until this message to handled by the server
		run (endFunc, True)

	time.sleep (sleepTime)

while (1):
	if debug:
		mainLoop ()
	else:
		try:
			mainLoop ()		
		except:
			print ("Fatal error, retry...")
			time.sleep (sleepTime)

