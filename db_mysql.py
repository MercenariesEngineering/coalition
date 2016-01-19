import MySQLdb, unittest
from db_sql import DBSQL

class DBMySQL(DBSQL):
	def __init__ (self, host, user, password, db):
		super(DBMySQL, self).__init__ ()
		self.Conn = MySQLdb.connect(host, user, password, db)
		with self.Conn:
			cur = self.Conn.cursor()

			'''	cur.execute('DROP TABLE Jobs')
			cur.execute('DROP TABLE Events')
			cur.execute('DROP TABLE Workers')
			cur.execute('DROP TABLE Dependencies')
			'''
			cur.execute('CREATE TABLE IF NOT EXISTS Jobs(id INTEGER PRIMARY KEY AUTO_INCREMENT, parent INT, title TEXT, command TEXT, dir TEXT, environment TEXT, state TEXT, '
				'worker TEXT, start_time INT, duration INT, ping_time INT, run_done INT, retry INT, timeout INT, priority INT, affinity TEXT, user TEXT, finished INT, errors INT, '
				'working INT, total INT, total_finished INT, total_errors INT, total_working INT, url TEXT, progress FLOAT, progress_pattern TEXT)')

			def createKeySafe (table, column, opt=""):
				cur.execute('SHOW INDEX FROM %s WHERE Column_name="%s"' % (table, column))
				data = cur.fetchone()
				if not data:
					cur.execute('CREATE %s INDEX %s_index ON %s(%s)' % (opt, column, table, column))

			createKeySafe ('Jobs', 'parent')

			cur.execute('CREATE TABLE IF NOT EXISTS Dependencies(job_id Int, dependency INT)')
			
			createKeySafe ('Dependencies', 'job_id')
			createKeySafe ('Dependencies', 'dependency')

			cur.execute('CREATE TABLE IF NOT EXISTS Workers(name VARCHAR(255), ip TEXT, affinity TEXT, state TEXT, ping_time INT, finished INT, error INT, last_job INT, current_event INT, cpu TEXT, free_memory INT, total_memory int, active BOOLEAN)')
			createKeySafe ('Workers', 'name', 'UNIQUE')

			cur.execute('CREATE TABLE IF NOT EXISTS Events(id INTEGER PRIMARY KEY AUTO_INCREMENT, worker VARCHAR(255), job_id INT, job_title TEXT, state TEXT, start INT, duration INT)')
			createKeySafe ('Events', 'worker')
			createKeySafe ('Events', 'job_id')
			createKeySafe ('Events', 'start')
