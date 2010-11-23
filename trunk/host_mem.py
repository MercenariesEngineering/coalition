import sys,re

if sys.platform=="win32":
	from ctypes import Structure, c_ulonglong
	from ctypes.wintypes import DWORD, windll, byref
	DWORDLONG = c_ulonglong
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

def parseMemInfo():
	memtotal = 0
	memfree = 0
	buffers = 0
	cached = 0
	file = open ("/proc/meminfo", "r")
	for line in file:
		words = re.split ('\W+', line)
		if len(words) >= 2:
			if words[0] == 'MemTotal':
				memTotal = int(words[1])
			if words[0] == 'MemFree':
				memFree = int(words[1])
			if words[0] == 'Buffers':
				buffers = int(words[1])
			if words[0] == 'Cached':
				cached = int(words[1])
	return memTotal, memFree+buffers+cached


def getTotalMem ():
	if sys.platform=="win32":
	    x = MEMORYSTATUSEX() # create the structure
	    x.dwLength = 8*8;
	    windll.kernel32.GlobalMemoryStatusEx(byref(x)) # from cytypes.wintypes
	    return x.ullTotalPhys
	else:
		total, free = parseMemInfo ()
		return total * 1024

def getAvailableMem ():
	if sys.platform=="win32":
	    x = MEMORYSTATUSEX() # create the structure
	    x.dwLength = 8*8;
	    windll.kernel32.GlobalMemoryStatusEx(byref(x)) # from cytypes.wintypes
	    return x.ullAvailPhys
	else:
		total, free = parseMemInfo ()
		return free * 1024

