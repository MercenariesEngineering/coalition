import MySQLdb, unittest
from db_sql import DBSQL

class DBMySQL(DBSQL):
	def __init__ (self, host, user, password, database, **kwargs):
		self.config = kwargs["config"]
		self.cloudconfig = kwargs["cloudconfig"]
		self.Conn = MySQLdb.connect(host, user, password, database)
		with self.Conn:
			cur = self.Conn.cursor()

			'''	cur.execute('DROP TABLE Jobs')
			cur.execute('DROP TABLE Events')
			cur.execute('DROP TABLE Workers')
			cur.execute('DROP TABLE Dependencies')
			'''

			def createKeySafe (table, column, opt=""):
				cur.execute('SHOW INDEX FROM %s WHERE Column_name="%s"' % (table, column))
				data = cur.fetchone()
				if not data:
					cur.execute('CREATE %s INDEX %s_index ON %s(%s)' % (opt, column, table, column))

			cur.execute('CREATE TABLE IF NOT EXISTS Jobs(id INTEGER PRIMARY KEY AUTO_INCREMENT, '
				'parent INT DEFAULT 0, title TEXT DEFAULT "", command TEXT DEFAULT "", dir TEXT DEFAULT "", '
				'environment TEXT DEFAULT "", state TEXT DEFAULT "", paused BOOLEAN DEFAULT 0, '
				'worker TEXT DEFAULT "", start_time INT DEFAULT 0, duration INT DEFAULT 0, run_done INT DEFAULT 0, '
				'timeout INT DEFAULT 0, priority INT UNSIGNED DEFAULT 8, '
				'affinity TEXT DEFAULT "", affinity_bits BIGINT DEFAULT 0, '
				'user TEXT DEFAULT "", finished INT DEFAULT 0, errors INT DEFAULT 0, working INT DEFAULT 0, total INT DEFAULT 0, '
				'total_finished INT DEFAULT 0, total_errors INT DEFAULT 0, total_working INT DEFAULT 0, url TEXT DEFAULT "", '
				'progress FLOAT, progress_pattern TEXT DEFAULT "", '
				'h_affinity BIGINT DEFAULT 0, h_priority BIGINT UNSIGNED DEFAULT 0, h_paused BOOLEAN DEFAULT 0, h_depth INT DEFAULT 0)')

			createKeySafe ('Jobs', 'parent')

			cur.execute('CREATE TABLE IF NOT EXISTS Dependencies(job_id Int, dependency INT)')
			
			createKeySafe ('Dependencies', 'job_id')
			createKeySafe ('Dependencies', 'dependency')

			cur.execute('CREATE TABLE IF NOT EXISTS Workers(name VARCHAR(255), start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, ip TEXT, affinity TEXT DEFAULT "", affinity_bits BIGINT DEFAULT 0, state TEXT, finished INT, error INT, last_job INT, current_event INT, cpu TEXT, free_memory INT, total_memory int, active BOOLEAN)')
			createKeySafe ('Workers', 'name', 'UNIQUE')

			cur.execute('CREATE TABLE IF NOT EXISTS Events(id INTEGER PRIMARY KEY AUTO_INCREMENT, worker VARCHAR(255), job_id INT, job_title TEXT, state TEXT, start INT, duration INT)')
			createKeySafe ('Events', 'worker')
			createKeySafe ('Events', 'job_id')
			createKeySafe ('Events', 'start')

			cur.execute('CREATE TABLE IF NOT EXISTS Affinities(id INTEGER, name TEXT)')

			data = cur.fetchone()
		# super is called *after* because DBSQL inits stuffs in the DB
		super(DBMySQL, self).__init__ ()
