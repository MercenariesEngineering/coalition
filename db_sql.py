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
		priority, affinity, user, finished, errors, working, total, total_finished, total_errors, totalworking, url, progress, progress_pattern):
		with self.Conn:
			cur = self.Conn.cursor()
			self._execute(cur, "INSERT INTO Jobs (parent, title, command, dir, environment, state, worker, start_time, duration, ping_time, run_done, retry,"
				"timeout, priority, affinity, user, finished, errors, working, total, total_finished, total_errors, total_working, url, progress, progress_pattern)"
				" VALUES (%d,%s,%s,%s,%s,%s,%s,%d,%d,%d,%d,%d,%d,%d,%s,%s,%d,%d,%d,%d,%d,%d,%d,%s,%s,%s)" % (parent, convdata(title), convdata(command), convdata(dir), convdata(environment), convdata(state), convdata(worker), starttime, duration, pingtime, _try, retry, timeout, 
				priority, convdata(affinity), convdata(user), finished, errors, working, total, total_finished, total_errors, totalworking, convdata(url), convdata(progress), convdata(progress_pattern)))
			data = cur.fetchone()
			return Job (self, cur.lastrowid, parent, title, command, dir, environment, state, worker, starttime, duration, pingtime, _try, retry, timeout, 
				priority, affinity, user, finished, errors, working, total, total_finished, total_errors, totalworking, url, progress, progress_pattern)

	def deleteJob (self, id):
		with self.Conn:
			cur = self.Conn.cursor()
			self._execute(cur, "DELETE FROM Jobs WHERE id=%d" % id);

	def getJob (self, id):
		if id == 0:
			return self.getRoot ()

		# First try the db cache
		job = self.Jobs.get (id)
		if job:
			return job

		with self.Conn:
			cur = self.Conn.cursor()
			self._execute(cur, "SELECT * FROM Jobs WHERE id=%d" % id);
			row = cur.fetchone()
			if row:
				return Job (self, *row)

	def getJobChildren (self, id):
		with self.Conn:
			cur = self.Conn.cursor()
			self._execute(cur, "SELECT * FROM Jobs WHERE parent=%d" % id);
			rows = cur.fetchall()
			return [(self.Jobs.get (row[0]) or Job (self, *row)) for row in rows]


	def hasJobChildren (self, id):
		with self.Conn:
			cur = self.Conn.cursor()
			self._execute(cur, "SELECT COUNT(Parent) FROM Jobs WHERE parent=%d" % id);
			rows = cur.fetchone()
			return rows[0] > 0

	def getJobDependencies (self, id):
		with self.Conn:
			cur = self.Conn.cursor()
			self._execute(cur, "SELECT job.* FROM Jobs job INNER JOIN Dependencies dep ON job.id = dep.dependency WHERE dep.job_id=%d" % id);
			rows = cur.fetchall()
			return [(self.Jobs.get (row[0]) or Job (self, *row)) for row in rows]

	def setJobDependencies (self, id, dependencies):
		with self.Conn:
			cur = self.Conn.cursor()
			req= "DELETE FROM Dependencies WHERE job_id=%d" % int(id)
			self._execute(cur, req)
			for dep in dependencies:
				req = "INSERT INTO Dependencies (job_id, dependency) VALUES ("+str(id)+","+str(dep)+")"
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
			self._execute(cur, "SELECT * FROM Workers WHERE name=%s" % convdata(name));
			rows = cur.fetchone()
			if rows:
				return Worker (self, *rows)

	def deleteWorker (self, name):
		with self.Conn:
			cur = self.Conn.cursor()
			self._execute(cur, "DELETE FROM Workers WHERE name=%s" % convdata(name));

	def newEvent (self, worker, job, jobTitle, state, start, duration):
		with self.Conn:
			cur = self.Conn.cursor()
			self._execute(cur, "INSERT INTO Events (worker, job_id, job_title, state, start, duration) VALUES (%s, %d, %s, %s, %d, %d)" % (convdata(worker), job, convdata(jobTitle), convdata(state), start, duration))
			data = cur.fetchone()
			return Event (self, cur.lastrowid, worker, job, jobTitle, state, start, duration)

	def getEvent (self, id):
		with self.Conn:
			cur = self.Conn.cursor()
			self._execute(cur, "SELECT * FROM Events WHERE id=%d" % id);
			rows = cur.fetchone()
			if rows:
				return Event (self, *rows)

	def getEvents (self, job, worker, howlong):
		with self.Conn:
			cur = self.Conn.cursor()
			req = "SELECT * FROM Events WHERE start>%d" % (int(time.time())-howlong)
			if worker:
				req += " AND worker=%s" % convdata(worker)
			if job > 0:
				req += " AND job_id=%d" % job
			self._execute(cur, req);
			rows = cur.fetchall()
			return [Event (self, *row) for row in rows]

	'''From class DB'''
	def edit (self, jobs, workers, events):
		with self.Conn:
			cur = self.Conn.cursor()
			for id,attr in jobs.iteritems():
				# Remove dependencies from the list
				toUpdate = [k+"="+convdata(v) for k,v in attr.iteritems() if k != 'dependencies']
				if toUpdate:
					req = "UPDATE Jobs SET " + ",".join(toUpdate) + " WHERE id=" + str(id) + ""
					self._execute(cur, req)
					cur.fetchall()
				# Special case for dependencies
				if attr.get('dependencies'):
					self.setJobDependencies (id, attr['dependencies'])
			for name,attr in workers.iteritems():
				req = "UPDATE Workers SET " + ",".join([k+"="+convdata(v) for k,v in attr.iteritems()]) + " WHERE name='" + name + "'"
				self._execute(cur, req)
				cur.fetchall()
			for id,attr in events.iteritems():
				req = "UPDATE Events SET " + ",".join([k+"="+convdata(v) for k,v in attr.iteritems()]) + " WHERE id=" + str(id)
				self._execute(cur, req)
				cur.fetchall()
