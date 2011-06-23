import sys, getopt, urllib, httplib, re

global cmd, serverUrl, dir, title, action,id
dir = "."
title = "New job"
startIndex = 1
endIndex = 1
retry = 10
affinity = ""
priority = 1000
timeout = 0
parent = 0
dependencies = ""
id=-1
localprogress=None
globalprogress=None

def usage():
	print ("Usage: control.py [OPTIONS] SERVER_URL ACTION [COMMAND]")
	print ("Control the Coalition server located at SERVER_URL.\n")
	print("Actions:")
	print("  add: add a job, use option -c for command")
	print("  list: list the jobs on the server")
	print("  remove: remove job designated by id, option -i is necessary") 
	print ("Options:")
	print ("  -h, --help\t\tShow this help")
	print ("  -v, --verbose\t\tIncrease verbosity")
	print ("  -c, --cmd=COMMAND\t\tIf action is add, add command to server")
	print ("  -d, --directory=DIR\tWorking directory (default: "+dir+")")
	print ("  -t, --title=TITLE\tSet the job title (default: "+title+")")
	print ("  -p, --priority=PRIORITY\tPriority of the job (default: "+str(priority)+")")
	print ("  -r, --retry=RETRY\tNumber of retry this jobs can do (default: "+str(retry)+")")
	print ("  -a, --affinity=AFFINITY\tAffinity words to workers, separated by a comma (default: \"\"")
	print ("  -i, --jobid=JOBID\tID of the Job")
	print ("  -T, --timeout=TIMEOUT\ttimeout for the job")
	print ("  -D, --dependencies=DEPS\tIDs of the dependent jobs (exemple : \"21 22 23\"")
	print ("  -P, --parent=PARENT\tId of of the parent of the job")
	print ("      --globalprogress=PATTERN\tThe job progression pattern")
	print ("      --localprogress=PATTERN\tThe second job progression pattern")

	print ("\nExample : control -t \"Job\" -a \"Linux\" -c \"echo Hello world!\" http://localhost:8080 add")

# Parse the options
try:
	opts, args = getopt.getopt(sys.argv[1:], "a:d:e:h:r:s:t:v:c:i:D:p:T:P:", ["affinity=", "directory=", "end=", "help", "retry=", "start=", "title=", "verbose=", "command=", "cmd=", "dependencies=", "priority=", "timeout=","parent=","localprogress=","globalprogress="])
	if len(args) != 2 :
		usage()
		sys.exit(2)
	serverUrl = args[0]
        while serverUrl[-1] == '/':
            serverUrl = serverUrl[:-1]
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
	elif o in ("-c", "--command", "--cmd"):
		cmd=a
	elif o in ("-i", "--jobid"):
		id=a
	elif o in ("-D", "--dependencies"):
		dependencies=a
	elif o in ("-T", "--timeout"):
		timeout=int(a)
	elif o in ("-P", "--parent"):
		parent=int(a)
	elif o in ("--localprogress"):
		localprogress = a
	elif o in ("--globalprogress"):
		globalprogress = a
	else:
		assert False, "unhandled option " + o

# Log function
def output (str):
	if verbose:
		print (str)

if action=="add":
	params = urllib.urlencode({'parent':parent, 'title':title, 'cmd':cmd, 'dir':dir, 'priority':priority, 'retry':retry, 'timeout':timeout, 'affinity':affinity, 'dependencies':dependencies, 'localprogress':localprogress, 'globalprogress':globalprogress})
	conn = httplib.HTTPConnection(re.sub("^http://", "", serverUrl))
	conn.request("GET", "/json/addjob?"+params)
	response = conn.getresponse()
	data = response.read()
	conn.close()
	print data
	
elif action=="list":
	params = urllib.urlencode({'id':parent})
	conn = httplib.HTTPConnection(re.sub("^http://", "", serverUrl))
	conn.request("GET", "/json/getjobs?"+params)
	response = conn.getresponse()
	data = response.read()
	conn.close()

	data = eval (data)
	vars=data["Vars"]
	print (vars)
	jobs=data["Jobs"]
	parents=data["Parents"]
	
	parents_info=''
	for i in range(len(parents)):
		parents_info = parents_info+ str(parents[i]["ID"])+" " +str(parents[i]["Title"])+ " > "
	print(parents_info)
	for i in range(len(jobs)):
		for j in range(len(vars)):
			print (jobs[i])
elif action=="remove":
	if id<0: 
		print("Use option -i to specify the job id to remove")
	else:
		params = urllib.urlencode({'id':id})
		conn = httplib.HTTPConnection(re.sub("^http://", "", serverUrl))
		conn.request("GET", "/json/clearjobs?"+params)
		response = conn.getresponse()
		data = response.read()
		conn.close()
else:
	print("I don't know what to do with myself. Use another action")
