import httplib, urllib, json, sys

class CoalitionError(Exception):
	pass

class Job(object):
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
	def __init__(self, host, port):
		self.IntoWith = False
		self._Conn = httplib.HTTPConnection (host, port)

	def _send (self, command, params):
		if params.get ('self'):
			del params['self']
		params = json.dumps (params)
		headers = {'Content-Type': 'application/json'}
		self._Conn.request ("POST", "/json/%s?"%command, params, headers)
		res = self._Conn.getresponse()
		if res.status == 200:
			return res.read ()
		else:
			raise CoalitionError (res.read())

	def getJob (self, id):
		res = self._send ('getJob', locals().copy ())
		return Job (json.loads(res), self)

	def getJobChildren (self, id):
		res = self._send ('getJobChildren', locals().copy ())
		res = json.loads(res)
		children = []
		for r in res:
			children.append (Job (r, self))
		return children

	def getJobDependencies (self, id):
		res = self._send ('getJobDependencies', locals().copy ())
		res = json.loads(res)
		children = []
		for r in res:
			children.append (Job (r, self))
		return children

	def setJobDependencies (self, id, ids):
		res = self._send ('setJobDependencies', locals().copy ())
		return res

	def newJob  (self, parent=0, title="", command = "", dir = "", environment = "", state="WAITING", priority = 1000, retry = 10, timeout = 0, affinity = "", user = "", dependencies = []):
		res = self._send ('newJob', locals().copy ())
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
			data = {'Jobs':self.Jobs, 'Workers':self.Workers}
			res = self._send ('edit', data)
			return res
