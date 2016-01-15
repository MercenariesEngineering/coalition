import subprocess, time, os, unittest, httplib, json, coalition, sys

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
			childrenID.append (conn.newJob (command="echo job%d" % i, title="job%d" % i, parent=parentID, state='PAUSED'))

		depJob = conn.getJob (depJobID)
		self.assertEqual(depJob.ID, depJobID)
		self.assertEqual(depJob.Title, 'jobDependencies')
		self.assertEqual(depJob.Command, 'echo dependencies')
		self.assertEqual(depJob.State, "PAUSED")

		# Set the dependencies
		conn.setJobDependencies (depJob.ID, childrenID)
		depsJobs = conn.getJobDependencies (depJob.ID)
		depsID = [job.ID for job in depsJobs]
		# Check childrenID and depsID are equal
		self.assertTrue(any(map(lambda v: v in childrenID, depsID)))

		# Start all the jobs
		with conn:
			depJob.State = 'WAITING'
			jobs = conn.getJobChildren (parentID)
			for job in jobs:
				job.State = 'WAITING'

		depJob = conn.getJob (depJobID)
		self.assertNotEqual(depJob.State, "PAUSED")

		jobs = conn.getJobChildren (parentID)
		for k,job in enumerate(jobs):
			self.assertEqual(job.ID, childrenID[k])
			self.assertEqual(job.Title, 'job%d'%k)
			self.assertEqual(job.Command, 'echo job%d'%k)
			self.assertNotEqual(job.State, 'PAUSED')

		print "Waiting job end.."
		sys.stdout.flush ()
	  	while (True):
			depJob = conn.getJob (depJobID)
			if depJob.State == "FINISHED":
				for id in childrenID:
					job = conn.getJob (id)
					self.assertEqual(job.State, "FINISHED")
				return
			time.sleep (.1)

	if __name__ == '__main__':
		unittest.main(verbosity=2)

finally:
	pass
