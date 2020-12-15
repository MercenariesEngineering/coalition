# -*- coding: utf-8 -*-

import time


class DB(object):
	def __init__(self):
		self.IntoWith = False

	'''Enter a transaction block'''
	def __enter__(self):

		self.Jobs = {}
		self.Worker = {}

		# Those map are the edits done on every objects to commit at the end of the transaction
		self.JobsToUpdate = {}
		self.WorkersToUpdate = {}

		self.IntoWith = True

	'''Leave a transaction block'''
	def __exit__ (self, type, value, traceback):
		self.IntoWith = False
		if not isinstance(value, TypeError):
			self.editJobs(self.JobsToUpdate)
			self.editWorkers(self.WorkersToUpdate)

	def getRoot (self):
		return Job (self, 0, 0, "Root", "", "", "", "", "", 0, 0, 0, 0, 0, 0,  0, "", "", 0, 0, 0, 0, 0, 0, 0, "", "", "")


class Worker(object):
	'''
	The database proxy object for a worker

	This object is readonly outside a transaction block.
	'''
	def __init__ (self, db, values):
		self.db = db
		self.name = values['name']
		self.Data = values
		# Should not exist in the cache
		assert (db.Workers.get (self.name) == None)
		# Cache it
		db.Workers[self.name] = self

	def __setattr__(self, attr, value):
		# Backup the value for delayed writting
		db = super (object, self).__getattr__ ('db')
		name = super (object, self).__getattr__ ('name')
		data = super (object, self).__getattr__ ('data')
		if not db.IntoWith:
			raise Exception
		w = db.WorkerToUpdate.get (name)
		if not w:
			w = {}
			db.WorkersToUpdate[name] = w
		w[attr] = value
		data[attr] = value

	def __getattr__(self, attr):
		data = super (object, self).__getattr__ ('data')
		return data[attr]


class Job(object):
	'''
	The database proxy object for a job

	This object is readonly outside a transaction block.
	'''
	def __init__ (self, db, values):
		self.db = db
		self.id = values['id']
		self.Data = values
		# Should not exist in the cache
		assert (db.Jobs.get (self.id) == None)
		# Cache it
		db.Jobs[self.id] = self

	def __setattr__(self, attr, value):
		# Backup the value for delayed writting
		db = super (object, self).__getattr__ ('db')
		id = super (object, self).__getattr__ ('id')
		data = super (object, self).__getattr__ ('data')
		if not db.IntoWith:
			raise Exception
		w = db.WorkerToUpdate.get (id)
		if not w:
			w = {}
			db.WorkersToUpdate[id] = w
		w[attr] = value
		data[attr] = value

	def __getattr__(self, attr):
		data = super (object, self).__getattr__ ('data')
		return data[attr]


# vim: tabstop=4 noexpandtab shiftwidth=4 softtabstop=4 textwidth=79

