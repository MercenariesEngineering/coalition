from db import *
import sys

def convdata (d):
	return isinstance(d, str) and repr (d) or (isinstance(d, bool) and (d and '1' or '0') or (isinstance(d, unicode) and repr(str(d)) or str(d)))

class DBSQL(DB):
	def __init__ (self):
		super(DBSQL, self).__init__ ()

	def _execute (self, cur, req, data=None):
		print "[SQL] " + req
		sys.stdout.flush()
		if data:
			cur.execute (req, data)
		else:
			cur.execute (req)

	def newJob (self, parent, title, command, dir, environment, state, worker, starttime, duration, pingtime, _try, retry, timeout, 
		priority, affinity, user, finished, errors, working, total, totalfinished, totalerrors, totalworking, url, localprogressionpattern, globalprogressionpattern):
		with self.Conn:
			cur = self.Conn.cursor()
			self._execute(cur, "INSERT INTO Jobs (Parent, Title, Command, Dir, Environment, State, Worker, StartTime, Duration, PingTime, Try, Retry,"
				"TimeOut, Priority, Affinity, User, Finished, Errors, Working, Total, TotalFinished, TotalErrors, TotalWorking, URL, LocalProgress, GlobalProgress)"
				" VALUES (%d,%s,%s,%s,%s,%s,%s,%d,%d,%d,%d,%d,%d,%d,%s,%s,%d,%d,%d,%d,%d,%d,%d,%s,%s,%s)" % (parent, convdata(title), convdata(command), convdata(dir), convdata(environment), convdata(state), convdata(worker), starttime, duration, pingtime, _try, retry, timeout, 
				priority, convdata(affinity), convdata(user), finished, errors, working, total, totalfinished, totalerrors, totalworking, convdata(url), convdata(localprogressionpattern), convdata(globalprogressionpattern)))
			data = cur.fetchone()
			return Job (self, cur.lastrowid, parent, title, command, dir, environment, state, worker, starttime, duration, pingtime, _try, retry, timeout, 
				priority, affinity, user, finished, errors, working, total, totalfinished, totalerrors, totalworking, url, localprogressionpattern, globalprogressionpattern)

	def removeJob (self, id):
		with self.Conn:
			cur = self.Conn.cursor()
			self._execute(cur, "DELETE FROM Jobs WHERE ID=%d" % id);

	def getJob (self, id):
		if id == 0:
			return self.getRoot ()

		# First try the DB cache
		job = self.Jobs.get (id)
		if job:
			return job

		with self.Conn:
			cur = self.Conn.cursor()
			self._execute(cur, "SELECT * FROM Jobs WHERE ID=%d" % id);
			row = cur.fetchone()
			if row:
				return Job (self, *row)

	def getJobChildren (self, id):
		with self.Conn:
			cur = self.Conn.cursor()
			self._execute(cur, "SELECT * FROM Jobs WHERE Parent=%d" % id);
			rows = cur.fetchall()
			return [(self.Jobs.get (row[0]) or Job (self, *row)) for row in rows]


	def hasJobChildren (self, id):
		with self.Conn:
			cur = self.Conn.cursor()
			self._execute(cur, "SELECT COUNT(Parent) FROM Jobs WHERE Parent=%d" % id);
			rows = cur.fetchone()
			return rows[0] > 0

	def getJobDependencies (self, id):
		with self.Conn:
			cur = self.Conn.cursor()
			self._execute(cur, "SELECT job.* FROM Jobs job INNER JOIN Dependencies dep ON job.ID = dep.Dependency WHERE dep.JobId=%d" % id);
			rows = cur.fetchall()
			return [(self.Jobs.get (row[0]) or Job (self, *row)) for row in rows]

	def setJobDependencies (self, id, dependencies):
		with self.Conn:
			cur = self.Conn.cursor()
			req= "DELETE FROM Dependencies WHERE JobID=%d" % int(id)
			self._execute(cur, req)
			for dep in dependencies:
				req = "INSERT INTO Dependencies (JobId, Dependency) VALUES ("+str(id)+","+str(dep)+")"
				self._execute(cur, req)
			cur.fetchall()

	def getWorkers (self):
		with self.Conn:
			cur = self.Conn.cursor()
			self._execute(cur, 'SELECT * FROM Workers');
			rows = cur.fetchall()
			return [Worker (self, *row) for row in rows]

	def newWorker (self, name, time):
		with self.Conn:
			cur = self.Conn.cursor()
			self._execute(cur, "INSERT INTO Workers VALUES (%s, '', '', 'WAITING', %d, 0, 0, -1, -1, '[0]', 0, 0, 1)" % (convdata(name), time))
			data = cur.fetchone()
			return self.getWorker (name)

	def getWorker (self, name):
		with self.Conn:
			cur = self.Conn.cursor()
			self._execute(cur, "SELECT * FROM Workers WHERE Name=%s" % convdata(name));
			rows = cur.fetchone()
			if rows:
				return Worker (self, *rows)

	def newEvent (self, worker, job, jobTitle, state, start, duration):
		with self.Conn:
			cur = self.Conn.cursor()
			self._execute(cur, "INSERT INTO Events (Worker, JobID, JobTitle, State, Start, Duration) VALUES (%s, %d, %s, %s, %d, %d)" % (convdata(worker), job, convdata(jobTitle), convdata(state), start, duration))
			data = cur.fetchone()
			return Event (self, cur.lastrowid, worker, job, jobTitle, state, start, duration)

	def getEvent (self, id):
		with self.Conn:
			cur = self.Conn.cursor()
			self._execute(cur, "SELECT * FROM Events WHERE ID=%d" % id);
			rows = cur.fetchone()
			if rows:
				return Event (self, *rows)

	def getEvents (self, job, worker, howlong):
		with self.Conn:
			cur = self.Conn.cursor()
			req = "SELECT * FROM Events WHERE Start>%d" % (int(time.time())-howlong)
			if worker:
				req += " AND Worker=%s" % convdata(worker)
			if job > 0:
				req += " AND JobID=%d" % job
			self._execute(cur, req);
			rows = cur.fetchall()
			return [Event (self, *row) for row in rows]

	'''From class DB'''
	def edit (self, jobs, workers, events):
		with self.Conn:
			cur = self.Conn.cursor()
			for id,attr in jobs.iteritems():
				# Remove dependencies from the list
				toUpdate = [k+"="+convdata(v) for k,v in attr.iteritems() if k != 'Dependencies']
				if toUpdate:
					req = "UPDATE Jobs SET " + ",".join(toUpdate) + " WHERE ID=" + str(id) + ""
					self._execute(cur, req)
					cur.fetchall()
				# Special case for dependencies
				if attr.get('Dependencies'):
					self.setJobDependencies (id, attr['Dependencies'])
			for name,attr in workers.iteritems():
				req = "UPDATE Workers SET " + ",".join([k+"="+convdata(v) for k,v in attr.iteritems()]) + " WHERE Name='" + name + "'"
				self._execute(cur, req)
				cur.fetchall()
			for id,attr in events.iteritems():
				req = "UPDATE Events SET " + ",".join([k+"="+convdata(v) for k,v in attr.iteritems()]) + " WHERE ID=" + str(id)
				self._execute(cur, req)
				cur.fetchall()
