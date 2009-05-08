import xmlrpclib, socket, time, subprocess, thread, getopt, sys, os, base64, signal, string, re, platform, ConfigParser

# Options
global serverUrl, debug, verbose, sleepTime, broadcastPort, gogogo, xmlrpcServer
debug = False
verbose = False
sleepTime = 2
affinity = ""
name = socket.gethostname()
broadcastPort = 19211
workerMonitorPort = 19212
gogogo = True
serverUrl = ""


# Go to the script directory
global coalitionDir
if sys.platform=="win32":
	import _winreg
	# under windows, uses the registry setup by the installer
	hKey = _winreg.OpenKey (_winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Mercenaries Engineering\\Coalition", 0, _winreg.KEY_READ)
	coalitionDir, type = _winreg.QueryValueEx (hKey, "Installdir")
else:
	coalitionDir = "."
os.chdir (coalitionDir)

# Read the config file
config = ConfigParser.SafeConfigParser()
config.read ("coalition.ini")
if config.has_option('worker', 'serverUrl'):
	serverUrl = config.get('worker', 'serverUrl')

def usage():
	print ("Usage: worker [OPTIONS] [SERVER_URL]")
	print ("Start a Coalition worker using the server located at SERVER_URL.")
	print ("If no SERVER_URL is specified, the worker will try to locate the server using a broadcast.\n")
	print ("Options:")
	print ("  -d, --debug\t\tRun without the main try/catch")
	print ("  -h, --help\t\tShow this help")
	print ("  -n, --name=NAME\tWorker name (default: "+name+")")
	print ("  -s, --sleep=SLEEPTIME\tSleep time between two heart beats (default: "+str(sleepTime)+"s)")
	print ("  -a, --affinity=AFFINITY\tAffinity words to jobs (default: \"\"")
	print ("  -v, --verbose\t\tIncrease verbosity")
	print ("\nExample : worker -s 30 -v http://localhost:8080")

if sys.platform!="win32":
	# Parse the options
	try:
		opts, args = getopt.getopt(sys.argv[1:], "a:dhn:s:v", ["affinity=", "debug", "help", "name=", "sleep=", "verbose"])
		if len(args) > 0:
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
		elif o in ("-a", "--affinity"):
			affinity = a
		elif o in ("-v", "--verbose"):
			verbose = True
		elif o in ("-s", "--sleep"):
			sleepTime = float(a)
		else:
			assert False, "unhandled option " + o

# Log for debugging
def debugOutput (str):
	if verbose:
		print (str)

# Log for debugging
def debugRaw (str):
	if verbose:
		print (str),

# Add to the logs
def info (str):
	global gLog, gLogLock
	gLogLock.acquire()
   	try:
		gLog = gLog + "WORKER: " + str + "\n";
		if verbose:
			print (str)
  	finally:
		gLogLock.release()

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
def _execProcess (cmd,dir,user):
	global errorCode, gLog, pid

	# Change the user ?
	if user != "":
		debugOutput ("Run the command using login " + user)
		#os.seteuid (pwd.getpwnam(user)[2])
		cmd = "su - " + user + " -c \"" + "cd "+ dir + "; " +cmd + "\""
	else:
		# Set the working directory
		try:
			os.chdir (dir)
		except OSError:
			info ("Can't change dir to "+dir)

	# Run the job
	info ("exec " + cmd)

	process = subprocess.Popen (cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

	# Get the pid
	pid = int(process.pid)
	while (1):
		# Read some lines of logs
		line = process.stdout.readline()
	
		# "" means EOF
		if line == "":
			info ("end")
			break

		debugRaw (line)
		gLogLock.acquire()
   		try:
        		gLog = gLog + line
   		finally:
         		gLogLock.release()
		
	# Get the error code of the job
	errorCode = process.wait ()
	info ("Job returns code: " + str(errorCode))
	

def execProcess (cmd,dir,user):
	global working, errorCode
	if debug:
		_execProcess (cmd,dir,user)
	else:
		try:
			_execProcess (cmd,dir,user)	
		except:
			errorCode = -1
			print ("Fatal error executing the job...")
			time.sleep (sleepTime)

	# Signal to the main process the job is finished
	working = False

### To kill all child process
def killr (pid, sig): 
	if sys.platform!="win32":
		names=os.listdir("/proc/")
		for name in names:
			try:
				f = open("/proc/" + name +"/stat","r")
				line = f.readline()
				words =  string.split(line)
				if words[3]==str(pid):
					debugOutput("Found in " + name)
					killr(int(name), sig)
			except IOError:
				pass
			
		
	try:
		os.kill(pid,sig)
	except:
		pass
		
	




# Safe method to run a command on the server, if retry is true, the function won't return until the message is passed
def run (func, retry):
	global gogogo
	while (gogogo):
		try:
			return func ()
		except socket.error:
			pass
		if not retry:
			debugOutput ("Server down, continue...")
			break
		debugOutput ("No server")
		if gogogo:
			time.sleep (sleepTime)

# Flush the logs to the server
def heartbeat (jobId, retry):
	global gLog, pid, gLogLock, xmlrpcServer
	debugOutput ("Flush logs (" + str(len(gLog)) + " bytes)")
	def func ():
		global gLog
		result = True

		gLogLock.acquire()
   		try:
        		result = xmlrpcServer.heartbeat (name, jobId, base64.b64encode(gLog), getloadavg())
			gLog = ""
   		finally:
         		gLogLock.release()
		
			
		if not result:
			debugOutput ("Server ask to stop the jod " + str(jobId))

			# Send the kill signal to the process
			if pid != 0:
				debugOutput ("kill "+str(pid)+" "+str(signal.SIGKILL))
				try:
					killr (pid, signal.SIGKILL)
				except OSError:
					debugOutput ("kill failed")
					pass
	run (func, retry)

# LoadAvg
def getloadavg ():
	try:
		return os.getloadavg ()
	except:
		return -1

def evalEnv (_str):
	if platform.system () != 'Windows':
		def _mapDrive (match):
			return '$(' + match.group(1).upper () + '_DRIVE)'
		_str = re.sub ('^([a-zA-Z]):', _mapDrive, _str)
	def _getenv (match):
		result = os.getenv (match.group(1))
		if result == None:
			info ("Environment variable not found : " + match.group(1))
			result = ""
		return result
	return re.sub ('\$\(([^)]*)\)', _getenv, _str)

# Application main loop
def mainLoop ():
	global working, errorCode, gLog, pid, xmlrpcServer

	debugOutput ("Ask for a job")
	# Function to ask a job to the server
	def startFunc ():
		return xmlrpcServer.pickjobwithaffinity (name, getloadavg(), affinity)

	# Block until this message to handled by the server
	jobId, cmd, dir, user = run (startFunc, True)

	if jobId != -1:
		_cmd = evalEnv (cmd)
		_dir = evalEnv (dir)
		debugOutput ("Start jod " + str(jobId) + " in " + _dir + " : " + _cmd)

		# Reset the globals
		working = True
		stop = False
		pid = 0

		# Launch a new thread to run the process
		gLog = ""
		thread.start_new_thread ( execProcess, (_cmd,_dir,user))

		# Flush the logs
		while (working):
			heartbeat (jobId, False)
			time.sleep (sleepTime)

		# Flush for real for the last time
		heartbeat (jobId, True)

		debugOutput ("Finished jod " + str(jobId) + " (code " + str(errorCode) + ") : " + _cmd)

		# Function to end the job
		def endFunc ():
			xmlrpcServer.endjob (name, jobId, errorCode)

		# Block until this message to handled by the server
		run (endFunc, True)

	time.sleep (sleepTime)

def main():
	global xmlrpcServer, serverUrl, gogogo

	# If no server, look for it with a broadcast
	if serverUrl == "":
		from socket import SOL_SOCKET, SO_BROADCAST
		from socket import socket, AF_INET, SOCK_DGRAM, timeout

		s = socket (AF_INET, SOCK_DGRAM)
		s.setsockopt(SOL_SOCKET, SO_BROADCAST, True)
		s.bind (('0.0.0.0', 0))
		s.settimeout (1)
		while (gogogo):
			try:
				debugOutput ("Broadcast port " + str (broadcastPort))
				s.sendto ("coalition", ('255.255.255.255', broadcastPort))
				data, addr = s.recvfrom (1024)
				if data == "roxor":
					serverUrl = "http://" + addr[0] + ":" + str(broadcastPort)
					debugOutput ("Found : " + serverUrl)
					found = True
					break
			except timeout:
				pass
		s.close ()

	xmlrpcServer = xmlrpclib.ServerProxy(serverUrl+"/workers")

	while gogogo:
		if debug:
			mainLoop ()
		else:
			try:
				mainLoop ()		
			except:
				print ("Fatal error, retry...")
				if gogogo:
					time.sleep (sleepTime)

if sys.platform=="win32":

	# Windows Service
	import win32serviceutil
	import win32service
	import win32event

	class WindowsService(win32serviceutil.ServiceFramework):
		_svc_name_ = "CoalitionWorker"
		_svc_display_name_ = "Coalition Worker"

		def __init__(self, args):
			win32serviceutil.ServiceFramework.__init__(self, args)
			self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

		def SvcStop(self):
			global gogogo
			gogogo = False
			self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
			win32event.SetEvent(self.hWaitStop)

		def SvcDoRun(self):
			import servicemanager

			self.CheckForQuit()
			main()

		def CheckForQuit(self):
			global gogogo
			print ("CheckForQuit")
			retval = win32event.WaitForSingleObject(self.hWaitStop, 10)
			if not retval == win32event.WAIT_TIMEOUT:
				# Received Quit from Win32
				gogogo = False

	if __name__=='__main__':
		win32serviceutil.HandleCommandLine(WindowsService)
else:
	main()
