import xmlrpclib, sys

server = xmlrpclib.ServerProxy("http://localhost:8080/xmlrpc")

# Build a command line
cmd = ""
for i in range(len(sys.argv)):
	if i > 1 :
		if i > 2:
			cmd = cmd + " "
		cmd = cmd + sys.argv[i]

if cmd == "" :
	print ("addjob job_title job_command")
else:
	server.addjob (sys.argv[1], cmd)
