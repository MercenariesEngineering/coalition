# Run after the win32 installation : Add to the config file the network drive mapping

import os, win32net

import _winreg
# under windows, uses the registry setup by the installer
hKey = _winreg.OpenKey (_winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Mercenaries Engineering\\Coalition", 0, _winreg.KEY_READ)
coalitionDir, type = _winreg.QueryValueEx (hKey, "Installdir")
os.chdir (coalitionDir)

data = win32net.NetUseEnum (None,0)
drives = data[0]
if len(drives) > 0 :
	# Add the network drives to the config file
	file = open ("coalition.ini", "a")
	file.write ("driveNetwork=")
	for drive in range(len(drives)):
		print str(drives[drive])
		file.write (drives[drive]["local"])
		file.write (",")
		file.write (drives[drive]["remote"])
		file.write (",")
	file.write ("\n")
	file.close ()

