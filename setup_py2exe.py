from distutils.core import setup
import py2exe
setup(service=['server','worker'], windows=['win32_network_drives.py'], options = {"py2exe": { "dll_excludes": ["MSWSOCK.dll","POWRPROF.dll"]}})
