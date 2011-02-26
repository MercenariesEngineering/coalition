from distutils.core import setup
import py2exe
setup(service=['server', 'worker_service'], console=['worker.py','control.py'], options = {"py2exe": { "dll_excludes": ["MSWSOCK.dll","POWRPROF.dll"]}})
