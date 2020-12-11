import sys
import MySQLdb
from db_sql import DBSQL

class DBMySQL(DBSQL):

	class Context:
		def __init__ (self, db, conn):
			self.DB = db
			self.Conn = conn
			self.Conn.ping(True)
			self.Conn.autocommit = False

		def __enter__(self):
			pass

		def __exit__ (self, type, value, traceback):
			if not isinstance(value, TypeError):
				self.Conn.commit ()
			else:
				self.Conn.rollback ()

		def cursor (self):
			return self.Conn.cursor ()


	def __init__ (self, host, user, password, database, **kwargs):
		self.config = kwargs["config"]
		self.cloudconfig = kwargs["cloudconfig"]
		self.Conn = self.Context (self, MySQLdb.connect(host, user, password, database))
		# super is called *after* because DBSQL inits stuffs in the DB
		super(DBMySQL, self).__init__()
