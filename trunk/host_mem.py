import sys
from ctypes import Structure, c_ulonglong
from ctypes.wintypes import DWORD, windll, byref
DWORDLONG = c_ulonglong

if sys.platform=="win32":
	class MEMORYSTATUSEX(Structure):
	    _fields_ = [
					('dwLength', DWORD),
					('dwMemoryLoad', DWORD),
					('ullTotalPhys', DWORDLONG),
					('ullAvailPhys', DWORDLONG),
					('ullTotalPageFile', DWORDLONG),
					('ullAvailPageFile', DWORDLONG),
					('ullTotalVirtual', DWORDLONG),
					('ullAvailVirtual', DWORDLONG),
					('ullAvailExtendedVirtual', DWORDLONG)
					]

def getTotalMem ():
	if sys.platform=="win32":
	    x = MEMORYSTATUSEX() # create the structure
	    x.dwLength = 8*8;
	    windll.kernel32.GlobalMemoryStatusEx(byref(x)) # from cytypes.wintypes
	    return x.ullTotalPhys

def getAvailableMem ():
	if sys.platform=="win32":
	    x = MEMORYSTATUSEX() # create the structure
	    x.dwLength = 8*8;
	    windll.kernel32.GlobalMemoryStatusEx(byref(x)) # from cytypes.wintypes
	    return x.ullAvailPhys
