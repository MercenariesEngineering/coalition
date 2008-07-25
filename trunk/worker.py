import xmlrpclib, socket, time, popen2, thread, getopt, sys
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

# Log function
def output (str):
	if verbose:
		print (str)

server = xmlrpclib.ServerProxy(serverUrl+"/xmlrpc")

global working
working = False
global errorCode
errorCode = 0

# Current log
global log
log = ""

class JobStop:
	pass

#global lock
#lock = thread.allocate_lock ()

# Thread functio to execute the job process
def execProcess (cmd):
	global working
	global errorCode
	global log
	# Run the job
	process = popen2.Popen3 (cmd, True)
	while (1):
		# Read some lines of logs
		line = process.fromchild.readline()
		
		# "" means EOF
		if line == "":
			print ("end")
			break

		log = log + line

	# Get the error code of the job
	errorCode = process.wait ()

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
			output ("Server down, continue...")
			break
		output ("No server")
		time.sleep (sleepTime)

# Flush the logs to the server
def flushLogs (jobId, retry):
	global log
	output ("Flush logs (" + str(len(log)) + " bytes)")
	def func ():
		global log
		result = server.heartbeat (name, jobId, log)
		log = ""
		if not result:
			output ("Server ask to stop the jod " + str(jobId))
			raise JobStop
	run (func, retry)

# Application main loop
def mainLoop ():
	global working, errorCode, log

	output ("Ask for a job")
	# Function to ask a job to the server
	def startFunc ():
		return server.pickjob (name)

	# Block until this message to handled by the server
	jobId, cmd = run (startFunc, True)

	if jobId != -1:
		output ("Start jod " + str(jobId) + " : " + cmd)
		working = True

		# Launch a new thread to run the process
		thread.start_new_thread ( execProcess, (cmd,))

		try:
			# Flush the logs
			while (working):
				flushLogs (jobId, False)
				time.sleep (sleepTime)

			# Flush for real for the last time
			flushLogs (jobId, True)

			output ("Finished jod " + str(jobId) + " (code " + str(errorCode) + ") : " + cmd)

			# Function to end the job
			def endFunc ():
				server.endjob (name, jobId, errorCode)

			# Block until this message to handled by the server
			run (endFunc, True)
		except JobStop:
			pass

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

