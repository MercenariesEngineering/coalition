import sqlite3, unittest, time
from db_sql import DBSQL

class DBSQLite(DBSQL):
	def __init__ (self, database):
		super(DBSQLite, self).__init__ ()

		self.Conn = sqlite3.connect(database)
		with self.Conn:
			cur = self.Conn.cursor()
			cur.execute('CREATE TABLE IF NOT EXISTS Jobs(ID INTEGER PRIMARY KEY AUTOINCREMENT, Parent INT, Title TEXT, Command TEXT, Dir TEXT, Environment TEXT, State TEXT, '
				'Worker TEXT, StartTime INT, Duration INT, PingTime INT, Try INT, Retry INT, TimeOut INT, Priority INT, Affinity TEXT, User TEXT, Finished INT, Errors INT, '
				'Working INT, Total INT, TotalFinished INT, TotalErrors INT, TotalWorking INT, URL TEXT, LocalProgress TEXT, GlobalProgress TEXT)')

			cur.execute('CREATE INDEX IF NOT EXISTS Parent_index ON Jobs(Parent)')

			cur.execute('CREATE TABLE IF NOT EXISTS Dependencies(JobId Int, Dependency INT)')
			cur.execute('CREATE INDEX IF NOT EXISTS JobId_index ON Dependencies(JobId)')
			cur.execute('CREATE INDEX IF NOT EXISTS Dependency_index ON Dependencies(Dependency)')

			cur.execute('CREATE TABLE IF NOT EXISTS Workers(Name TEXT, IP TEXT, Affinity TEXT, State TEXT, PingTime INT, Finished INT, Error INT, LastJob INT, CurrentActivity INT, CPU TEXT, FreeMemory INT, TotalMemory int, Active BOOLEAN)')
			cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS Name_index ON Workers (Name)')

			cur.execute('CREATE TABLE IF NOT EXISTS Events(ID INTEGER PRIMARY KEY AUTOINCREMENT, Worker TEXT, JobID INT, JobTitle TEXT, State TEXT, Start INT, Duration INT)')
			cur.execute('CREATE INDEX IF NOT EXISTS Worker_index ON Events(Worker)')
			cur.execute('CREATE INDEX IF NOT EXISTS JobID_index ON Events(JobID)')
			cur.execute('CREATE INDEX IF NOT EXISTS Start_index ON Events(Start)')
			data = cur.fetchone()
