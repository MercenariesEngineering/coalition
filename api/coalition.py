import httplib, urllib, json, sys

class CoalitionError(Exception):
	pass

class Job(object):
	''' A job object returned by the :class:`Connection`. Don't create such objects yourself.

	'''

	def __init__ (self, d, conn):
		assert (conn)
		self.Conn = False
		self.__dict__.update (d)
		self.Conn = conn

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

	def getJob (self, id):
		''' Returns a :class:`Job` object.

		:param id: the id of the :class:`Job` to return
		'''
		res = self._send ("GET", '/api/jobs/' + str(id))
		return Job (json.loads(res), self)

	def getJobChildren (self, id):
		''' Returns a :class:`Job` children objects.

		:param id: the job.ID of the parent :class:`Job`
		:rtype: A list of :class:`Job` objects
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
		:rtype: The list of :class:`Job` objects on which the job depends
		'''
		res = self._send ("GET", '/api/jobs/'+str(id)+'/dependencies')
		res = json.loads(res)
		children = []
		for r in res:
			children.append (Job (r, self))
		return children

	def setJobDependencies (self, id, ids):
		''' Set the :class:`Job` objects on which a job has a dependency.

		:param id: the id of the job with dependencies
		:rtype: The list of job.ID (int) on which the job depends
		'''
		res = self._send ("POST", '/api/jobs/'+str(id)+'/dependencies', ids)
		return res

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
		
		:param retry: the job retry count. If the job fails, the server will retry to run it this number of time.
		:type retry: int
		
		:param affinity: the job affinity string. Affinities are coma separated keywords. To run a job, the worker affinities must match all the job affinities.
		:type affinity: str
		
		:param user: the job user name.
		:type user: str
		
		:param [int] dependencies: the jobs id on which the new job has dependencies. The job will run when the dependency jobs have been completed without error.

		:rtype: The list of job id (int) on which the job depends
		'''
		params = locals().copy ()
		del params['self']
		res = self._send ("PUT", '/api/jobs', params)
		return int(res)

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
				res = self._send ("POST", '/api/jobs', self.Jobs)
			if len(self.Workers) > 0:
				res = self._send ("POST", '/api/workers', self.Workers)
			return res
