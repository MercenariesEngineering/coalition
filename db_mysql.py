import MySQLdb
from db_sql import DBSQL

class DBMySQL(DBSQL):

	def __init__ (self, host, user, password, database, **kwargs):
		self.config = kwargs["config"]
		self.cloudconfig = kwargs["cloudconfig"]
		self.Conn = MySQLdb.connect(host, user, password, database)
		self.Conn.ping(True)
		# super is called *after* because DBSQL inits stuffs in the DB
		super(DBMySQL, self).__init__()
