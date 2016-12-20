#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=4 noexpandtab shiftwidth=4 softtabstop=4

import os, sys

sys.path.append( "api" )

import subprocess, time, os, unittest, httplib, json, coalition, sys, doctest
from subprocess import Popen, PIPE

processes = [] # Store processes


def launch_workers():

    for i in range( 0, 4 ): # Launch 4 workers
        p = Popen( [ "python", "worker.py", "-nw%d" % i, "http://localhost:19211" ], stderr = PIPE, stdout = PIPE )
        processes.append( p )

def launch_server():

    p = Popen( [ "python", "server.py" ] ) # Launch a server process
    processes.append( p )

def launch_test():
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


    		affinities = {}
    		for i in range( 1, 65 ):
    			affinities[str(i)] = ""

    		affinities["1"] = "linux"
    		affinities["2"] = "win"
    		affinities["3"] = "windows playmobil"
    		affinities["4"] = "windows"
    		affinities["5"] = "dos"

    		aff = conn.setAffinities( affinities )

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

    		firstSleepJobId = conn.newJob( command = "sleep 3", title = "First Job", state = "WAITING", affinity = "linux", priority = 128 )
    		firstSleepJob = conn.getJob( firstSleepJobId )
    		self.assertEqual( firstSleepJob.id, firstSleepJobId )
    		self.assertEqual( firstSleepJob.title, "First Job" )
    		self.assertEqual( firstSleepJob.command, "sleep 3" )
    		self.assertEqual( firstSleepJob.state, "WAITING" )
    		self.assertEqual( firstSleepJob.affinity, "linux" )
    		self.assertEqual( firstSleepJob.priority, 128 )

    		secondSleepJobId = conn.newJob( command = "sleep 3", title = "Second Job", state = "WAITING", affinity = "windows", priority = 127 )
    		secondSleepJob = conn.getJob( secondSleepJobId )
    		self.assertEqual( secondSleepJob.id, secondSleepJobId )
    		self.assertEqual( secondSleepJob.title, "Second Job" )
    		self.assertEqual( secondSleepJob.command, "sleep 3" )
    		self.assertEqual( secondSleepJob.state, "WAITING" )
    		self.assertEqual( secondSleepJob.affinity, "windows" )
    		self.assertEqual( secondSleepJob.priority, 127 )

    		# Test that all the jobs with an affinity are taken first (as long as there is a worker matching this affinity)
    		windowsPlaymobilJobId = conn.newJob( command = "sleep 3", title = "Windows Playmobil", state = "WAITING", affinity = "windows playmobil", priority = 127 )
    		windowsPlaymobilJob = conn.getJob( windowsPlaymobilJobId )
    		self.assertEqual( windowsPlaymobilJob.id, windowsPlaymobilJobId )
    		self.assertEqual( windowsPlaymobilJob.title, "Windows Playmobil" )
    		self.assertEqual( windowsPlaymobilJob.command, "sleep 3" )
    		self.assertEqual( windowsPlaymobilJob.state, "WAITING" )
    		self.assertEqual( windowsPlaymobilJob.affinity, "windows playmobil" )
    		self.assertEqual( windowsPlaymobilJob.priority, 127 )

    		winJobId = conn.newJob( command = "sleep 3", title = "Win", state = "WAITING", affinity = "win", priority = 127 )
    		winJob = conn.getJob( winJobId )
    		self.assertEqual( winJob.id, winJobId )
    		self.assertEqual( winJob.title, "Win" )
    		self.assertEqual( winJob.command, "sleep 3" )
    		self.assertEqual( winJob.state, "WAITING" )
    		self.assertEqual( winJob.affinity, "win" )
    		self.assertEqual( winJob.priority, 127 )

    		dosJobId = conn.newJob( command = "sleep 3", title = "Dos", state = "WAITING", affinity = "dos", priority = 127 )
    		dosJob = conn.getJob( dosJobId )
    		self.assertEqual( dosJob.id, dosJobId )
    		self.assertEqual( dosJob.title, "Dos" )
    		self.assertEqual( dosJob.command, "sleep 3" )
    		self.assertEqual( dosJob.state, "WAITING" )
    		self.assertEqual( dosJob.affinity, "dos" )
    		self.assertEqual( dosJob.priority, 127 )

    		basicJobId = conn.newJob( command = "sleep 3", title="Basic", state = "WAITING", priority = 127 )
    		basicJob = conn.getJob( basicJobId )
    		self.assertEqual( basicJob.id, basicJobId )
    		self.assertEqual( basicJob.title, "Basic" )
    		self.assertEqual( basicJob.command, "sleep 3" )
    		self.assertEqual( basicJob.state, "WAITING" )
    		self.assertEqual( basicJob.priority, 127 )

    		workers = conn.getWorkers()

    		new_workers = {}
    		new_workers[workers[0]['name']] = {}
    		new_workers[workers[0]['name']]['affinity'] = "windows\nlinux"

    		new_workers[workers[1]['name']] = {}
    		new_workers[workers[1]['name']]['affinity'] = "windows playmobil\nwin\ndos"

    		updated_workers = conn.editWorkers( new_workers )



    	  	while (True):
    			secondSleepJob = conn.getJob( secondSleepJobId )
    			firstSleepJob = conn.getJob( firstSleepJobId )
    			if ( secondSleepJob.state == "FINISHED" ) & ( firstSleepJob.state == "FINISHED"):

    				self.assertTrue( secondSleepJob.start_time < firstSleepJob.start_time )
    				self.assertEqual( secondSleepJob.worker, workers[0]['name'] )
    				self.assertEqual( firstSleepJob.worker, workers[0]['name'] )

    				return

    			time.sleep (.1)

    		while (True):

    			windowsPlaymobilJob = conn.getJob( windowsPlaymobilJobId )
    			winJob = conn.getJob( winJobId )
    			dosJob = conn.getJob( dosJobId )
    			basicJob = conn.getJob( basicJobId )

    			if ( windowsPlaymobilJob.state == "FINISHED" ) & ( windowsJob.state == "FINISHED" ) & ( dosJob.state == "FINISHED" ) & ( basicJob.state == "FINISHED" ):

    				self.assertTrue( windowsPlaymobilJob.start_time < winJob.start_time )
    				self.assertTrue( winJob.start_time < dosJob.start_time )
    				self.assertTrue( windowsPlaymobilJob.start_time < dosJob.start_time )
    				self.assertTrue( ( dosJob.start_time < basicJob.start_time ) | ( dosJob.worker != basicJob.worker ) )

    				return

    			time.sleep (.1)


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


def main():

    # Launch a server and several workers processes
    launch_server()
    launch_workers()

    # Start the test when environemtn variable is set and server / workers are launched
    launch_test()

    # Iterate over the processes
    for p in processes:
        # Kill the process when test is done
        pass


if __name__ == "__main__":
    main()
