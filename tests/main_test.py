#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os, time, subprocess, unittest
sys.path.append(os.path.abspath("."))
from api import coalition

HOST="localhost"
PORT="19211"
NUM_WORKERS = 4
NUM_JOBS = 10
VERBOSITY = 5

def test_server_python_api():
    tests = [
            "test_newJob",
            "test_getJob",
            "test_getWorkers",
            "test_editWorkers",
            "test_priorities",
            "test_affinities_first",
            "test_setJobDependencies",
            "test_states",
            "test_children_finish_before_parent",
            "test_no_job_error",]
    suite = unittest.TestSuite(map(ServerPythonApiTestCase, tests))
    return unittest.TextTestRunner(verbosity=VERBOSITY).run(suite)

def test_server_xmlrpc():
    tests = ['test_setJobDependencies',]
    suite = unittest.TestSuite(map(ServerXmlrpcTestCase, tests))
    unittest.TextTestRunner(verbosity=VERBOSITY).run(suite)

def launch_server():
    """Launch a coalition server."""
    # The --init parameter prevents database overwriting. The database has to be
    # initially empty.
    cmd = ["python", "server.py"]
    return subprocess.Popen(cmd)


def launch_worker(identifier):
    """Launch coalition worker."""
    cmd = ["python", "worker.py", "-n", identifier, "http://{}:{}".format(HOST,PORT)]
    return subprocess.Popen(cmd)


class ServerPythonApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.server = launch_server()
        time.sleep(5)
        if self.server.poll() is not None:
            print("Server failed to start.")
            exit(1)
        self.workers = [launch_worker("worker-{}".format(i)) for i in range(2)]
        self.conn = coalition.Connection(HOST, PORT)
        affinities = dict()
        for i in range(1, 65):
            affinities[str(i)] = ""
        affinities["1"] = "linux"
        affinities["2"] = "win"
        affinities["3"] = "windows project"
        affinities["4"] = "windows"
        affinities["5"] = "dos"
        self.conn.setAffinities(affinities)
        self.depJobID = self.conn.newJob(command="echo dependencies", title="jobDependencies", state='PAUSED')
        self.parentID = self.conn.newJob(title="parent")
        self.childrenID = [self.conn.newJob(command="echo 'job-{}'".format(i),
            title="job-{}".format(i), parent=self.parentID, state='PAUSED') for i in range(NUM_JOBS)]
        self.firstSleepJobId = self.conn.newJob(command="sleep 2", title="First Job", state="WAITING", affinity="linux", priority=129)
        self.secondSleepJobId = self.conn.newJob(command="sleep 2",
            title="Second Job", state="WAITING", affinity="linux", priority=128)
        self.windowsProjectJobId = self.conn.newJob(command="sleep 1", title="windows project", state="WAITING", affinity="windows project", priority=127)
        self.winJobId = self.conn.newJob(command="sleep 1", title="Win", state="WAITING", affinity="win", priority=127)
        self.dosJobId = self.conn.newJob(command="sleep 1", title="Dos", state="WAITING", affinity="dos", priority=127)
        self.basicJobId = self.conn.newJob(command="sleep 1", title="Basic",
                state="WAITING", priority=300)

    @classmethod
    def tearDownClass(self):
        for worker in self.workers:
            worker.terminate()
        self.server.terminate()

    def test_newJob(self):
        self.assertNotEqual(self.depJobID, None)
        self.assertNotEqual(self.parentID, None)

    def test_getJob(self):
        depJob = self.conn.getJob(self.depJobID)
        firstSleepJob = self.conn.getJob(self.firstSleepJobId)
        secondSleepJob = self.conn.getJob(self.secondSleepJobId)

        self.assertEqual(depJob.id, self.depJobID)
        self.assertEqual(depJob.title, 'jobDependencies')
        self.assertEqual(depJob.command, 'echo dependencies')
        self.assertEqual(depJob.state, "PAUSED")

        self.assertEqual(firstSleepJob.id, self.firstSleepJobId)
        self.assertEqual(firstSleepJob.title, "First Job")
        #self.assertEqual(firstSleepJob.state, "WAITING")
        self.assertEqual(firstSleepJob.affinity, "linux")
        self.assertEqual(firstSleepJob.priority, 129)

        self.assertEqual(secondSleepJob.id, self.secondSleepJobId)
        self.assertEqual(secondSleepJob.title, "Second Job")
        #self.assertEqual(secondSleepJob.state, "WAITING")
        self.assertEqual(secondSleepJob.affinity, "linux")
        self.assertEqual(secondSleepJob.priority, 128)

    def test_getWorkers(self):
        for k in range(1,10):
            workers = self.conn.getWorkers()
            if len(workers) >= 2:
                break
            time.sleep (1)

        self.assertEqual(len(workers), 2)

    def test_editWorkers(self):
        workers = self.conn.getWorkers()
        new_workers = dict()
        new_workers[workers[0]['name']] = dict()
        new_workers[workers[0]['name']]['affinity'] = "windows\nlinux"
        new_workers[workers[1]['name']] = dict()
        new_workers[workers[1]['name']]['affinity'] = "windows project\nwin\ndos"
        self.assertEqual(self.conn.editWorkers(new_workers), '1')

    def test_priorities(self):
        firstSleepJob = self.conn.getJob(self.firstSleepJobId)
        secondSleepJob = self.conn.getJob(self.secondSleepJobId)
        while not (secondSleepJob.state == "FINISHED") & (firstSleepJob.state == "FINISHED"):
            time.sleep(1)
            firstSleepJob = self.conn.getJob(self.firstSleepJobId)
            secondSleepJob = self.conn.getJob(self.secondSleepJobId)
        self.assertTrue(secondSleepJob.start_time > firstSleepJob.start_time)

    def test_affinities_first(self):
        windowsProjectJob = self.conn.getJob( self.windowsProjectJobId )
        winJob = self.conn.getJob( self.winJobId )
        dosJob = self.conn.getJob( self.dosJobId )
        basicJob = self.conn.getJob( self.basicJobId )

        while not ( windowsProjectJob.state == "FINISHED" ) & ( winJob.state == "FINISHED" ) & ( dosJob.state == "FINISHED" ) & ( basicJob.state == "FINISHED" ):
            windowsProjectJob = self.conn.getJob( self.windowsProjectJobId )
            winJob = self.conn.getJob( self.winJobId )
            dosJob = self.conn.getJob( self.dosJobId )
            basicJob = self.conn.getJob( self.basicJobId )

        self.assertTrue( windowsProjectJob.start_time < winJob.start_time )
        self.assertTrue( winJob.start_time < dosJob.start_time )
        self.assertTrue( windowsProjectJob.start_time < dosJob.start_time )
        self.assertTrue( ( dosJob.start_time < basicJob.start_time ) | ( dosJob.worker != basicJob.worker ) )

    def test_setJobDependencies(self):
        self.conn.setJobDependencies (self.depJobID, self.childrenID)
        depsJobs = self.conn.getJobDependencies (self.depJobID)
        depsID = [job.id for job in depsJobs]
        with self.conn:
            depJob = self.conn.getJob(self.depJobID)
            depJob.state = "WAITING"
        self.assertTrue(any(map(lambda v: v in self.childrenID, depsID)))

    def test_states(self):
        with self.conn:
            for job in self.conn.getJobChildren(self.parentID):
                job.state = "WAITING"
        depJob = self.conn.getJob (self.depJobID)
        self.assertNotEqual(depJob.state, "PAUSED")

    def test_children_finish_before_parent(self):
        for i in self.childrenID:
            job = self.conn.getJob (i)
            with self.conn:
                job.state = "WAITING"

        depJob = self.conn.getJob (self.depJobID)
        while depJob.state != "FINISHED":
            depJob = self.conn.getJob (self.depJobID)
            time.sleep(1)

    def test_no_job_error(self):
        parent = self.conn.getJob (self.parentID)
        self.assertEqual (parent.state, "FINISHED")
        self.assertEqual (parent.working, 0)
        self.assertEqual (parent.errors, 0)
        self.assertEqual (parent.run_done, 0)


class ServerXmlrpcTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.server = launch_server()
        self.workers = [launch_worker("worker1"), launch_worker("worker2")]
        self.conn = coalition.Connection(HOST, PORT)

    @classmethod
    def tearDownClass(self):
        for worker in self.workers:
            worker.terminate()
        self.server.terminate()

    def test_setJobDependencies(self):
        """set job2 dependent on job1"""
        job1 = self.conn.newJob(0, "Test-1", "ls /", ".", "", "WAITING", False, 100, 15, "" , "", "", "")['id']
        job2 = self.conn.newJob(0, "Test-2", "ls /", ".", "", "WAITING", False, 100, 15, "" , "", "", "")['id']
        self.conn.setJobDependencies(job2, [job1])
        self.assertEqual(len(self.getJobDependencies(job2)), 1)
        self.assertEqual(self.getJob(job2)['state'], "PENDING")

    def test_pick_job(self):
        pick1 = self.pickJob ("worker1", 1, 1, 1, "127.0.0.1")
        pick2 = self.pickJob ("worker2", 1, 1, 1, "127.0.0.1")
        assertEqual(pick1[0], job1)
        assertEqual(self.getWorker ('worker1') ['state'], "WORKING")
        assertEqual(self.getJob(job1)['state'], "WORKING")
        assertEqual(pick2[0], -1)
        assertEqual(self.getJob(job2)['state'], "PENDING")

    def test_heartbeats(self):
        h1 = self.heartbeat ("worker1", pick1[0], 1, 1, 1, '127.0.0.1')
        h2 = self.heartbeat ("worker2", pick2[0], 1, 1, 1, '127.0.0.1')
        assertIsNotNone (h1)
        assertEqual(self.getWorker('worker1')['state'], "WORKING")
        assertIsNone(h2)
        assertEqual(self.getWorker('worker2')['state'], "WAITING")

    def test_worker1_finish_job(self):
        self.endJob("worker1", pick1[0], 0, "127.0.0.1")
        assertEqual(self.getWorker('worker1')['state'], "WAITING")
        assertEqual(self.getJob(job1)['state'], "FINISHED")
        assertEqual(self.getJob(job2)['state'], "WAITING")

    def test_worker1_pick_job(self):
        pick1 = self.pickJob ("worker1", 1, 1, 1, "127.0.0.1")
        assertEqual(pick1[0], job2)
        assertEqual(self.getWorker('worker1')['state'], "WORKING")
        assertEqual(self.getJob(job2)['state'], "WORKING")

    def	test_worker1_finish_job(self):
        self.endJob ("worker1", pick1[0], 0, "127.0.0.1")
        assertEqual(self.getWorker('worker1')['state'], "WAITING")
        assertEqual(self.getJob(job1) ['state'], "FINISHED")

    def	test_worker2_pick_job(self):
        pick2 = self.pickJob ("worker2", 1, 1, 1, "127.0.0.1")
        assertEqual (pick2[0], -1)
        assertEqual (self.getWorker ('worker2') ['state'], "WAITING")

    def test_worker2_pick_job(self):
        job3 = self.newJob (0, "Test-1", "ls /", ".", "", "PAUSED", False, 100, 15, "" , "", "", "") ['id']
        pick2 = self.pickJob ("worker2", 1, 1, 1, "127.0.0.1")
        assertEqual (pick2[0], -1)
        assertEqual (self.getJob (job3) ['state'], "PAUSED")
        assertEqual (self.getWorker ('worker2') ['state'], "WAITING")

    def	test_start_job3(self):
        self.startJob (job3)
        assertEqual (self.getJob (job3)['state'], "WAITING")

    def	test_worker2_pick_job(self):
        pick2 = self.pickJob ("worker2", 1, 1, 1, "127.0.0.1")
        assertEqual (pick2[0], job3)
        assertEqual (self.getJob (job3) ['state'], "WORKING")
        assertEqual (self.getWorker ('worker2') ['state'], "WORKING")

    def test_worker2_error_job(self):
        self.endJob ("worker2", pick2[0], 1, "127.0.0.1")
        assertEqual (self.getJob (job3) ['state'], "ERROR")
        assertEqual (self.getWorker ('worker2') ['state'], "WAITING")

    def test_worker2_pick_job(sefl):
        pick2 = self.pickJob ("worker2", 1, 1, 1, "127.0.0.1")
        assertEqual (pick2[0], -1)

    def test_reset_job3(self):
        self.resetJob (job3)
        assertEqual (self.getJob (job3)['state'], "WAITING")

    def test_worker2_pick_job(self):
        pick2 = self.pickJob ("worker2", 1, 1, 1, "127.0.0.1")
        assertEqual (pick2[0], job3)

    def	test_worker2_end_job(self):
        self.endJob ("worker2", pick2[0], 0, "127.0.0.1")
        assertEqual (self.getJob (job3) ['state'], "FINISHED")
        assertEqual (self.getWorker ('worker2') ['state'], "WAITING")

    def test_worker1_pick_job(self):
        job4 = self.newJob (0, "Test-1", "ls /", ".", "", "WAITING", False, 100, 10, "" , "", "", "") ['id']
        job5 = self.newJob (0, "Test-2", "ls /", ".", "", "WAITING", False, 100, 12, "" , "", "", "") ['id']
        pick1 = self.pickJob ("worker1", 1, 1, 1, "127.0.0.1")
        assertEqual (pick1[0], job5)

    def test_delete_job4(self):
        self.deleteJob (job4)
        assertIsNone(self.getJob(job4))

    def	test_worker1_heartbeats(self):
        h1 = self.heartbeat ("worker1", pick1[0], 1, 1, 1, '127.0.0.1')
        assertIsNtNone (h1)
        assertEqual(self.getWorker('worker1')['state'], "WORKING")

    def test_delete_job5(self):
        self.deleteJob (job5)
        assertIsNone(self.getJob(job5))

    def test_worker1_heartbeats(self):
        h1 = self.heartbeat ("worker1", pick1[0], 1, 1, 1, '127.0.0.1')
        assertIsNone(h1)
        assertEqual(self.getWorker('worker1')['state'], "WAITING")

    def test_pause_jobs(self):
        job6 = self.newJob (0, "Test-1", "ls /", ".", "", "WAITING", False, 100, 10, "" , "", "", "") ['id']
        self.pauseJob (job6)
        assertEqual (self.getJob (job6) ['state'], "PAUSED")
        assertEqual (self.getJob (job6) ['h_paused'], True)

    def	test_worker1_pick_job(self):
        pick1 = self.pickJob ("worker1", 1, 1, 1, "127.0.0.1")
        assertEqual (pick1[0], -1)

    def	test_start_job6(self):
        self.startJob (job6)
        assertEqual (self.getJob (job6) ['state'], "WAITING")
        assertEqual (self.getJob (job6) ['h_paused'], False)

    def	test_worker1_pick_job(self):
        pick1 = self.pickJob ("worker1", 1, 1, 1, "127.0.0.1")
        assertEqual (pick1[0], job6)
        assertEqual (self.getJob (job6) ['state'], "WORKING")

    def	test_worker1_heartbeats(self):
        h1 = self.heartbeat ("worker1", pick1[0], 1, 1, 1, '127.0.0.1')
        assertIsNotNone (h1)

    def	test_pause_job6(self):
        self.pauseJob (job6)
        assertEqual (self.getJob (job6) ['state'], "PAUSED")
        assertEqual (self.getJob (job6) ['h_paused'], True)

    def	test_worker1_heartbeats(self):
        h1 = self.heartbeat ("worker1", pick1[0], 1, 1, 1, '127.0.0.1')
        assertIsNone(h1)

    def	test_start_job6(self):
        self.startJob (job6)
        assertEqual (self.getJob (job6) ['state'], "WAITING")
        assertEqual (self.getJob (job6) ['h_paused'], False)

    def	test_worker1_pick_job(self):
        self.stopWorker ("worker1")
        pick1 = self.pickJob ("worker1", 1, 1, 1, "127.0.0.1")
        assertEqual (pick1[0], -1)
        assertEqual (self.getWorker ('worker1') ['state'], "WAITING")

    def	test_worker1_heartbeats(self):
        h1 = self.heartbeat ("worker1", pick1[0], 1, 1, 1, '127.0.0.1')
        assertIsNone(h1)

    def	test_worker1_pick_job(self):
        self.startWorker ("worker1")
        pick1 = self.pickJob ("worker1", 1, 1, 1, "127.0.0.1")
        assertEqual (pick1[0], job6)
        assertEqual (self.getJob (job6) ['state'], "WORKING")

    def	test_worker1_heartbeats(self):
        h1 = self.heartbeat ("worker1", pick1[0], 1, 1, 1, '127.0.0.1')
        assertIsNotNone(h1)

    def test_worker1_deleted(self):
        self.deleteWorker ("worker1")
        h1 = self.heartbeat ("worker1", pick1[0], 1, 1, 1, '127.0.0.1')
        assertIsNotNone(h1)

    def	test_worker1_stopped(self):
        self.stopWorker ("worker1")
        h1 = self.heartbeat ("worker1", pick1[0], 1, 1, 1, '127.0.0.1')
        assertIsNone(h1)

    def	test_delete_job6(self):
        self.deleteJob (job6)
        assertIsNone(self.getJob (job6))

    def test_worker1_pick_job(self):
        self.startWorker ("worker1")
        pick1 = self.pickJob ("worker1", 1, 1, 1, "127.0.0.1")
        assertEqual(pick1[0], -1)

    def	test_create_job7(self):
        job7 = self.newJob (0, "Parent-1", "", ".", "", "WAITING", False, 100, 10, "" , "", "", "") ['id']
        pick1 = self.pickJob ("worker1", 1, 1, 1, "127.0.0.1")
        assertEqual(pick1[0], -1)

    def	test_create_job8(self):
        job8 = self.newJob (job7, "Child-1", "ls /", ".", "", "WAITING", False, 100, 10, "" , "", "", "") ['id']
        pick1 = self.pickJob ("worker1", 1, 1, 1, "127.0.0.1")
        assertEqual (pick1[0], job8)

    def	test_worker1_heartbeats(self):
        h1 = self.heartbeat ("worker1", pick1[0], 1, 1, 1, '127.0.0.1')
        assertIsNotNone(h1)

    def test_worker1_finish_job_and_change_job7_priority(self):
        self.endJob ("worker1", pick1[0], 0, "127.0.0.1")
        job8prio = self.getJob (job8) ['h_priority']
        self.editJobs ({ job7: { "priority": 12 } })
        assertLess(job8prio, self.getJob(job8)['h_priority'])

    def test_worker1_pick_job12(self):
        job9 = self.newJob (0, "Parent-2", "", ".", "", "WAITING", False, 100, 10, "" , "", "", "") ['id']
        job10 = self.newJob (0, "Parent-3", "", ".", "", "WAITING", False, 100, 11, "" , "", "", "") ['id']
        job11 = self.newJob (job9, "Child-2", "ls /", ".", "", "WAITING", False, 100, 10, "" , "", "", "") ['id']
        job12 = self.newJob (job10, "Child-3", "ls /", ".", "", "WAITING", False, 100, 8, "" , "", "", "") ['id']
        pick1 = self.pickJob ("worker1", 1, 1, 1, "127.0.0.1")
        assert (pick1[0] == job12)

    def test_worker1_pick_job11(self):
        self.endJob ("worker1", pick1[0], 0, "127.0.0.1")
        pick1 = self.pickJob ("worker1", 1, 1, 1, "127.0.0.1")
        assert (pick1[0] == job11)

    def test_worker1_finish_job(self):
        self.endJob ("worker1", pick1[0], 0, "127.0.0.1")


    def test_intricate_dependencies(self):
        # performs intricate dependencies testing
        # like a group dependent on a paused job
        # and job dependent on this group
        job20 = self.newJob (0, "job20", "sleep 2", ".", "", "PAUSED", False, 0, 100, "" , "", "", "") ['id']
        job21 = self.newJob (0, "job21", "", ".", "", "WAITING", False, 0, 100, "" , "", "", "") ['id']
        self.setJobDependencies (job21, [ job20 ])
        job22 = self.newJob (job21, "job22", "sleep 2", ".", "", "WAITING", False, 0, 100, "" , "", "", "") ['id']
        job23 = self.newJob (0, "job23", "sleep 2", ".", "", "WAITING", False, 0, 150, "" , "", "", "") ['id']
        self.setJobDependencies (job23, [ job21 ])
        job24 = self.newJob (0, "job24", "sleep 2", ".", "", "WAITING", False, 0, 200, "" , "", "", "") ['id']
        self.setJobDependencies (job24, [ job20 ])
        pick1 = self.pickJob ("worker1", 1, 1, 1, "127.0.0.1")
        # can't start any job, all are dependent on job20 which is paused
        assertEqual(pick1[0], -1)
        assertEqual(self.getJob(job20)['state'], 'PAUSED')
        assertEqual(self.getJob(job21)['state'], 'PENDING')
        assertEqual(self.getJob(job22)['state'], 'WAITING')
        assertIsNotNone(self.getJob(job22)['h_paused'])
        assertEqual(self.getJob(job23)['state'], 'PENDING')
        assertEqual(self.getJob(job24)['state'], 'PENDING')

    def test_can_only_pick_jobs20(self):
        self.startJob (job20)
        pick1 = self.pickJob ("worker1", 1, 1, 1, "127.0.0.1")
        assertEqual(pick1[0], job20)

    def test_worker1_finish_job(self):
        self.endJob("worker1", pick1[0], 0, "127.0.0.1")
        assertEqual(self.getJob(job20)['state'], 'FINISHED')
        assertEqual(self.getJob(job21)['state'], 'WAITING')
        assertEqual(self.getJob(job22)['state'], 'WAITING')
        assertNotNone(not self.getJob(job22) ['h_paused'])
        assertEqual(self.getJob(job23)['state'], 'PENDING')
        assertEqual(self.getJob(job24)['state'], 'WAITING')

    def test_worker1_pick_jobs24(self):
        # pick job24 as it is the top priority job
        pick1 = self.pickJob("worker1", 1, 1, 1, "127.0.0.1")
        assertEqual(pick1[0], job24)

    def test_worker1_finish_job(self):
        self.endJob ("worker1", pick1[0], 0, "127.0.0.1")
        assertEqual(self.getJob(job20)['state'], 'FINISHED')
        assertEqual(self.getJob(job21)['state'], 'WAITING')
        assertEqual(self.getJob(job22)['state'], 'WAITING')
        assertIsNone(self.getJob(job22)['h_paused'])
        assertEqual(self.getJob(job23)['state'], 'PENDING')
        assertEqual(self.getJob(job24)['state'], 'FINISHED')

    def test_pick_job22(self):
        # pick job22 as job23 is still pending and job21 can't be picked as a group
        pick1 = self.pickJob ("worker1", 1, 1, 1, "127.0.0.1")
        assertEqual(pick1[0], job22)

    def test_worker1_finish_job(self):
        self.endJob ("worker1", pick1[0], 0, "127.0.0.1")

        assertEqual (self.getJob (job20) ['state'], 'FINISHED')
        assertEqual (self.getJob (job21) ['state'], 'FINISHED')
        assertEqual (self.getJob (job22) ['state'], 'FINISHED')
        assertEqual (self.getJob (job23) ['state'], 'WAITING')
        assertEqual (self.getJob (job24) ['state'], 'FINISHED')

    def test_worker1_pick_job23(self):
        # and eventually pick job23
        pick1 = self.pickJob ("worker1", 1, 1, 1, "127.0.0.1")
        assert (pick1[0] == job23)
    def test_worker1_finish_jobs(self):
        self.endJob ("worker1", pick1[0], 0, "127.0.0.1")

        assertEqual (self.getJob (job20) ['state'], 'FINISHED')
        assertEqual (self.getJob (job21) ['state'], 'FINISHED')
        assertEqual (self.getJob (job22) ['state'], 'FINISHED')
        assertEqual (self.getJob (job23) ['state'], 'FINISHED')
        assertEqual (self.getJob (job24) ['state'], 'FINISHED')


if __name__ == "__main__":
    result = test_server_python_api()
    if result.wasSuccessful():
        exit(0)
    else:
        exit(1)
# vim: tabstop=4 noexpandtab shiftwidth=4 softtabstop=4 textwidth=79

