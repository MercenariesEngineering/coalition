import time

class DB(object):
	def __init__(self):
		self.IntoWith = False

	'''Enter a transaction block'''
	def __enter__(self):

		# Jobs is a map between job.ID and the actual job proxy
		# This cache is erased after each transaction
		self.Jobs = {}

		# Those map are the edits done on every objects to commit at the end of the transaction
		self.JobsToUpdate = {}
		self.WorkersToUpdate = {}
		self.EventsToUpdate = {}

		self.IntoWith = True

	'''Leave a transaction block'''
	def __exit__ (self, type, value, traceback):
		self.IntoWith = False
		if not isinstance(value, TypeError):
			self.edit (self.JobsToUpdate, self.WorkersToUpdate, self.EventsToUpdate)

	def getRoot (self):
		return Job (self, 0, 0, "Root", "", "", "", "", "", 0, 0, 0, 0, 0, 0,  0, "", "", 0, 0, 0, 0, 0, 0, 0, "", "", "")

class Event(object):
	'''
	The database proxy object for an event

	This object is readonly outside a transaction block.
	'''
	def __init__ (self, db, id, worker, job, jobTitle, state, start, duration):
		self.__initialized = False
		self.DB = db
		self.ID = id
		self.Worker = worker
		self.JobID = job
		self.JobTitle = jobTitle
		self.State = state
		self.Start = start
		self.Duration = duration

		# Can't write anymore
		self.__initialized=True

	# The setattr method is override after the init to crash if used
	def __setattr__(self, attr, value):
		if attr != "_Event__initialized":
			if self.__initialized:
				# Backup the value for delayed writting
				if self.DB.IntoWith:
					w = self.DB.EventsToUpdate.get(self.ID)
					if not w:
						w = {}
						self.DB.EventsToUpdate[self.ID] = w
					w[attr] = value
				else:
					raise Exception
		super(Event, self).__setattr__(attr, value)

class Worker(object):
	'''
	The database proxy object for a worker

	This object is readonly outside a transaction block.
	'''
	def __init__ (self, db, name, ip, affinity, state, pingTime, finished, error, lastJob, currentActivity, cpu, freeMemory, totalMemory, active):
		self.__initialized = False
		self.DB = db
		self.Name=name
		self.IP=ip
		self.Affinity=affinity
		self.State=state
		self.PingTime=pingTime
		self.Finished=finished
		self.Error=error
		self.LastJob=lastJob
		self.CurrentActivity=currentActivity
		self.CPU=cpu
		self.FreeMemory=freeMemory
		self.TotalMemory=totalMemory
		self.Active=active

		# Can't write anymore
		self.__initialized=True

	# The setattr method is override after the init to crash if used
	def __setattr__(self, attr, value):
		if attr != "_Worker__initialized":
			if self.__initialized:
				# Backup the value for delayed writting
				if self.DB.IntoWith:
					w = self.DB.WorkersToUpdate.get(self.Name)
					if not w:
						w = {}
						self.DB.WorkersToUpdate[self.Name] = w
					w[attr] = value
				else:
					raise Exception
		super(Worker, self).__setattr__(attr, value)

class Job(object):
	'''
	The database proxy object for a job

	This object is readonly outside a transaction block.
	'''
	def __init__ (self, db, id, parent, title, command, dir, environment, state, worker, starttime, duration, pingtime, _try, retry, timeout, 
		priority, affinity, user, finished, errors, working, total, totalfinished, totalerrors, totalworking, url, localprogress, globalprogress):
		self.__initialized = False
		self.DB = db						# The database
		self.ID = id						# Job ID
		self.Parent = parent				# Parent Job ID
		self.Title = title					# Job title
		self.Command = command				# Job command to execute
		self.Dir = dir						# Job working directory
		self.Environment = environment		# Job environment
		self.State = state					# Job state, can be WAITING, WORKING, PAUSED, FINISHED or ERROR
		self.Worker = worker				# Worker hostname
		self.StartTime = starttime			# Start working time 
		self.Duration = duration			# Duration of the process
		self.PingTime = pingtime			# Last worker ping time
		self.Try = _try						# Number of try
		self.Retry = retry					# Number of try max
		self.TimeOut = timeout				# Timeout in seconds
		self.Priority = priority			# Job priority
		self.Affinity = affinity			# Job affinity
		self.User = user					# Job user
		self.Finished = finished			# Number of finished children
		self.Errors = errors				# Number of error children
		self.Working = working				# Number of children working
		self.Total = total					# Total number of (grand)children
		self.TotalFinished = totalfinished	# Total number of (grand)children finished
		self.TotalErrors = totalerrors		# Total number of (grand)children in error
		self.TotalWorking = totalworking	# Total number of children working
		self.URL = url						# URL to open
		self.LocalProgress = localprogress
		self.GlobalProgress = globalprogress
		self.__initialized = True

		# Should not exist in the cache
		assert (db.Jobs.get (self.ID) == None)
		# Cache it
		db.Jobs[self.ID] = self

	def hasChildren (self):
		return self.DB.hasJobChildren (self.ID)

	def getDependencies (self):
		return self.DB.getJobDependencies (self.ID)

	# The setattr method is override after the init to crash if used
	def __setattr__(self, attr, value):
		if attr != "_Job__initialized":
			if self.__initialized:
				# Backup the value for delayed writting
				if self.DB.IntoWith and self.ID != 0:
					w = self.DB.JobsToUpdate.get(self.ID)
					if not w:
						w = {}
						self.DB.JobsToUpdate[self.ID] = w
					w[attr] = value
				else:
					raise Exception
		super(Job, self).__setattr__(attr, value)

"""
	def __init__ (self, title, cmd = "", dir = "", environment = None, priority = 1000, retry = 10, timeout = 0, affinity = "", user = "", localprogress = '', globalprogress = ''):
		self.__initialized = False
		self.ID = None						# Job ID
		self.Parent = None					# Parent Job ID
		self.Title = title					# Job title
		self.Command = cmd					# Job command to execute
		self.Dir = dir						# Job working directory
		self.Environment = environment		# Job environment
		self.State = "WAITING"				# Job state, can be WAITING, WORKING, FINISHED or ERROR
		self.Worker = ""					# Worker hostname
		self.StartTime = time.time()		# Start working time 
		self.Duration = 0					# Duration of the process
		self.PingTime = self.StartTime		# Last worker ping time
		self.Try = 0						# Number of try
		self.Retry = strToInt (retry)		# Number of try max
		self.TimeOut = strToInt (timeout)	# Timeout in seconds
		self.Priority = strToInt (priority)	# Job priority
		self.Affinity = affinity			# Job affinity
		self.User = user					# Job user
		self.Finished = 0					# Number of finished children
		self.Errors = 0						# Number of error children
		self.Working = 0					# Number of children working
		self.Total = 0						# Total number of (grand)children
		self.TotalFinished = 0				# Total number of (grand)children finished
		self.TotalErrors = 0				# Total number of (grand)children in error
		self.TotalWorking = 0				# Total number of children working
		self.URL = ""						# URL to open
		self.LocalProgress = localprogress
		self.GlobalProgress = globalprogress

"""