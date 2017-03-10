# -*- coding: utf-8 -*-

import sqlite3, MySQLdb, unittest, time, re, sys
from db import DB
from importlib import import_module
import cloud
from cloud.common import createWorkerInstanceName
from textwrap import dedent
import os


def convdata (d):
	return isinstance(d, str) and repr (d) or (isinstance(d, bool) and (d and '1' or '0') or (isinstance(d, unicode) and repr(str(d)) or str(d)))

class DBSQL(DB):

	def __init__ (self):
		self.StartTime = time.time ()
		self.lastworkerinstancestarttime = 0
		self.LastUpdate = 0
		self.EnterTime = 0
		self.RunTime = 0.0
		self.HeartBeats = 0
		self.PickJobs = 0
		self.Verbose = False
		self.NotifyFinished = None
		self.NotifyError = None
		self.Workers = dict()
		self.AffinityBitsToName = dict()

		tables = self._getDatabaseTables()

		if ("Workers",) in tables:
			self._populateWorkersCache()

		if ("Affinities",) in tables:
			self._populateAffinitiesTable()

	def __enter__(self):
		self.EnterTime = time.time ()
		self.Conn.__enter__ ()

	def __exit__ (self, type, value, traceback):
		self.RunTime = time.time ()-self.EnterTime
		if not isinstance(value, TypeError):
			self._update ()
		self.Conn.__exit__ (type, value, traceback)

	def _execute (self, cur, req, data=None):
		now = time.time ()
		if data:
			cur.execute (req, data)
		else:
			cur.execute (req)
		after = time.time ()
		if self.Verbose:
			sys.stdout.flush ()
			sys.stdout.write ("[SQL] (%f/%f) %s\n" % (now-self.StartTime, after-now, req))
			sys.stdout.flush ()

	def _rowAsDict (self, cur, row):
		if row:
			result = {}
			for idx, col in enumerate (cur.description):
				result[col[0]] = row[idx]
			return result
		else:
			return None

	def _populateWorkersCache(self):
		"""Populate cache with pre-existent data in Workers table."""
		cur = self.Conn.cursor ()
		self._execute (cur, "SELECT name FROM Workers")
		for worker in cur:
			info = {}
			info['ping_time'] = int (time.time ())
			info['cpu'] = ''
			info['free_memory'] = 0
			info['total_memory'] = 0
			info['ip'] = ''
			info['timeout'] = False
			self.Workers[worker[0]] = info

	def _populateAffinitiesTable(self):
		"""Populate Affinities table with pre-existent data having an id < 64."""
		cur = self.Conn.cursor ()
		with self.Conn:
			affinities = {}
			self._execute (cur, "SELECT id, name FROM Affinities")
			for row in cur:
				affinities[int (row[0])] = row[1]
			for i in range (1, 64):
				if not i in affinities:
					self._execute (cur, "INSERT INTO Affinities (id, name) VALUES (%d,'')" % i)

	def listJobs (self):
		cur = self.Conn.cursor ()
		self._execute (cur, "SELECT * FROM Jobs")
		for row in cur:
			print (self._rowAsDict (cur, row))

	def listJobsByStates(self, state, *argv):
		cur = self.Conn.cursor ()
		req = "SELECT * FROM Jobs WHERE state = '%s'" % state
		if argv:
			for arg in argv:
				req += " OR state = '%s'" % arg
		self._execute (cur, req)
		return [self._rowAsDict (cur, row) for row in cur]

	def listWorkers (self):
		cur = self.Conn.cursor ()
		self._execute (cur, "SELECT * FROM Workers")
		for row in cur:
			print (row)

	def listWorkersByStates(self, state, *argv):
		cur = self.Conn.cursor ()
		req = "SELECT * FROM Workers WHERE state = '%s'" % state
		if argv:
			for arg in argv:
				req += " OR state = '%s'" % arg
		self._execute (cur, req)
		return [self._rowAsDict (cur, row) for row in cur]

	def listAffinities (self):
		cur = self.Conn.cursor ()
		self._execute (cur, "SELECT id, name FROM Affinities")
		aff = {}
		for row in cur:
			if row[1] != "" and row[0] >= 1 and row[0] <= 63:
				aff[row[1]] = (1L << (row[0]-1))
		return aff

	def getAffinities (self):
		cur = self.Conn.cursor ()
		self._execute (cur, "SELECT id, name FROM Affinities")
		aff = {}
		for row in cur:
			if row[0] >= 1 and row[0] <= 63:
				aff[row[0]] = row[1]
		return aff

	def setAffinities (self, affinities):
		# reset affinities cache
		self.AffinityBitsToName = {}
		cur = self.Conn.cursor ()
		for id, affinity in affinities.iteritems ():
			self._execute (cur, "UPDATE Affinities SET name = '%s' WHERE id = %d" % (affinity, int (id)))

	def getAffinityMask (self, affinities):
		if affinities == "":
			return 0
		aff = self.listAffinities ()
		mask = 0L
		cur = self.Conn.cursor ()
		for affinity in affinities.split (","):
			if affinity != "":
				m = re.match(r"^#(\d+)$", affinity)
				if m:
					bit = (int(m.group (1))-1)
					mask = mask | (1L << bit)
				else:
					mask = mask | aff[affinity]
		return mask

	def getAffinityString (self, affinity_bits):
		if affinity_bits == 0:
			return ""
		if affinity_bits in self.AffinityBitsToName:
			return self.AffinityBitsToName[affinity_bits]
		names = []
		aff = self.getAffinities()
		for id, name in aff.iteritems ():
			bit = (1L << (id-1));
			if affinity_bits & bit != 0:
				if name != '':
					names.append (name)
				else:
					names.append ("#"+ str (id))
		names.sort ()
		result = ",".join (names)
		self.AffinityBitsToName[affinity_bits] = result
		return result

	def newJob (self, parent, title, command, dir, environment, state, paused, timeout, 
				priority, affinity, user, url, progress_pattern, dependencies = None):
		cur = self.Conn.cursor ()
		self._execute (cur, "SELECT h_depth, h_affinity, h_priority, h_paused, command FROM Jobs WHERE id = %d" % parent)
		data = cur.fetchone ()
		if state == "PAUSED":
			paused = True;
		if data is None:
			data = [-1, 0, 0, False, '']
		if data[4] != '':
			print ("Error : can't add job, parent %d is not a group" % parent)
			return None
		# one depth below
		h_depth = data[0]+1
		# merge parent affinities with child affinities
		parent_affinities = data[1]
		child_affinities = self.getAffinityMask (affinity)
		h_affinity = parent_affinities | child_affinities
		# merge priority
		priority = max (0, min (255, int (priority)))
		h_priority = data[2] + (priority << (56-h_depth*8))
		h_paused = data[3] or paused

		self._execute (cur, "INSERT INTO Jobs (parent, title, command, dir, "
						"environment, timeout, priority, affinity, affinity_bits, "
						"user, url, progress_pattern, paused, state, worker, "
						"h_depth, h_affinity, h_priority, h_paused) VALUES"
						"(%d,%s,%s,%s,"
						"%s,%d,%d,%s,%d,"
						"%s,%s,%s,%d,'WAITING','',"
						"%d,'%s',%d,%d)" % (parent, repr (title), repr (command), repr (dir), 
						repr (environment), timeout, priority, repr (affinity), child_affinities,
						repr (user), repr (url), repr (progress_pattern), paused,
						h_depth, h_affinity, h_priority, h_paused))
		data = cur.fetchone ()
		job = self.getJob (cur.lastrowid)
		if job is not None and dependencies is not None:
			self.setJobDependencies (job['id'], dependencies)
		self._updateJobCounters (parent)
		job['dependencies'] = dependencies
		return job

	def getJob (self, id):
		cur = self.Conn.cursor ()
		self._execute (cur, "SELECT * FROM Jobs WHERE id = %d" % id)
		result = self._rowAsDict (cur, cur.fetchone ())
		if result is not None:
			if result['paused']:
				result['state'] = str ("PAUSED")
			if result['state'] == "WORKING" and result['total'] == 0:
				current_time = int (time.time ())
				result['duration'] = current_time - result['start_time']
			result['affinity'] = self.getAffinityString (result['affinity_bits'])
			# get dependencies
			result['dependencies'] = []
			self._execute (cur, "SELECT job.id FROM Jobs AS job "
							"INNER JOIN Dependencies AS dep ON job.id = dep.dependency "
							"WHERE dep.job_id = %d" % id)
			for row in cur:
				result['dependencies'].append (row[0])
		return result

	def getJobChildren (self, id, data):
		cur = self.Conn.cursor ()
		self._execute (cur, "SELECT * FROM Jobs WHERE parent = %d" % id)
		jobs = []
		for row in cur:
			result = self._rowAsDict (cur, row)
			if result and result['paused']:
				result['state'] = str ("PAUSED")
			if result['state'] == "WORKING" and result['total'] == 0:
				current_time = int (time.time ())
				result['duration'] = current_time - result['start_time']
			result['affinity'] = self.getAffinityString (result['affinity_bits'])
			jobs.append (result)
		return jobs

	def getJobDependencies (self, id):
		cur = self.Conn.cursor ()
		self._execute (cur, "SELECT job.* FROM Jobs AS job "
						"INNER JOIN Dependencies AS dep ON job.id = dep.dependency "
						"WHERE dep.job_id = %d" % id)
		rows = cur.fetchall()
		return [self._rowAsDict (cur, row) for row in rows]

	def getChildrenDependencyIds (self, id):
		cur = self.Conn.cursor ()
		self._execute (cur, "SELECT job.id AS id, dep.dependency AS dependency FROM Dependencies AS dep "
						"INNER JOIN Jobs AS job ON job.id = dep.job_id "
						" WHERE job.parent = %d" % id)
		rows = cur.fetchall()
		return [self._rowAsDict (cur, row) for row in rows]

	def getWorker (self, hostname):
		cur = self.Conn.cursor ()
		self._execute (cur, "SELECT * FROM Workers WHERE name = '%s'" % hostname)
		worker = self._rowAsDict (cur, cur.fetchone ())
		try:
			info = self.Workers[hostname]
			worker['ping_time'] = info['ping_time']
			worker['cpu'] = info['cpu']
			worker['free_memory'] = info['free_memory']
			worker['total_memory'] = info['total_memory']
		except:
			pass
		
		self._execute (cur, "SELECT affinity FROM WorkerAffinities WHERE worker_name = '%s'" % ( hostname ) )
		affinities = []
		
		data = cur.fetchone()

		if data is None:
			worker['affinity'] = ""
			return worker

		for data in cur:
			affinities.append( self.getAffinityString( data ) )

		worker['affinity'] = "\n".join( affinities )
		return worker

	def getWorkerStartTime(self, name):
		"""Get the number of seconds since epoch."""
		cur = self.Conn.cursor ()
		self._execute(cur, "SELECT start_time FROM Workers WHERE name = '%s'" % name)
		db_type = self._getDatabaseType()
		if db_type == "mysql":
			start_time = cur.fetchone()[0].timetuple()
		else:
			start_time = time.strptime(cur.fetchone()[0], '%Y-%m-%d %H:%M:%S')
		return time.mktime(start_time)

	def getWorkers (self):
		cur = self.Conn.cursor ()
		self._execute (cur, "SELECT * FROM Workers")
		workers = []
		for row in cur:
			worker = self._rowAsDict (cur, row)
			try:
				info = self.Workers[worker['name']]
				worker['ping_time'] = info['ping_time']
				worker['cpu'] = info['cpu']
				worker['free_memory'] = info['free_memory']
				worker['total_memory'] = info['total_memory']
			except:
				pass

			req = self.Conn.cursor()
			self._execute( req, "SELECT affinity FROM WorkerAffinities WHERE worker_name = '%s'" % ( worker['name'] ) )
			affinities = []

			for d in req:

				affinities.append( self.getAffinityString( d[0] ) )

			worker['affinity'] = "\n".join( affinities )
			print worker['affinity']
			worker['start_time'] = self.getWorkerStartTime(worker['name'])
			workers.append (worker)
		return workers

	def getEvents (self, job, worker, howlong):
		cur = self.Conn.cursor()
		req = "SELECT * FROM Events WHERE start > %d" % (int(time.time())-howlong)
		if worker:
			req += " AND worker=%s" % convdata (worker)
		if job > 0:
			req += " AND job_id=%d" % job
		self._execute (cur, req);
		return [self._rowAsDict (cur, row) for row in cur.fetchall ()]

	def editJobs (self, jobs):
		cur = self.Conn.cursor ()
		for id, attr in jobs.iteritems ():
			toUpdate = [k+"="+convdata(v) for k,v in attr.iteritems()
				if k != 'dependencies' and k != 'affinity' and k != 'priority' and
					k != 'state' and k != 'parent']
			if toUpdate:
				req = "UPDATE Jobs SET " + ",".join (toUpdate) + " WHERE id=" + str(id)
				self._execute(cur, req)
				cur.fetchall()
			# Special cases
			if attr.get ('paused') is not None:
				paused = attr.get ('paused')
				if paused:
					self.pauseJob (int (id))
				else:
					self.startJob (int (id))
			if attr.get ('state'):
				state = attr.get ('state')
				if state == 'PAUSED':
					self.pauseJob (int (id))
				elif state == 'WAITING':
					self.startJob (int (id))
				else:
					self._setJobState (int (id), state, True)
			updateChildren = False
			if attr.get ('parent') is not None:
				self.moveJob (int (id), int (attr['parent']))
			if attr.get ('affinity') is not None:
				self.setJobAffinity (int (id), attr['affinity'])
			if attr.get ('priority'):
				self.setJobPriority (int (id), attr['priority'])
			if attr.get ('parent') is not None or attr.get ('affinity') is not None or attr.get ('priority') is not None or attr.get ('paused') is not None:
				self._updateChildren (int (id))
			if attr.get ('dependencies'):
				dependencies = attr['dependencies']
				if type(dependencies) is str:
					# Parse the dependencies string
					dependencies = re.findall ('(\d+)', dependencies)
				ids = []
				for i, dep in enumerate (dependencies) :
					try:
						ids.append (int (dep))
					except:
						pass
				self.setJobDependencies (int (id), ids)
				self._setJobState (int (id), None, True)

	def editWorkers (self, workers):
		cur = self.Conn.cursor ()
		for name, attr in workers.iteritems ():
			hasField = False
			req = "UPDATE Workers SET"
			for k, v in attr.iteritems():
				if k != 'affinity':
					hasField = True
					req += " " + k + " = " + convdata (v)
			req += " WHERE name = '" + name + "'"
			if hasField:
				self._execute(cur, req)
				cur.fetchall()
			if attr.get ('affinity') is not None:
				self.setWorkerAffinity (str (name), attr['affinity'])

	def setJobProgress (self, jobId, progress):
		cur = self.Conn.cursor ()
		self._execute (cur, "UPDATE Jobs SET progress = %f WHERE id = %d" % (progress, jobId))

	def _getDatabaseType(self):
		"""Get the database type."""
		return self.config.get("server", "db_type")

	def _getDatabaseTables(self):
		"""Return list of database tables."""
		cur = self.Conn.cursor()
		db_type = self._getDatabaseType()
		if db_type == "mysql":
			req = "SHOW TABLES;"
		else:
			req = "SELECT name FROM	sqlite_master WHERE type = 'table';"
		self._execute(cur, req)
		return cur.fetchall()

	def _getDatabaseVersion(self):
		"""Return database version."""
		cur = self.Conn.cursor()
		tables = self._getDatabaseTables()
		if not ("Migrations",) in tables:
			current_version = [("0000",)]
		else:
			req = "SELECT database_version FROM Migrations;"
			self._execute(cur, req)
			current_version = cur.fetchall()
		return int(current_version[0][0])

	def _getMigrationVersion(self):
		"""Return latest migration version."""
		return int(max([re.sub(r'_.*$', '', f) for f in
			os.walk("migrations").next()[2]]))

	def initDatabase(self):
		"""Initialize the database."""
		if len(self._getDatabaseTables()):
			print("The database is not empty, it will not be initialized.")
			return False
		print("Initializing database.")
		return self.migrateDatabase(init=True)

	def migrateDatabase(self, init=False):
		"""Migrate the database."""
		db_type = self._getDatabaseType()
		current = self._getDatabaseVersion()
		target = self._getMigrationVersion()
		if init:
			# Init with the '0000' migration
			current -= 1
		cur = self.Conn.cursor()
		print("The database version is {current} and the migration target is {target}. Migrating.".format(current=current, target=target))
		while current < target:
			current += 1
			migration_module_name = "{current:04d}_db_{db_type}".format(current=current, db_type=db_type)
			migration_module = import_module("migrations.{}".format(migration_module_name))
			with self.Conn:
				for step in migration_module.steps:
					self._execute(cur, step.strip())
		if init:
			with self.Conn:
				for i in range(1, 64):
					self._execute(cur, dedent("""
					INSERT INTO Affinities (id, name)
					VALUES ('{}', '')""".format(i)))
		return True

	def moveJob (self, jobId, parent):
		cur = self.Conn.cursor ()
		self._execute (cur, "SELECT parent FROM Jobs WHERE id = %d" % jobId)
		previous = cur.fetchone ()
		self._execute (cur, "UPDATE Jobs SET parent = %d WHERE id = %d" % (parent, jobId))
		self._updateJobCounters (previous[0])
		self._updateJobCounters (parent)

	def setJobAffinity (self, id, affinity):
		cur = self.Conn.cursor ()
		affinities = self.getAffinityMask (affinity)
		self._execute (cur, "UPDATE Jobs SET affinity = '%s', affinity_bits = %d WHERE id = %d" % (affinity, affinities, id))

	def setJobPriority (self, id, priority):
		cur = self.Conn.cursor ()
		priority = max (0, min (255, int (priority)))
		self._execute (cur, "UPDATE Jobs SET priority = %d WHERE id = %d" % (priority, id))

	def setJobDependencies (self, id, dependencies):
		cur = self.Conn.cursor ()
		self._execute (cur, "DELETE FROM Dependencies WHERE job_id = %d" % int (id))
		for dep in dependencies:
			self._execute (cur, "INSERT INTO Dependencies (job_id,dependency) "
							"VALUES (%d,%d)" % (int (id), int (dep)))
		self._setJobState (int (id), None, True)

	def resetJob (self, id, updateChildren = True):
		cur = self.Conn.cursor ()
		self._execute (cur, "UPDATE Jobs SET start_time = 0 WHERE id = %d" % id)
		self._setJobState (id, "WAITING", False)
		self._execute (cur, "SELECT id FROM Jobs WHERE parent = %d" % id)
		for row in cur:
			self.resetJob (row[0], False)
		if updateChildren:
			self._resetJobCounters (id)

	def resetErrorJob (self, id, updateChildren = True):
		cur = self.Conn.cursor ()
		self._execute (cur, "SELECT state FROM Jobs WHERE id = %d" % id)
		data = cur.fetchone ()
		if data is not None and data[0] == "ERROR":
			self._execute (cur, "UPDATE Jobs SET start_time = 0 WHERE id = %d" % id)
			self._setJobState (id, "WAITING", False)
		self._execute (cur, "SELECT id FROM Jobs WHERE parent = %d" % id)
		for row in cur:
			self.resetErrorJob (row[0], False)
		if updateChildren:
			self._resetJobCounters (id)

	def startJob (self, id):
		cur = self.Conn.cursor ()
		self._execute (cur, "UPDATE Jobs SET paused = 0 WHERE id = %d" % id)
		self._setJobState (id, "WAITING", False)
		self._updateChildren (id)
		self._updateJobCounters (id)

	def pauseJob (self, id):
		cur = self.Conn.cursor ()
		self._execute (cur, "UPDATE Jobs SET paused = 1 WHERE id = %d" % id)
		self._setJobState (id, "PAUSED", False)
		self._updateChildren (id)
		self._updateJobCounters (id)

	def deleteJob (self, id, deletedJobs = [], updateCounters = True):
		cur = self.Conn.cursor ()
		self._execute (cur, "SELECT id FROM Jobs WHERE parent = %d" % id)
		for row in cur:
			self.deleteJob (row[0], deletedJobs, False)
		parent = None
		if updateCounters:
			self._execute (cur, "SELECT parent FROM Jobs WHERE id = %d" % id)
			parent = cur.fetchone ()
		self._execute (cur, "DELETE FROM Jobs WHERE id = %d" % id)
		# clean up Events?
		#self._execute (cur, "DELETE FROM Events WHERE job_id = %d" % id)
		deletedJobs.append (id)
		if parent is not None:
			self._updateJobCounters (parent[0])

	def newWorker (self, name):
		cur = self.Conn.cursor ()
		self._execute (cur, "INSERT INTO Workers (name,ip,affinity, state,finished,"
						"error,last_job,current_event,cpu,free_memory,total_memory,active) "
						"VALUES ('%s','','','WAITING',0,0,-1,-1,'[0]',0,0,1)" % name)

	def setWorkerAffinity (self, name, affinity):
		cur = self.Conn.cursor ()
		# Delete all the worker's affinities
		self._execute( cur, "DELETE FROM WorkerAffinities WHERE worker_name = '%s'" % ( name ) )

		if len( affinity ) > 0:

			affinities = affinity.split( "\n" )

			for index, aff in enumerate( affinities ):

				query = "INSERT INTO WorkerAffinities ( worker_name, affinity, ordering ) VALUES( '%s', %d, %d )" % ( name, self.getAffinityMask( aff ), index+1 )
				self._execute( cur, query )


	def stopWorker (self, name):
		cur = self.Conn.cursor ()
		self._execute (cur, "UPDATE Workers SET active = 0 WHERE name = '%s'" % name)
		self._execute (cur, "SELECT job.id FROM Jobs AS job "
						"INNER JOIN Workers AS worker ON "
							"worker.last_job = job.id AND worker.name = job.worker "
							"WHERE worker.name = '%s' AND job.state = 'WORKING'" % name)
		row = cur.fetchone ()
		if row is not None:
			self._setJobState (row[0], "WAITING", True)

	def startWorker (self, name):
		cur = self.Conn.cursor ()
		self._execute (cur, "UPDATE Workers SET active = 1 WHERE name = '%s'" % name)

	def deleteWorker (self, name):
		cur = self.Conn.cursor ()
		self._execute (cur, "DELETE FROM Workers WHERE name = '%s'" % name)
		try:
			del self.Workers[name]
		except:
			pass

	def _updateWorkerInfo (self, hostname, cpu, free_memory, total_memory, ip):
		try:
			info = self.Workers[hostname]
		except:
			info = {}
			self.Workers[hostname] = info
		info['ping_time'] = int (time.time ())
		info['cpu'] = cpu
		info['free_memory'] = free_memory
		info['total_memory'] = total_memory
		info['ip'] = ip
		info['timeout'] = False
		return info

	# Worker heartbeats while running a job
	# Lookup for worker and job
	# update worker and job
	def heartbeat (self, hostname, jobId, cpu, free_memory, total_memory, ip):
		self.HeartBeats += 1
		current_time = int(time.time())
		cur = self.Conn.cursor ()

		self._updateWorkerInfo (hostname, cpu, free_memory, total_memory, ip)

		_query = ("SELECT w.active, w.state, j.state FROM Workers as w "
					"INNER JOIN Jobs AS j ON "
						"j.worker = w.name AND j.id = %d AND w.last_job = %d AND "
						"w.state = 'WORKING' AND j.state = 'WORKING' and j.h_paused = 0 "
					"WHERE w.name = '%s'" % (jobId, jobId, hostname))
		self._execute (cur, _query)
		data = cur.fetchone ()

		if data:
			return True

		# slow path here
		# either worker doesn't exist or job is not assigned to the worker or job was pause
		# get the worker active and state
		self._execute (cur, "SELECT active, state FROM Workers WHERE name = '%s'" % hostname)
		worker = cur.fetchone ()
		if worker is None:
			# create worker if needed
			self.newWorker (hostname)
			self._execute (cur, "SELECT active, state FROM Workers WHERE name = '%s'" % hostname)
			worker = cur.fetchone ()

		# by default we're suspicious and we flag the worker as waiting
		state = "WAITING"
		job = None
		if worker[0] == True:
			self._execute (cur, "SELECT state, h_paused FROM Jobs WHERE id = %d AND worker = '%s'" % (jobId, hostname))
			job = cur.fetchone ()
			if job is not None and job[0] == "WORKING" and not job[1]:
				# if the worker is active and is running the job, it's all good
				# we just lost track of the worker (deleteWorker) and we just need
				# to update them
				self._setWorkerState (hostname, "WORKING")
				return True

		# something is not right!
		# reset the worker to WAITING
		self._setWorkerState (hostname, "WAITING")
		# and if the job exists, reset it to WAITING as well
		if job is not None:
			self._setJobState (jobId, "WAITING", True)
		return False

	def pickJob (self, hostname, cpu, free_memory, total_memory, ip):
		self.PickJobs += 1
		current_time = int(time.time())
		cur = self.Conn.cursor()

		self._updateWorkerInfo(hostname, cpu, free_memory, total_memory, ip)

		# get the worker active and state
		self._execute(cur, "SELECT active, state, last_job FROM Workers WHERE name = '%s'" % hostname)
		worker = cur.fetchone()
		if worker is None:
			self.newWorker(hostname)
			self._execute(cur, "SELECT active, state, last_job FROM Workers WHERE name = '%s'" % hostname)
			worker = cur.fetchone()

		# check the worker is not already working
		# this can happen if the worker crashed and restarted before
		# timeout is detected
		if worker[1] == "WORKING":
			# reset all working jobs assigned to this worker
			self._execute(cur, "SELECT id FROM Jobs WHERE state = 'WORKING' and worker = '%s'" % hostname)
			for job in cur:
				self._setJobState(job[0], "WAITING", True)

		# worker is not active, drop now
		if not worker[0]:
			return -1,"","","",None

		# Here, we have an INNER JOIN query
		# Fetch the FIRST job whose affinity match the worker's first affinity in the list (stored in WorkerAffinities)
		self._execute(cur, dedent("""
			SELECT J.id, J.title, J.command, J.dir, J.user, J.environment
			FROM Jobs AS J
			INNER JOIN WorkerAffinities AS W
			ON (( J.h_affinity & W.affinity = J.h_affinity ) & ( J.h_affinity != 0 ))
			WHERE W.worker_name = '{}'
			AND J.state = 'WAITING'
			AND NOT J.h_paused
			AND J.command != ''
			ORDER BY W.ordering ASC, J.h_priority DESC, J.id ASC LIMIT 1""".format(hostname)))

		job = cur.fetchone() # This instruction is redundant because there is a LIMIT 1 in the query

		# At this point, the job will be set to None IF :
		# * There is no Worker whose affinity match any Job affinity
		# * A job has no affinity
		# The former case is EXPECTED, but not the latter one
		# Therefore, we need to add a query that take the first Job that has no affinity WHEN Workers are not doing anything
		if job is None:
			self._execute(cur, dedent("""
				SELECT id, title, command, dir, user, environment
				FROM Jobs
				WHERE state = 'WAITING'
				AND NOT h_paused
				AND affinity = ''
				AND command != ''
				ORDER BY h_priority DESC, id ASC LIMIT 1"""))

			job = cur.fetchone ()

			if job is None: # Finally, return nothing if there is no job.
				return -1, "", "", "", None

		# update the job and worker
		id = job[0]

		# create a new event
		self._execute (cur, "INSERT INTO Events (worker, job_id, job_title, state, start, duration) "
								"VALUES (%s, %d, %s, 'WORKING', %d, %d)" %
								(convdata (hostname), job[0], convdata (job[1]),
									current_time, 0))
		cur.fetchone ()
		eventid = cur.lastrowid

		self._execute (cur, "UPDATE Jobs SET worker = '%s', start_time = %d, duration = 0, progress = 0.0 "
						"WHERE id = %d" % (hostname, current_time, id))
		self._execute (cur, "UPDATE Workers SET last_job = %d, state = 'WORKING', current_event = %d "
						"WHERE name = '%s'" % (id, eventid, hostname))

		self._setJobState (id, "WORKING", True)

		if job[4] != None and job[4] != "":
			return job[0], job[2], job[3], job[4], job[5]
		else:
			return job[0], job[2], job[3], "", job[5]

	def endJob (self, hostname, jobId, errorCode, ip):
		current_time = int(time.time())
		cur = self.Conn.cursor ()
		self._execute (cur, "SELECT active, current_event FROM Workers WHERE name = '%s'" % hostname)
		worker = cur.fetchone ()
		if worker is None:
			self.newWorker (hostname)
			self._execute (cur, "SELECT active, current_event FROM Workers WHERE name = '%s'" % hostname)
			worker = cur.fetchone ()

		self._execute (cur, "SELECT state, start_time FROM Jobs WHERE id = %d AND worker = '%s' AND state = 'WORKING'" % (jobId, hostname))
		job = cur.fetchone ()
		if job is not None:
			state = (errorCode != 0) and "ERROR" or "FINISHED"
			# update event
			start_time = job[1]
			self._execute (cur, "UPDATE Events SET state = %s, duration = %d WHERE id = %d" %
									(convdata (state), current_time-start_time, worker[1]))
			self._setJobState (jobId, state, True)
			self._setWorkerState (hostname, state)

	def _isJobPending (self, id):
		cur = self.Conn.cursor ()
		self._execute (cur, "SELECT COUNT(job.id) FROM Jobs AS job "
						"INNER JOIN Dependencies AS dep ON job.id = dep.dependency "
						"WHERE dep.job_id = %d AND job.state != 'FINISHED'" % id)
		result = cur.fetchone ()
		return (result[0] > 0)

	def _updateDependentJobsState (self, id):
		cur = self.Conn.cursor ()
		self._execute (cur, "SELECT job.id FROM Jobs AS job "
						"INNER JOIN Dependencies AS dep ON job.id = dep.job_id "
						"WHERE dep.dependency = %d" % id)
		for dependent in cur:
			self._setJobState (dependent[0], None, True)

	# update the job state
	# also check dependencies, mark pending in this case
	# if None is passed as state, assumes previous state
	def _setJobState (self, id, state, updateCounters):
		current_time = int(time.time())
		cur = self.Conn.cursor ()
		self._execute (cur, "SELECT state, parent, user, title, id FROM Jobs WHERE id = %d" % id)
		job = cur.fetchone ()
		if job is not None:
			jobdict = self._rowAsDict (cur, job)
			# passed None, use previous state
			if state is None:
				state = job[0]
			# job set to waiting/pending, check dependencies first
			if state == "WAITING" or state == "PENDING":
				state = self._isJobPending (id) and "PENDING" or "WAITING"
			# changing status?
			if state != job[0]:
				if state == "FINISHED" and self.NotifyFinished:
					self.NotifyFinished (jobdict)
				elif state == "ERROR" and self.NotifyError:
					self.NotifyError (jobdict)
				_set = "state = '%s'" % state
				if state == "FINISHED" or state == "ERROR":
					_set += ", duration = %d-start_time" % current_time
					_set += ", run_done = run_done+1"
				self._execute (cur, "UPDATE Jobs SET "+_set+" WHERE id = %d" % id)
				self._updateDependentJobsState (id)
				self._updateChildren (id)
				if updateCounters:
					self._updateJobCounters (job[1])

	# recompute the whole job hierarchy counters
	def _resetJobCounters (self, id, updateParent = True):
		if id != 0:
			cur = self.Conn.cursor ()
			self._execute (cur, "SELECT id FROM Jobs WHERE parent = %d" % id)
			for child in cur:
				self._resetJobCounters (child[0], False)
			self._updateJobCounters (id, updateParent)

	# update this job and its parent counters
	def _updateJobCounters (self, id, updateParent = True):
		if id != 0:
			current_time = int(time.time())
			cur = self.Conn.cursor ()
			total = 0
			working = 0
			errors = 0
			finished = 0
			total_working = 0
			total_errors = 0
			total_finished = 0
			start_time = 0
			duration = 0
			self._execute (cur, "SELECT state, total_working, total_errors, total_finished, total, start_time, duration FROM Jobs WHERE parent = %d" % id)
			for job in cur:
				state = job[0]
				if job[4] == 0:
					total += 1
					if state == 'WORKING':
						working += 1
					elif state == 'ERROR':
						errors += 1
					elif state == 'FINISHED':
						finished += 1
				total_working += job[1]
				total_errors += job[2]
				total_finished += job[3]
				total += job[4]
				if job[5] != 0:
					if start_time == 0:
						start_time = job[5]
					else:
						start_time = min (start_time, job[5])
				if state == 'ERROR' or state == 'FINISHED':
					duration += job[6]
				elif state == 'WORKING':
					duration += (current_time - job[5])
			total_working += working
			total_errors += errors
			total_finished += finished
			# update job counters!
			# note that we also update the start_time as the minimum of
			# all children start times
			_set = ("working = %d, errors = %d, finished = %d, "
					"total_working = %d, total_errors = %d, total_finished = %d, "
					"total = %d" % (working, errors, finished, total_working,
					total_errors, total_finished, total))
			if total > 0:
				_set += ", start_time = %d, duration = %d" % (start_time, duration)
			self._execute (cur, "UPDATE Jobs SET " + _set + (" WHERE id = %d" % id))
			if total > 0:
				self._execute (cur, "SELECT state, parent, user, title, id, progress FROM Jobs WHERE id = %d" % id)
				oldState = cur.fetchone ()
				jobdict = self._rowAsDict (cur, oldState)
				newState = "WAITING"
				if total_errors > 0:
					newState = "ERROR"
				elif total_finished == total:
					newState = "FINISHED"
				elif total_working > 0:
					newState = "WORKING"
				if newState != oldState[0]:
					# parent job is finished!
					# update the duration now!
					if newState == "WAITING" or newState == "PENDING":
						newState = self._isJobPending (id) and "PENDING" or "WAITING"
					self._execute (cur, "UPDATE Jobs SET state = '%s' WHERE id = %d" % (newState, id))
					# and send notification
					if newState == "FINISHED" and self.NotifyFinished:
						self.NotifyFinished (jobdict)
					elif newState == "ERROR" and self.NotifyError:
						self.NotifyError (jobdict)
					# no longer pending, unpause children
					if newState == "WAITING" and oldState[0] == "PENDING":
						self._updateChildren (id)
					# finished job, update dependent jobs
					if newState == "FINISHED":
						self._updateDependentJobsState (id)
				progress = float (total_finished) / total
				if progress != oldState[5]:
					self._execute (cur, "UPDATE Jobs SET progress = %f WHERE id = %d" % (progress, id))

			if updateParent:
				self._execute (cur, "SELECT parent FROM Jobs WHERE id = %d" % id)
				parent = cur.fetchone ()
				if parent is not None:
					self._updateJobCounters (parent[0])

	# update the worker state
	# if passing an error state, increase counters
	def _setWorkerState (self, hostname, state):
		cur = self.Conn.cursor ()
		self._execute (cur, "SELECT state FROM Workers AS worker WHERE name = '%s'" % hostname)
		worker = cur.fetchone ()
		if worker is not None and worker[0] != state:
			if state == "ERROR":
				self._execute (cur, "UPDATE Workers SET state = 'WAITING', error = error+1 WHERE name = '%s'" % hostname)
			elif state == "TIMEOUT":
				self._execute (cur, "UPDATE Workers SET state = 'TIMEOUT', error = error+1 WHERE name = '%s'" % hostname)
			elif state == "FINISHED":
				self._execute (cur, "UPDATE Workers SET state = 'WAITING', finished = finished+1 WHERE name = '%s'" % hostname)
			else:
				self._execute (cur, "UPDATE Workers SET state = '%s' WHERE name = '%s'" % (state, hostname))

	# update children hierarchical values, such as h_priority, h_affinity, h_paused
	def _updateChildren (self, id,  parenth = None):
		cur = self.Conn.cursor ()
		self._execute (cur, "SELECT parent, affinity_bits, priority, paused, state FROM Jobs WHERE id = %d" % id)
		job = cur.fetchone ()
		if job:
			if not parenth:
				self._execute (cur, "SELECT h_depth, h_affinity, h_priority, h_paused FROM Jobs WHERE id = %d" % job[0])
				parenth = cur.fetchone () or (-1, 0, 0, False)
			h_depth = parenth[0]+1
			h_affinity = parenth[1] | job[1]
			h_priority = parenth[2] + (job[2] << (56-h_depth*8))
			h_paused = parenth[3] or job[3] or job[4] == "PENDING"
			self._execute (cur, "UPDATE Jobs SET h_depth = %d, h_affinity = %d, h_priority = %d, h_paused = %d "
				"WHERE id = %d" % (h_depth, h_affinity, h_priority, h_paused, id))
			self._execute (cur, "SELECT id FROM Jobs WHERE parent = %d" % id)
			jobh = [h_depth,h_affinity,h_priority,h_paused]
			for child in cur:
				self._updateChildren (child[0], jobh)

	def _update (self):
		current_time = int(time.time())
		# update timeout jobs no more than every 10 seconds
		if current_time - self.LastUpdate >= 10:
			load = self.RunTime / (current_time - self.LastUpdate)
			if self.Verbose:
				print ("[STAT] %d heartbeats, %d pickjobs, load %f" % (self.HeartBeats, self.PickJobs, load))
			self.HeartBeats = 0
			self.PickJobs = 0
			self.LastUpdate = current_time
			self.RunTime = 0
			cur = self.Conn.cursor ()
			timeout = 60

			# find all working jobs that are running out of time *or*
			# all working jobs which worker is timing out
			self._execute (cur, "SELECT id, worker FROM Jobs "
								"WHERE state = 'WORKING' AND command != '' AND "
									"(timeout != 0 AND %d-start_time > timeout)" %
										current_time)
			for job in cur:
				print ("Job %d timeout!" % job[0])
				self._setJobState (job[0], "ERROR", True)
				self._setWorkerState (job[1], "TIMEOUT")

			for worker in self.Workers:
				info = self.Workers[worker]
				if current_time - info['ping_time'] > timeout and not info['timeout']:
					# worker timeout!
					info['timeout'] = True
					self._execute (cur, "SELECT last_job FROM Workers WHERE name = '%s' AND state = 'WORKING'" % worker)
					data = cur.fetchone ()
					if data is not None:
						self._setJobState (data[0], "WAITING", True)
					if self.getWorker(worker)['state'] == "TERMINATED":
						# State TERMINATED is more explicit than TIMEOUT for terminated instances
						pass
					else:
						self._setWorkerState (worker, "TIMEOUT")

			# If cloud mode has been set via "servermode" option
			if self.cloudconfig:
				cloudprovider = self.config.get('server', 'servermode')
				# Dynamic module loading for configured provider
				self.cloudmanager = import_module('cloud.{}'.format(cloudprovider))
				waitingjobs = self.listJobsByStates("WAITING")
				if len(waitingjobs):
					self._manageWorkerInstanceStart(current_time,
						waitingjobs)
				else:
					self._manageWorkerInstanceTerminate(current_time)

	def _manageWorkerInstanceStart(self, current_time, waitingjobs):
		"""
		Manage worker starting. A new worker is started if the start
		delay is reached, if there are more waiting jobs than available
		workers and the maximum number of instances has not been reached.
		Create an instance via the cloud provider module, create a
		worker reference in the coalition DB and update the delay
		timestamp.
		"""
		if current_time - self.lastworkerinstancestarttime < int(
				self.cloudconfig.get("coalition", "workerinstancestartdelay")):
			return
		availableworkers = self.listWorkersByStates("STARTING", "WORKING", "WAITING")
		if len(waitingjobs) > len(availableworkers) and len(availableworkers) < int(
				self.cloudconfig.get("coalition", "workerinstancemax")):
			name = createWorkerInstanceName(
				self.cloudconfig.get("worker", "nameprefix"))
			self.cloudmanager.startInstance(name, self.cloudconfig)
			self.newWorker(name)
			self._setWorkerState(name, 'STARTING')
			self.lastworkerinstancestarttime = current_time
			if self.Verbose:
				print("[CLOUD] Starting new instance %s" % name)

	def _manageWorkerInstanceTerminate(self, current_time):
		"""
		Manage worker termination. Worker instances are terminated if
		they are not working and they have been living for at least the
		number of second defined by "workerinstancestopdelay". Terminate
		via the cloud provider module, update the coalition DB reference.
		"""
		uselessworkers = self.listWorkersByStates(
			"STARTING", "WAITING", "TIMEOUT")
		if len(uselessworkers):
			for worker in uselessworkers:
				name = worker["name"]
				lastworkerstarttime = self.getWorkerStartTime(name)
				if lastworkerstarttime and (
						current_time - lastworkerstarttime > int(
						self.cloudconfig.get("coalition",
						"workerinstanceminimumlifetime"))):
					self._setWorkerState(name, "TERMINATED")
					self.cloudmanager.stopInstance(name)
					if self.Verbose:
						print("[CLOUD] Terminating instance %s" % name)

	def requiresMigration(self):
		"""
		Check if database requires migration.
		Returns a boolean.
		"""
		return self._getDatabaseVersion() < self._getMigrationVersion()

	def reset (self):
		cur = self.Conn.cursor ()
		self._execute (cur, "DELETE FROM Jobs");
		self._execute (cur, "DELETE FROM Workers");
		self._execute (cur, "DELETE FROM Dependencies");
		self._execute (cur, "DELETE FROM Events");
		self._execute (cur, "DELETE FROM Affinities");
		self._execute (cur, "DELETE FROM WorkerAffinities");


# vim: tabstop=4 noexpandtab shiftwidth=4 softtabstop=4 textwidth=79

