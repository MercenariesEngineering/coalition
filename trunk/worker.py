import xmlrpclib, socket, time, popen2, thread, getopt, sys
from select import select

# Options
global debug, verbose
debug = False
verbose = False

def usage():
	print ("worker [OPTIONS]")
	print ("\t-d --debug\t\tRun without the main try/catch")
	print ("\t-v --verbose\t\tIncrease verbosity")

# Parse the options
try:
	opts, args = getopt.getopt(sys.argv[1:], "dv", ["debug", "verbose"])
except getopt.GetoptError, err:
	# print help information and exit:
	print str(err) # will print something like "option -a not recognized"
	usage()
	sys.exit(2)
for o, a in opts:
	if o in ("-d", "--debug"):
		debug = True
	elif o in ("-v", "--verbose"):
		verbose = True
	else:
		assert False, "unhandled option " + o

# Log function
def output (str):
	if verbose:
		print (str)

hostname = socket.gethostname()
server = xmlrpclib.ServerProxy("http://localhost:8080/xmlrpc")

global working
working = False
global errorCode
errorCode = 0

# Current log
global log
log = ""

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
		output ("Wait for the server")
		time.sleep (2)

# Flush the logs to the server
def flushLogs (jobId, retry):
	global log
	output ("Flush logs (" + str(len(log)) + " bytes)")
	def func ():
		global log
		server.log (hostname, jobId, log)
		log = ""
	run (func, retry)

# Application main loop
def mainLoop ():
	global working, errorCode, log

	output ("Ask for a job")
	# Function to ask a job to the server
	def startFunc ():
		return server.pickjob (hostname)

	# Block until this message to handled by the server
	jobId, cmd = run (startFunc, True)

	if jobId != -1:
		output ("Start jod " + str(jobId) + " : " + cmd)
		working = True

		# Launch a new thread to run the process
		thread.start_new_thread ( execProcess, (cmd,))

		# Flush the logs
		while (working):
			flushLogs (jobId, False)
			time.sleep (2)

		# Flush for real for the last time
		flushLogs (jobId, True)

		output ("Finished jod " + str(jobId) + " (code " + str(errorCode) + ") : " + cmd)

		# Function to end the job
		def endFunc ():
			server.endjob (hostname, jobId, errorCode)

		# Block until this message to handled by the server
		run (endFunc, True)

	time.sleep (2)

while (1):
	if debug:
		mainLoop ()
	else:
		try:
			mainLoop ()		
		except:
			print ("Fatal error, retry...")
			time.sleep (2)

