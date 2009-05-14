import _winreg, os, re, os.path

compile = True
buildNsis = True

# under windows, uses the registry setup by the installer
hKey = _winreg.OpenKey (_winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\NSIS", 0, _winreg.KEY_READ)
NSISDir, type = _winreg.QueryValueEx (hKey, "")
print ("NSIS found here : " + NSISDir)

# Stop the services
os.system ("net stop CoalitionServer")

# Compile the services
# os.chdir ("../..")
if compile:
	os.system ("python server.py remove")
	os.system ("python setup_py2exe.py install")
	os.system ("python setup_py2exe.py py2exe")

if buildNsis:
	# Generates the NSIS script
	f = open ("install/win32/coalition.nsi", "r")
	script = f.read ()
	f.close ()

	installFiles = ""
	removeFiles = ""
	currentDir = ""
	currentPath = ""

	def setOutPath (path, goin):
		global installFiles, removeFiles, currentDir, currentPath
		currentPath = path
		currentDir = path == "" and "$INSTDIR" or ("$INSTDIR\\" + path)
		installFiles = installFiles + "\tSetOutPath \"" + currentDir + "\"\n"
		if goin:
			removeFiles = "\tRMDir \"" + currentDir + "\"\n" + removeFiles

	def addFile (localpath):
		global installFiles, removeFiles, currentDir
		currentFile = currentDir + "\\" + os.path.basename (localpath)
		installFiles = installFiles + "\tFile \"" + localpath + "\"\n"
		removeFiles = "\tDelete \"" + currentFile + "\"\n" + removeFiles

	def addFiles (localpath, rec):
		global currentPath
		for file in os.listdir(localpath):
			filename = localpath + "\\" + file
			if os.path.isdir (filename):
				if rec and file != ".svn":
					oldpath = currentPath
					setOutPath (currentPath + "\\" + file, True)
					addFiles (filename, rec)
					setOutPath (oldpath, False)
			else:
				addFile (filename)

	setOutPath ("", True)
	addFile ("coalition.ini")
	addFile ("images\coalition.ico")
	addFile ("images\server_start.ico")
	addFile ("images\server_stop.ico")
	addFile ("images\worker_start.ico")
	addFile ("images\worker_stop.ico")
	addFiles ("dist", True)
	setOutPath ("public_html", True)
	addFiles ("public_html", True)

	installFiles = re.sub ("\\\\", "\\\\\\\\", installFiles)
	script = re.sub ("__INSTALL_FILES__", installFiles, script)
	removeFiles = re.sub ("\\\\", "\\\\\\\\", removeFiles)
	script = re.sub ("__REMOVE_FILES__", removeFiles, script)

	f = open ("_coalition.nsi", "w")
	f.write (script)
	f.close ()

	# Run NSIS
	os.system ("\"" + NSISDir + "/makensis.exe\" _coalition.nsi")

