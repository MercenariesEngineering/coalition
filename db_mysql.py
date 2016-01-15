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
			cur.execute('CREATE TABLE IF NOT EXISTS Jobs(ID INTEGER PRIMARY KEY AUTO_INCREMENT, Parent INT, Title TEXT, Command TEXT, Dir TEXT, Environment TEXT, State TEXT, '
				'Worker TEXT, StartTime INT, Duration INT, PingTime INT, Try INT, Retry INT, TimeOut INT, Priority INT, Affinity TEXT, User TEXT, Finished INT, Errors INT, '
				'Working INT, Total INT, TotalFinished INT, TotalErrors INT, TotalWorking INT, URL TEXT, LocalProgress TEXT, GlobalProgress TEXT)')

			def createKeySafe (table, column, opt=""):
				cur.execute('SHOW INDEX FROM %s WHERE Column_name="%s"' % (table, column))
				data = cur.fetchone()
				if not data:
					cur.execute('CREATE %s INDEX %s_index ON %s(%s)' % (opt, column, table, column))

			createKeySafe ('Jobs', 'Parent')

			cur.execute('CREATE TABLE IF NOT EXISTS Dependencies(JobId Int, Dependency INT)')
			
			createKeySafe ('Dependencies', 'JobId')
			createKeySafe ('Dependencies', 'Dependency')

			cur.execute('CREATE TABLE IF NOT EXISTS Workers(Name VARCHAR(255), IP TEXT, Affinity TEXT, State TEXT, PingTime INT, Finished INT, Error INT, LastJob INT, CurrentActivity INT, CPU TEXT, FreeMemory INT, TotalMemory int, Active BOOLEAN)')
			createKeySafe ('Workers', 'Name', 'UNIQUE')

			cur.execute('CREATE TABLE IF NOT EXISTS Events(ID INTEGER PRIMARY KEY AUTO_INCREMENT, Worker VARCHAR(255), JobID INT, JobTitle TEXT, State TEXT, Start INT, Duration INT)')
			createKeySafe ('Events', 'Worker')
			createKeySafe ('Events', 'JobID')
			createKeySafe ('Events', 'Start')
