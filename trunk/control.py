import xmlrpclib, sys, getopt

global cmd, serverUrl, dir, title, action,id
dir = "."
title = "New job"
startIndex = 1
endIndex = 1
retry = 10
affinity = ""
priority = 1000
dependencies = ""
id=-1

def usage():
	print ("Usage: control.py [OPTIONS] SERVER_URL ACTION [COMMAND]")
	print ("Control the Coalition server located at SERVER_URL.\n")
	print("Actions:")
	print("  add: add a job, use option -c for command")
	print("  list: list the jobs on the server")
	print("  remove: remove job designated by id, option -id is necessary") 
	print ("Options:")
	print ("  -h, --help\t\tShow this help")
	print ("  -c, --command=COMMAND\t\tIf action is add, add command to server")
	print ("  -d, --directory=DIR\tWorking directory (default: "+dir+")")
	print ("  -t, --title=TITLE\tSet the job title (default: "+title+")")
	print ("  -p, --priority=PRIORITY\tPriority of the job (default: "+str(priority)+")")
	print ("  -r, --retry=RETRY\tNumber of retry this jobs can do (default: "+str(retry)+")")
	print ("  -a, --affinity=AFFINITY\tAffinity words to workers, separated by a comma (default: \"\"")
	print("   -i, --jobid=JOBID\tID of the Job")
	print("   -D, --dependencies=DEPS\tIDs of the dependent jobs (exemple : \"21 22 23\"")
	print ("  -v, --verbose\t\tIncrease verbosity")

	print ("\nExample : control -t \"Job\" -a \"Linux\" -c \"echo Hello world!\" http://localhost:8080 add")

# Parse the options
try:
	opts, args = getopt.getopt(sys.argv[1:], "a:d:e:hr:s:t:v:c:i:D:", ["affinity=", "directory=", "end=", "help", "retry=", "start=", "title=", "verbose=", "command=", "dependencies="])
	if len(args) != 2 :
		usage()
		sys.exit(2)
	serverUrl = args[0]
	action = args[1]
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
	elif o in ("-a", "--affinity"):
		affinity = a
	elif o in ("-t", "--title"):
		title = a
	elif o in ("-c", "--command"):
		cmd=a
	elif o in ("-i", "--jobid"):
		id=a
	elif o in ("-D", "--dependencies"):
		dependencies=a
	else:
		assert False, "unhandled option " + o

# Log function
def output (str):
	if verbose:
		print (str)

server = xmlrpclib.ServerProxy(serverUrl + "/xmlrpc")

if action=="add":
	server.addjob (title, cmd, dir, priority, retry, affinity, dependencies)
	print("job added")
elif action=="list":
	jobs=server.getjobs()
	for i in range(len(jobs)):
		print(str(jobs[i]["ID"])+" "+str(jobs[i]["Title"])+" "+str(jobs[i]["State"])+" "+str(jobs[i]["Priority"])+" "+str(jobs[i]["Affinity"])+" "+str(jobs[i]["Worker"])+" "+str(jobs[i]["Duration"])+" "+str(jobs[i]["Try"])+" "+str(jobs[i]["Command"])+" "+str(jobs[i]["Dir"]))
elif action=="remove":
	if id<0: 
		print("Use option -id to specify the job id to remove")
	else:
		server.clearjob(int(id))
else:
	print("I don't know what to do with myself. Use another action")
