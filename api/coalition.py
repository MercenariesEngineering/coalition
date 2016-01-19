import httplib, urllib, json, sys

class CoalitionError(Exception):
	pass

class Job(object):
	''' A job object returned by the :class:`Connection`. Don't create such objects yourself.
	Job properties should be modified into a Connection block. Don't modify the ID or the State properties directly.
	'''

	def __init__ (self, d, conn):
		assert (conn)
		self.Conn = False
		self.__dict__.update (d)
		self.Conn = conn
		""":var int ID: the job ID
		:var int Parent: the parent job id
		:var str Title: the job title
		:var str Command: the job command to execute
		:var str Dir: the job working directory
		:var str Environment: the job environment
		:var str State: the job state. It can be "WAITING", "WORKING", "PAUSED", "FINISHED" or "ERROR"
		:var str Worker: the last worker name who took the job
		:var int StartTime: the job start time (in seconds after epoch)
		:var int Duration: the job duration (in seconds)
		:var int PingTime: the last time a worker ping on this job (in seconds after epoch)
		:var int Try: number of run done on this job
		:var int Retry: the job run count. If the job fails, the server will retry to run it this number of time.
		:var int TimeOut: maximum duration a job run can take in seconds. If timeout=0, no limit on the job run.
		:var int Priority: the job priority. For a given job hierarchy level, the job with the biggest priority is taken first.
		:var str Affinity: the job affinity string. Affinities are coma separated keywords. To run a job, the worker affinities must match all the job affinities.
		:var str User: the job user name.
		:var int Finished: number of finished children jobs. For parent node only. 
		:var int Errors: number of faulty children jobs. For parent node only. 
		:var int Working: number of working children jobs. For parent node only. 
		:var int Total: number of total (grand)children jobs. For parent node only. 
		:var int TotalFinished: number of finished (grand)children jobs. For parent node only. 
		:var int TotalErrors: number of faulty (grand)children jobs. For parent node only. 
		:var int TotalWorking: number of working (grand)children jobs. For parent node only. 
		:var str URL: an URL to the job result. If available, a link to this URL will be shown in the interface.
		"""

	def __setattr__(self, attr, value):
		if attr != "Conn" and self.Conn:
			if self.Conn.IntoWith:
				w = self.Conn.Jobs.get(self.ID)
				if not w:
					w = {}
					self.Conn.Jobs[self.ID] = w
				w[attr] = value
			else:
				raise CoalitionError("Can't write attributes outside a connection block")
		super(Job, self).__setattr__(attr, value)

class Connection:
	''' A connection to the coalition server.

	:param str host: the coalition server hostname
	:param int port: the coalition server port (19211 by default)

	>>> import coalition
	>>> # Connect the server
	>>> conn = coalition.Connection ("localhost", 19211)
	>>> # Create a first job in the root node
	>>> job_id = conn.newJob (0, "Test", "echo test")
	>>> # Inspect the job
	>>> job = conn.getJob (job_id)
	>>> print type(job.ID)
	<type 'int'>
	>>> print job.Title
	Test
	>>> print job.Command
	echo test
	>>> # Edit a job, the modification is sent to the server at the end of the block
	>>> with conn:
	...		job.Title = "Test2"
	...		job.Command = "echo test2"
	>>> print job.Title
	Test2
	>>> # Reload the job from the server to check it has been modified
	>>> job = conn.getJob (job.ID)
	>>> print job.Title
	Test2
	>>> # Create a parent node, must NOT have a command
	>>> parent_id = conn.newJob (0, "Parent")
	>>> # Create a job in the parent node
	>>> child_id = conn.newJob (parent_id, "Child", "echo child")
	>>> # Get the parent children
	>>> children = conn.getJobChildren (parent_id)
	>>> for child in children: print child.Title
	Child
	'''

	def __init__(self, host, port):
		self.IntoWith = False
		self._Conn = httplib.HTTPConnection (host, port)

	def _send (self, method, command, params=None):
		if params:
			params = json.dumps (params)
		headers = {'Content-Type': 'application/json'}
		self._Conn.request (method, command, params, headers)
		res = self._Conn.getresponse()
		if res.status == 200:
			return res.read ()
		else:
			raise CoalitionError (res.read())

	def newJob  (self, parent=0, title="", command = "", dir = "", environment = "", state="WAITING", priority = 1000, retry = 10, timeout = 0, affinity = "", user = "", dependencies = []):
		''' Create a job.

		:param parent: the parent job.ID
		:type parent: int
		
		:param title: the job title
		:type title: str
		
		:param command: the job command
		:type command: str
		
		:param dir: the job directory. This is the current directory when the job is run.
		:type dir: str
		
		:param environment: the job environment variables
		:type environment: str
		
		:param state: the job initial state. It must be "WAITING" or "PAUSED". If the state is "WAITING", the job will start as soon as possible. If the state is "PAUSED", the job won't start until it is started or reset.
		:type state: str

		:param priority: the job priority. For a given job hierarchy level, the job with the biggest priority is taken first.
		:type priority: int
		
		:param retry: the job run count. If the job fails, the server will retry to run it this number of time.
		:type retry: int

		:param timeout int: maximum duration a job run can take in seconds. If timeout=0, no limit on the job run.
		
		:param affinity: the job affinity string. Affinities are coma separated keywords. To run a job, the worker affinities must match all the job affinities.
		:type affinity: str
		
		:param user: the job user name.
		:type user: str
		
		:param [int] dependencies: the jobs id on which the new job has dependencies. The job will run when the dependency jobs have been completed without error.

		:rtype: the list of job id (int) on which the job depends
		'''
		params = locals().copy ()
		del params['self']
		res = self._send ("PUT", '/api/jobs', params)
		return int(res)

	def getJob (self, id):
		''' Returns a :class:`Job` object.

		:param id: the id of the :class:`Job` to return


		'''
		res = self._send ("GET", '/api/jobs/' + str(id))
		return Job (json.loads(res), self)

	def getJobChildren (self, id):
		''' Returns a :class:`Job` children objects.

		:param id: the job.ID of the parent :class:`Job`
		:rtype: a list of :class:`Job` objects

		'''
		res = self._send ("GET", '/api/jobs/'+str(id)+'/children')
		res = json.loads(res)
		children = []
		for r in res:
			children.append (Job (r, self))
		return children

	def getJobDependencies (self, id):
		''' Returns the :class:`Job` objects on which a job has a dependency.

		:param id: the job.ID of the :class:`Job` with dependencies
		:rtype: the list of :class:`Job` objects on which the job depends
		'''
		res = self._send ("GET", '/api/jobs/'+str(id)+'/dependencies')
		res = json.loads(res)
		children = []
		for r in res:
			children.append (Job (r, self))
		return children

	def setJobDependencies (self, id, ids):
		''' Set the :class:`Job` objects on which a job has a dependency.

		:param id int: the id of the job with dependencies
		:param ids [int]: the list of job.ID (int) on which the job depends
		'''
		res = self._send ("POST", '/api/jobs/'+str(id)+'/dependencies', ids)
		return res

	def __enter__(self):
		self.Jobs = {}
		self.Workers = {}
		self.IntoWith = True

	def __exit__ (self, type, value, traceback):
		self.IntoWith = False
		
		# Convert an object in dict
		def convobj (o):
			d = o.__dict__.copy ()
			del d['Conn']
			return d

		if not isinstance(value, TypeError):
			if len(self.Jobs) > 0:
				self._send ("POST", '/api/jobs', self.Jobs)
			if len(self.Workers) > 0:
				self._send ("POST", '/api/workers', self.Workers)
