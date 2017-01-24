# -*- coding: utf-8 -*-

import sqlite3
from db_sql import DBSQL


class DBSQLite(DBSQL):
	def __init__(self, database, **kwargs):
		self.config = kwargs["config"]
		self.cloudconfig = kwargs["cloudconfig"]
		self.Conn = sqlite3.connect(database)
		super(DBSQLite, self).__init__()

# vim: tabstop=4 noexpandtab shiftwidth=4 softtabstop=4 textwidth=79

