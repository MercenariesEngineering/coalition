
import sys,re,os

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
	elif sys.platform=="darwin":
		return int(os.popen('/usr/sbin/sysctl -n hw.memsize').read())
	else:
		total, free = parseMemInfo ()
		return total * 1024

def getAvailableMem ():
	if sys.platform=="win32":
	    x = MEMORYSTATUSEX() # create the structure
	    x.dwLength = 8*8;
	    windll.kernel32.GlobalMemoryStatusEx(byref(x)) # from cytypes.wintypes
	    return x.ullAvailPhys
	elif sys.platform=="darwin":
		for line in os.popen('/usr/bin/vm_stat').readlines():
			if line.startswith('Pages free'):
				data = line.split()
				return int(data[2].rstrip('.')) * 4 * 1024
		return 0
	else:
		total, free = parseMemInfo ()
		return free * 1024

