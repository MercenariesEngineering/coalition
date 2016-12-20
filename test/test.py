#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=4 noexpandtab shiftwidth=4 softtabstop=4

import subprocess, time, os, unittest, httplib, json, coalition, sys, doctest

workerCount = 1
server = True
verboseServer = True
verboseWorker = True
verbose = True;

if os.path.isfile ("test.db"):
	os.remove ("test.db")

host = "localhost"
port = 19211
url = "http://%s:%d" % (host, port)

try:
	time.sleep(3)
	conn = coalition.Connection (host, port)

	class TestCoalition(unittest.TestCase):

	  def test_000dependencies(self):
		jobCount = 10

		depJobID = conn.newJob (command="echo dependencies", title="jobDependencies", state='PAUSED')
		self.assertNotEqual (depJobID, None)

		parentID = conn.newJob (title="parent")
		self.assertNotEqual (parentID, None)

		childrenID = []
	  	for i in range(0, jobCount):
			childrenID.append (conn.newJob (command="echo 'job%d'" % i, title="job%d" % i, parent=parentID, state='PAUSED'))

		depJob = conn.getJob (depJobID)
		self.assertEqual(depJob.id, depJobID)
		self.assertEqual(depJob.title, 'jobDependencies')
		self.assertEqual(depJob.command, 'echo dependencies')
		self.assertEqual(depJob.state, "PAUSED")

		# Set the dependencies
		conn.setJobDependencies (depJob.id, childrenID)
		depsJobs = conn.getJobDependencies (depJob.id)
		depsID = [job.id for job in depsJobs]
		# Check childrenID and depsID are equal
		self.assertTrue(any(map(lambda v: v in childrenID, depsID)))

		# Start all the jobs
		with conn:
			depJob.state = 'WAITING'
			jobs = conn.getJobChildren (parentID)
			for job in jobs:
				job.state = 'WAITING'

		depJob = conn.getJob (depJobID)
		self.assertNotEqual(depJob.state, "PAUSED")

		jobs = conn.getJobChildren (parentID)
		for k,job in enumerate(jobs):
			self.assertEqual(job.id, childrenID[k])
			self.assertEqual(job.title, 'job%d'%k)
			self.assertEqual(job.command, "echo 'job%d'"%k)
			self.assertNotEqual(job.state, 'PAUSED')

		print "Waiting job end.."
		sys.stdout.flush ()
	  	while (True):
			depJob = conn.getJob (depJobID)
			if depJob.state == "FINISHED":
				
				# All children must be finished
				for id in childrenID:
					job = conn.getJob (id)
					self.assertEqual(job.state, "FINISHED")

				# The parent node must by finished without errors
				parent = conn.getJob (parentID)
				#self.assertEqual (parent.state, "FINISHED")
				self.assertEqual (parent.finished, jobCount)
				self.assertEqual (parent.working, 0)
				self.assertEqual (parent.errors, 0)
				self.assertEqual (parent.run_done, 0)

				return
			time.sleep (.1)

	if __name__ == '__main__':
   		doctest.testmod(coalition)
   		suite = unittest.TestLoader().loadTestsFromTestCase(TestCoalition)
		unittest.TextTestRunner(verbosity=2).run(suite)		

finally:
	pass
