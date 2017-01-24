# -*- coding: utf-8 -*-

import MySQLdb
from db_sql import DBSQL

class DBMySQL(DBSQL):

	def __init__ (self, host, user, password, database, **kwargs):
		self.config = kwargs["config"]
		self.cloudconfig = kwargs["cloudconfig"]
		self.Conn = MySQLdb.connect(host, user, password, database)
		self.Conn.ping(True)
		super(DBMySQL, self).__init__()

# vim: tabstop=4 noexpandtab shiftwidth=4 softtabstop=4 textwidth=79

