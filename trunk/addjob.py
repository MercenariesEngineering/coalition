import xmlrpclib, sys, getopt

global cmd, serverUrl, dir, title
dir = "."
title = "New job"
startIndex = 1
endIndex = 1
retry = 10
priority = 1000

def usage():
	print ("Usage: addjob [OPTIONS] SERVER_URL COMMAND")
	print ("Add a job COMMAND to a Coalition server located at SERVER_URL.\n")
	print ("Options:")
	print ("  -h, --help\t\tShow this help")
	print ("  -d, --directory=DIR\tWorking directory (default: "+dir+")")
	print ("  -t, --title=TITLE\tSet the job title (default: "+title+")")
	print ("  -s, --start=INDEX\tSet the index of the first job (default: "+str(startIndex)+")")
	print ("  -e, --end=INDEX\tSet the index of the last job (default: "+str(endIndex)+")")
	print ("  -p, --priority=PRIORITY\tPriority of the job (default: "+str(priority)+")")
	print ("  -r, --retry=RETRY\tNumber of retry this jobs can do (default: "+str(retry)+")")
	print ("  -v, --verbose\t\tIncrease verbosity")
	print ("\nExample : addjob -t \"Job%04d\" -s 1 -e 10 http://localhost:8080 \"echo Hello world!\"")

# Parse the options
try:
	opts, args = getopt.getopt(sys.argv[1:], "d:e:hr:s:t:v", ["directory=", "end=", "help", "retry=", "start=", "title=", "verbose="])
	if len(args) != 2 :
		usage()
		sys.exit(2)
	serverUrl = args[0]
	cmd = args[1]
except getopt.GetoptError, err:
	# print help information and exit:
	print str(err) # will print something like "option -a not recognized"
	usage()
	sys.exit(2)
for o, a in opts:
	if o in ("-h", "--help"):
		usage()
		sys.exit(2)
	elif o in ("-d", "--directory"):
		dir = a
	elif o in ("-s", "--start"):
		startIndex = int(a)
	elif o in ("-e", "--end"):
		endIndex = int(a)
	elif o in ("-v", "--verbose"):
		verbose = True
	elif o in ("-r", "--retry"):
		retry = int(a)
	elif o in ("-p", "--priority"):
		priority = int(a)
	elif o in ("-t", "--title"):
		title = a
	else:
		assert False, "unhandled option " + o

# Log function
def output (str):
	if verbose:
		print (str)

server = xmlrpclib.ServerProxy(serverUrl + "/xmlrpc")
for i in range(startIndex, endIndex+1):
#	output ("Add job : "+title % i+cmd % i+dir % i)
	def format (s, i):
		try:
			return s % i
		except TypeError:
			return s
	server.addjob (format (title, i), format (cmd, i), format (dir, i), priority, retry)

