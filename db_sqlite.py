import sqlite3, unittest, time
from db_sql import DBSQL

class DBSQLite(DBSQL):
	def __init__ (self, database, **kwargs):
		self.config = kwargs["config"]
		self.cloudconfig = kwargs["cloudconfig"]
		self.Conn = sqlite3.connect(database)
		with self.Conn:
			cur = self.Conn.cursor()

			cur.execute( 'CREATE TABLE IF NOT EXISTS WorkerAffinities ( id INTEGER PRIMARY KEY AUTOINCREMENT, worker_name TEXT, affinity BIGINT DEFAULT 0, ordering INT DEFAULT 0 )' )
			cur.execute( 'CREATE INDEX IF NOT EXISTS worker_name_index ON WorkerAffinities( worker_name ) ' )
			
			cur.execute('CREATE TABLE IF NOT EXISTS Jobs(id INTEGER PRIMARY KEY AUTOINCREMENT, '
				'parent INT DEFAULT 0, title TEXT DEFAULT "", command TEXT DEFAULT "", dir TEXT DEFAULT ".", '
				'environment TEXT DEFAULT "", state TEXT DEFAULT "WAITING", paused BOOLEAN DEFAULT 0, '
				'worker TEXT DEFAULT "", start_time INT DEFAULT 0, duration INT DEFAULT 0, run_done INT DEFAULT 0, '
				'timeout INT DEFAULT 0, priority UNSIGNED INT DEFAULT 8, '
				'affinity TEXT DEFAULT "", affinity_bits BIGINT DEFAULT 0, '
				'user TEXT DEFAULT "", finished INT DEFAULT 0, errors INT DEFAULT 0, working INT DEFAULT 0, total INT DEFAULT 0, '
				'total_finished INT DEFAULT 0, total_errors INT DEFAULT 0, total_working INT DEFAULT 0, url TEXT DEFAULT "", '
				'progress FLOAT, progress_pattern TEXT DEFAULT "", '
				'h_affinity BIGINT DEFAULT 0, h_priority UNSIGNED BIGINT DEFAULT 0, h_paused BOOLEAN DEFAULT 0, h_depth INT DEFAULT 0)')

			cur.execute('CREATE INDEX IF NOT EXISTS Parent_index ON Jobs(parent)')

			cur.execute('CREATE TABLE IF NOT EXISTS Dependencies(job_id Int, dependency INT)')
			cur.execute('CREATE INDEX IF NOT EXISTS JobId_index ON Dependencies(job_id)')
			cur.execute('CREATE INDEX IF NOT EXISTS Dependency_index ON Dependencies(dependency)')

			cur.execute('CREATE TABLE IF NOT EXISTS Workers(name TEXT, start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, ip TEXT, affinity TEXT DEFAULT "", affinity_bits BIGINT DEFAULT 0, state TEXT, finished INT, error INT, last_job INT, current_event INT, cpu TEXT, free_memory INT, total_memory int, active BOOLEAN)')
			cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS Name_index ON Workers (name)')

			cur.execute('CREATE TABLE IF NOT EXISTS Events(id INTEGER PRIMARY KEY AUTOINCREMENT, worker TEXT, job_id INT, job_title TEXT, state TEXT, start INT, duration INT)')
			cur.execute('CREATE INDEX IF NOT EXISTS Worker_index ON Events(worker)')
			cur.execute('CREATE INDEX IF NOT EXISTS JobID_index ON Events(job_id)')
			cur.execute('CREATE INDEX IF NOT EXISTS Start_index ON Events(start)')

			cur.execute('CREATE TABLE IF NOT EXISTS Affinities(id INTEGER, name TEXT)')

			data = cur.fetchone()
		# super is called *after* because DBSQL inits stuffs in the DB
		super(DBSQLite, self).__init__ ()
