import worker

# Windows Service
import win32serviceutil
import win32service
import win32event
import servicemanager

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
		self.CheckForQuit()
		main()

	def CheckForQuit(self):
		global gogogo
		retval = win32event.WaitForSingleObject(self.hWaitStop, 10)
		if not retval == win32event.WAIT_TIMEOUT:
			# Received Quit from Win32
			gogogo = False

win32serviceutil.HandleCommandLine(WindowsService)
