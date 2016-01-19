import sqlite3, unittest, time
from db_sql import DBSQL

class DBSQLite(DBSQL):
	def __init__ (self, database):
		super(DBSQLite, self).__init__ ()

		self.Conn = sqlite3.connect(database)
		with self.Conn:
			cur = self.Conn.cursor()
			cur.execute('CREATE TABLE IF NOT EXISTS Jobs(id INTEGER PRIMARY KEY AUTOINCREMENT, parent INT, title TEXT, command TEXT, dir TEXT, environment TEXT, state TEXT, '
				'worker TEXT, start_time INT, duration INT, ping_time INT, run_done INT, retry INT, timeout INT, priority INT, affinity TEXT, user TEXT, finished INT, errors INT, '
				'working INT, total INT, total_finished INT, total_errors INT, total_working INT, url TEXT, progress FLOAT, progress_pattern TEXT)')

			cur.execute('CREATE INDEX IF NOT EXISTS Parent_index ON Jobs(parent)')

			cur.execute('CREATE TABLE IF NOT EXISTS Dependencies(job_id Int, dependency INT)')
			cur.execute('CREATE INDEX IF NOT EXISTS JobId_index ON Dependencies(job_id)')
			cur.execute('CREATE INDEX IF NOT EXISTS Dependency_index ON Dependencies(dependency)')

			cur.execute('CREATE TABLE IF NOT EXISTS Workers(name TEXT, ip TEXT, affinity TEXT, state TEXT, ping_time INT, finished INT, error INT, last_job INT, current_event INT, cpu TEXT, free_memory INT, total_memory int, active BOOLEAN)')
			cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS Name_index ON Workers (name)')

			cur.execute('CREATE TABLE IF NOT EXISTS Events(id INTEGER PRIMARY KEY AUTOINCREMENT, worker TEXT, job_id INT, job_title TEXT, state TEXT, start INT, duration INT)')
			cur.execute('CREATE INDEX IF NOT EXISTS Worker_index ON Events(worker)')
			cur.execute('CREATE INDEX IF NOT EXISTS JobID_index ON Events(job_id)')
			cur.execute('CREATE INDEX IF NOT EXISTS Start_index ON Events(start)')
			data = cur.fetchone()
