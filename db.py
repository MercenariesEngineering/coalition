import time

class DB(object):
	def __init__(self):
		self.IntoWith = False

	'''Enter a transaction block'''
	def __enter__(self):

		# Jobs is a map between job.id and the actual job proxy
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
		self.db = db
		self.id = id
		self.worker = worker
		self.job_id = job
		self.job_title = jobTitle
		self.state = state
		self.start = start
		self.duration = duration

		# Can't write anymore
		self.__initialized=True

	# The setattr method is override after the init to crash if used
	def __setattr__(self, attr, value):
		if attr != "_Event__initialized":
			if self.__initialized:
				# Backup the value for delayed writting
				if self.db.IntoWith:
					w = self.db.EventsToUpdate.get(self.id)
					if not w:
						w = {}
						self.db.EventsToUpdate[self.id] = w
					w[attr] = value
				else:
					raise Exception
		super(Event, self).__setattr__(attr, value)

class Worker(object):
	'''
	The database proxy object for a worker

	This object is readonly outside a transaction block.
	'''
	def __init__ (self, db, name, ip, affinity, state, pingTime, finished, error, last_job, current_event, cpu, free_memory, total_memory, active):
		self.__initialized = False
		self.db = db
		self.name=name
		self.ip=ip
		self.affinity=affinity
		self.state=state
		self.ping_time=pingTime
		self.finished=finished
		self.error=error
		self.last_job=last_job
		self.current_event=current_event
		self.cpu=cpu
		self.free_memory=free_memory
		self.total_memory=total_memory
		self.active=active

		# Can't write anymore
		self.__initialized=True

	# The setattr method is override after the init to crash if used
	def __setattr__(self, attr, value):
		if attr != "_Worker__initialized":
			if self.__initialized:
				# Backup the value for delayed writting
				if self.db.IntoWith:
					w = self.db.WorkersToUpdate.get(self.name)
					if not w:
						w = {}
						self.db.WorkersToUpdate[self.name] = w
					w[attr] = value
				else:
					raise Exception
		super(Worker, self).__setattr__(attr, value)

class Job(object):
	'''
	The database proxy object for a job

	This object is readonly outside a transaction block.
	'''
	def __init__ (self, db, id, parent, title, command, dir, environment, state, worker, starttime, duration, pingtime, run_done, retry, timeout, 
		priority, affinity, user, finished, errors, working, total, total_finished, total_errors, totalworking, url, progress, progress_pattern):
		self.__initialized = False
		self.db = db						# The database
		self.id = id						# Job id
		self.parent = parent				# Parent Job id
		self.title = title					# Job title
		self.command = command				# Job command to execute
		self.dir = dir						# Job working directory
		self.environment = environment		# Job environment
		self.state = state					# Job state, can be WAITING, WORKING, PAUSED, FINISHED or ERROR
		self.worker = worker				# Worker hostname
		self.start_time = starttime			# Start working time 
		self.duration = duration			# Duration of the process
		self.ping_time = pingtime			# Last worker ping time
		self.run_done = run_done			# Number of time the job has been run
		self.retry = retry					# Number of try max
		self.timeout = timeout				# Timeout in seconds
		self.priority = priority			# Job priority
		self.affinity = affinity			# Job affinity
		self.user = user					# Job user
		self.finished = finished			# Number of finished children
		self.errors = errors				# Number of error children
		self.working = working				# Number of children working
		self.total = total					# Total number of (grand)children
		self.total_finished = total_finished	# Total number of (grand)children finished
		self.total_errors = total_errors		# Total number of (grand)children in error
		self.total_working = totalworking	# Total number of children working
		self.url = url						# URL to open
		self.progress = progress 			# Job progression between 0 and 1
		self.progress_pattern = progress_pattern	# The progression pattern to filter the log
		self.__initialized = True

		# Should not exist in the cache
		assert (db.Jobs.get (self.id) == None)
		# Cache it
		db.Jobs[self.id] = self

	def hasChildren (self):
		return self.db.hasJobChildren (self.id)

	def getDependencies (self):
		return self.db.getJobDependencies (self.id)

	# The setattr method is override after the init to crash if used
	def __setattr__(self, attr, value):
		if attr != "_Job__initialized":
			if self.__initialized:
				# Backup the value for delayed writting
				if self.db.IntoWith and self.id != 0:
					w = self.db.JobsToUpdate.get(self.id)
					if not w:
						w = {}
						self.db.JobsToUpdate[self.id] = w
					w[attr] = value
				else:
					raise Exception
		super(Job, self).__setattr__(attr, value)
