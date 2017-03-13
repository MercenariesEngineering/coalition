# -*- coding: utf-8 -*-

import httplib, urllib, json, sys

class Connection(object):
	"""A connection to the coalition server.

	:param str host: The coalition server hostname.
	:param int port: The coalition server port.
	"""

	def __init__(self, host='localhost', port=19211):
		"""Setup http connection."""
		self.IntoWith = False
		self._Conn = httplib.HTTPConnection(host, port)

	def _send(self, method, command, params=None):
		"""Send message to server.
		
		:param str method: Http request method between "GET", "PUT", "POST" and "DELETE".
		:param str command: REST api URL.
		:param str params: Optional parameters.
		:return: A string or an error.
		:rtype: str or :class:CoalitionError
		"""

		if params:
			params = json.dumps(params)
		headers = {'Content-Type': 'application/json'}
		self._Conn.request(method, command, params, headers)
		res = self._Conn.getresponse()
		if res.status == 200:
			return res.read()
		else:
			raise CoalitionError(res.read())

	def newJob(self, parent=0, title='', command='', dir='', environment='',
			state="WAITING", paused=False, priority=1000, timeout=0,
			affinity='', user='', progress_pattern='', dependencies=[]):
		"""Create a :class:`Job`.

		:param int parent: The parent :class:`Job` id.
		:param str title: The :class:`Job` title.
		:param str command: The :class:`Job` command, or an empty string for a parent node.
		:param str dir: The :class:`Job` directory. This is the current directory when the :class:`Job` is run.
		:param str environment: The :class:`Job` environment variables.
		:param str state: The :class:`Job` initial state. It must be "WAITING" or "PAUSED". If the state is "WAITING", the :class:`Job` will start as soon as possible. If the state is "PAUSED", the :class:`Job` won't start until it is started or reset.
		:param int priority: The :class:`Job` priority. For a given :class:`Job` hierarchy level, the :class:`Job` with the biggest priority is taken first.
		:param int timeout: The maximum duration a :class:`Job` run can take in seconds. If timeout=0, no limit on the :class:`Job` run.
		:param str affinity: The :class:`Job` affinity string. Affinities are coma separated keywords. To run a :class:`Job`, the worker affinities must match all the :class:`Job` affinities.
		:param str user: The :class:`Job` user name.
		:param str progress_pattern: A regexp pattern which filters the logs and return the progression. The pattern must include a '%percent' or a '%one' keyword.
		:param list(int) dependencies: The :class:`Job` ids on which the new :class:`Job` has dependencies. The :class:`Job` will run when the dependency jobs have been completed without error.
		:return: The :class:`Job` id.
		:rtype: int
		"""

		params = locals().copy()
		del params['self']
		res = self._send("PUT", '/api/jobs', params)
		return int(res)

	def getJob(self, id):
		"""Get a :class:`Job` instance.

		:param int id: The id of the :class:`Job`.
		:return: A :class:`Job` instance.
		:rtype: :class:`Job`
		"""

		res = self._send('GET', '/api/jobs/' + str(id))
		return Job(json.loads(res), self)

	def getJobChildren (self, id):
		"""Get :class:`Job` children instances.

		:param int id: The parent :class:`Job` id.
		:return: The list of children :class:`Job` instances.
		:rtype: list(:class:`Job`)
		"""

		res = self._send('GET', '/api/jobs/{id}/children'.format(id=id))
		return [Job(r, self) for r in json.loads(res)]

	def getJobDependencies (self, id):
		"""Get the :class:`Job` dependencies.
		Alternatively, the dependencies attribute of a :class:`Job` contains the list
		of dependent jobs ids.

		:param str id: The :class:`Job` id having dependencies.
		:return: The :class:`Job` instances on which the :class:`Job` has dependencies.
		:rtype: list(:class:`Job`)
		"""

		res = self._send('GET', '/api/jobs/{}/dependencies'.format(id))
		return [Job(r, self) for r in json.loads(res)]

	def setJobDependencies (self, id, ids):
		'''Set the :class:`Job` objects on which a job has a dependency.
		Alternatively, one can set the dependencies attribute of a Job.

		:param id int: the id of the job with dependencies
		:param ids [int]: the list of job.id (int) on which the job depends
		'''
		res = self._send ("POST", '/api/jobs/'+str(id)+'/dependencies', ids)
		return res

	def setAffinities( self, data ):
		'''Set the affinities.
		Affinities need to be set before they can be assigned to :class:`Job` or Worker.

		:param data: a dictionnary of affinities
		'''
		res = self._send( "POST", "/api/affinities", data )
		return res

	def getAffinities( self ):
		'''Get the affinities.
		Affinities need to be set before they can be assigned to :class:`Job` or Worker.

		:param data: a dictionnary of affinities
		'''

		res = self._send( "GET", "/api/affinities" )
		res = json.loads( res )
		return res

	def getWorkers ( self ):
		'''Returns the :class:`Worker` objects.
		Workers are identified by an index.

		:rtype: the list of :class:`Worker` objects.
		'''

		res = self._send ("GET", '/api/workers')
		res = json.loads( res )
		return res

	def editWorkers( self, workers ):
		'''Set the :class:`Worker` objects.
		All the workers' attributes are updated.

		:param data: a dictionnary of workers.
		'''

		res = self._send( "POST", '/api/workers', workers )
		return res

	def __enter__(self):
		self.Jobs = {}
		self.Workers = {}
		self.IntoWith = True

	def __exit__(self, type, value, traceback):
		self.IntoWith = False
		
		# Convert an object in dict
		def convobj (o):
			d = o.__dict__.copy()
			del d['Conn']
			return d

		if not isinstance(value, TypeError):
			if len(self.Jobs) > 0:
				self._send ("POST", '/api/jobs', self.Jobs)
			if len(self.Workers) > 0:
				self._send ("POST", '/api/workers', self.Workers)


class Job(object):
	'''A job object returned by the :class:`Connection`. Don't create such objects yourself.
	Job properties should be modified into a Connection with block. Don't modify the id or the state properties directly.
	'''

	def __init__ (self, d, conn):
		assert (conn)
		self.Conn = False
		self.__dict__.update (d)
		self.Conn = conn
		""":var int id: the job id
		:var int parent: the parent job id
		:var str title: the job title
		:var str command: the job command to execute, or an empty string if the job is a parent node.
		:var str dir: the job working directory
		:var str environment: the job environment
		:var str state: the job state. It can be "WAITING", "PAUSED", "WORKING", "PENDING", "FINISHED" or "ERROR"
		:var str paused: the job is paused, which is an alias for state == "PAUSED".
		:var str worker: the last worker name who took the job
		:var int start_time: the job start time (in seconds after epoch)
		:var int duration: the job duration (in seconds)
		:var int ping_time: the last time a worker ping on this job (in seconds after epoch)
		:var int run_done: number of run done on this job
		:var int timeout: maximum duration a job run can take in seconds. If timeout=0, no limit on the job run.
		:var int priority: the job priority. For a given job hierarchy level, the job with the biggest priority is taken first.
		:var str affinity: the job affinity string. Affinities are coma separated keywords. To run a job, the worker affinities must match all the job affinities.
		:var str user: the job user name.
		:var int finished: number of finished children jobs. For parent node only. 
		:var int errors: number of faulty children jobs. For parent node only. 
		:var int working: number of working children jobs. For parent node only. 
		:var int total: number of total (grand)children jobs. For parent node only. 
		:var int total_finished: number of finished (grand)children jobs. For parent node only. 
		:var int total_errors: number of faulty (grand)children jobs. For parent node only. 
		:var int total_working: number of working (grand)children jobs. For parent node only. 
		:var array dependencies: the ids of jobs this job is dependent on. 
		:var str url: an URL to the job result. If available, a link to this URL will be shown in the interface.
		:var float progress: the job progression between 0 and 1.
		:var str progress_pattern: a regexp pattern which filters the logs and return the progression. The pattern must include a '%percent' or a '%one' keyword.
		"""

	def __setattr__(self, attr, value):
		if attr != "Conn" and self.Conn:
			if self.Conn.IntoWith:
				w = self.Conn.Jobs.get(self.id)
				if not w:
					w = {}
					self.Conn.Jobs[self.id] = w
				w[attr] = value
			else:
				raise CoalitionError("Can't write attributes outside a connection block")
		super(Job, self).__setattr__(attr, value)


class CoalitionError(Exception):
	pass


# vim: tabstop=4 noexpandtab shiftwidth=4 softtabstop=4 textwidth=79

