REST API
========

The coalition server provides a REST API using json data.

Jobs
****

.. http:get:: /api/jobs

   Returns the root jobs (with parent=0).

   **Example request**:

   .. sourcecode:: http

	  GET /api/jobs HTTP/1.1
	  Host: localhost

   **Example response**:

   .. sourcecode:: http

	  HTTP/1.1 200 OK
	  Content-Type: application/json

	  [
		  {
			"id": 123,
			"parent": 0,
			"title": "Job 123",
			"command": "echo test",
			"dir": ".",
			"environment": "",
			"state": "WAITING",
			"worker": "worker-1",
			"start_time": 123456,
			"duration": 12,
			"ping_time": 123456,
			"run_done": 1,
			"retry": 10,
			"timeout": 10000,
			"priority": 1000,
			"affinity": "LINUX",
			"user": "render",
			"finished": 0,
			"errors": 0,
			"working": 0,
			"total": 10,
			"total_finished": 0,
			"total_errors": 0,
			"total_working": 0,
			"url": "http://localhost/image.png",
			"progress": 0.5,
			"progress_pattern": "#%percent"
		  },
		  {
			"id": 124,
			"parent": 0,
			"title": "Job 124",
			"command": "echo test",
			"dir": ".",
			"environment": "",
			"state": "WAITING",
			"worker": "worker-1",
			"start_time": 123456,
			"duration": 12,
			"ping_time": 123456,
			"run_done": 1,
			"retry": 10,
			"timeout": 10000,
			"priority": 1000,
			"affinity": "LINUX",
			"user": "render",
			"finished": 0,
			"errors": 0,
			"working": 0,
			"total": 10,
			"total_finished": 0,
			"total_errors": 0,
			"total_working": 0,
			"url": "http://localhost/image.png",
			"progress": 0.5,
			"progress_pattern": "#%percent"
		  }
	  ]

   :statuscode 200: no error
   :statuscode 500: error

.. http:get:: /api/jobs/(int:id)

   Returns the job (`id`) object.

   **Example request**:

   .. sourcecode:: http

	  GET /api/jobs/123 HTTP/1.1
	  Host: localhost

   **Example response**:

   .. sourcecode:: http

	  HTTP/1.1 200 OK
	  Content-Type: application/json

	  {
		"id": 123,
		"parent": 0,
		"title": "Job 123",
		"command": "echo test",
		"dir": ".",
		"environment": "",
		"state": "WAITING",
		"worker": "worker-1",
		"start_time": 123456,
		"duration": 12,
		"ping_time": 123456,
		"run_done": 1,
		"retry": 10,
		"timeout": 10000,
		"priority": 1000,
		"affinity": "LINUX",
		"user": "render",
		"finished": 0,
		"errors": 0,
		"working": 0,
		"total": 10,
		"total_finished": 0,
		"total_errors": 0,
		"total_working": 0,
		"url": "http://localhost/image.png",
		"progress": 0.5,
		"progress_pattern": "#%percent"
	  }

   :statuscode 200: no error
   :statuscode 500: error


.. http:put:: /api/jobs

   Create a job. Returns the new job id.

   **Example request**:

   .. sourcecode:: http

	  PUT /api/jobs HTTP/1.1
	  Host: localhost

	  { 
		"parent": 0,
		"title": "Job 1",
		"command": "echo test",
		"dir": ".",
		"environment": "",
		"state": "WAITING",
		"retry": 10,
		"timeout": 10000,
		"priority": 1000,
		"affinity": "LINUX",
		"user": "render",
		"url": "http://localhost/image.png",
		"progress_pattern": "#%percent"
	  }

   **Example response**:

   .. sourcecode:: http

	  HTTP/1.1 200 OK
	  Content-Type: application/json

	  123

   :statuscode 200: no error
   :statuscode 500: error


.. http:post:: /api/jobs

   Modify the jobs properties.

   **Example request**:

   .. sourcecode:: http

	  POST /api/jobs HTTP/1.1
	  Host: localhost

	  { 
		123:
		{
			"title": "Job renamed 123",
			"command": "echo renamed",
		},
		124:
		{
			"title": "Job renamed 124",
			"command": "echo renamed",
		}
	  }

   **Example response**:

   .. sourcecode:: http

	  HTTP/1.1 200 OK
	  Content-Type: application/json

	  1

   :statuscode 200: no error
   :statuscode 500: error


.. http:get:: /api/jobs/(int:id)/children

   Returns the job (`id`) children objects.

   **Example request**:

   .. sourcecode:: http

	  GET /api/jobs/123/children HTTP/1.1
	  Host: localhost

   **Example response**:

   .. sourcecode:: http

	  HTTP/1.1 200 OK
	  Content-Type: application/json

	  [
		{
			"id": 124,
			"parent": 123,
			"title": "Job 124",
			"command": "echo test",
			"dir": ".",
			"environment": "",
			"state": "WAITING",
			"worker": "worker-1",
			"start_time": 123456,
			"duration": 12,
			"ping_time": 123456,
			"run_done": 1,
			"retry": 10,
			"timeout": 10000,
			"priority": 1000,
			"affinity": "LINUX",
			"user": "render",
			"finished": 0,
			"errors": 0,
			"working": 0,
			"total": 10,
			"total_finished": 0,
			"total_errors": 0,
			"total_working": 0,
			"url": "http://localhost/image.png",
			"progress": 0.5,
			"progress_pattern": "#%percent"
		},
		{
			"id": 125,
			"parent": 123,
			"title": "Job 125",
			"command": "echo test",
			"dir": ".",
			"environment": "",
			"state": "WAITING",
			"worker": "worker-1",
			"start_time": 123456,
			"duration": 12,
			"ping_time": 123456,
			"run_done": 1,
			"retry": 10,
			"timeout": 10000,
			"priority": 1000,
			"affinity": "LINUX",
			"user": "render",
			"finished": 0,
			"errors": 0,
			"working": 0,
			"total": 10,
			"total_finished": 0,
			"total_errors": 0,
			"total_working": 0,
			"url": "http://localhost/image.png",
			"progress": 0.5,
			"progress_pattern": "#%percent"
		},
	  ]

.. http:get:: /api/jobs/(int:id)/dependencies

   Returns the job objects on which the job (`id`) depends.

   **Example request**:

   .. sourcecode:: http

	  GET /api/jobs/123/dependencies HTTP/1.1
	  Host: localhost

   **Example response**:

   .. sourcecode:: http

	  HTTP/1.1 200 OK
	  Content-Type: application/json

	  [
		{
			"id": 124,
			"parent": 0,
			"title": "Job 124",
			"command": "echo test",
			"dir": ".",
			"environment": "",
			"state": "WAITING",
			"worker": "worker-1",
			"start_time": 123456,
			"duration": 12,
			"ping_time": 123456,
			"run_done": 1,
			"retry": 10,
			"timeout": 10000,
			"priority": 1000,
			"affinity": "LINUX",
			"user": "render",
			"finished": 0,
			"errors": 0,
			"working": 0,
			"total": 10,
			"total_finished": 0,
			"total_errors": 0,
			"total_working": 0,
			"url": "http://localhost/image.png",
			"progress": 0.5,
			"progress_pattern": "#%percent"
		},
		{
			"id": 125,
			"parent": 0,
			"title": "Job 125",
			"command": "echo test",
			"dir": ".",
			"environment": "",
			"state": "WAITING",
			"worker": "worker-1",
			"start_time": 123456,
			"duration": 12,
			"ping_time": 123456,
			"run_done": 1,
			"retry": 10,
			"timeout": 10000,
			"priority": 1000,
			"affinity": "LINUX",
			"user": "render",
			"finished": 0,
			"errors": 0,
			"working": 0,
			"total": 10,
			"total_finished": 0,
			"total_errors": 0,
			"total_working": 0,
			"url": "http://localhost/image.png",
			"progress": 0.5,
			"progress_pattern": "#%percent"
		},
	  ]

.. http:post:: /api/jobs/(int:id)/dependencies

   Set the job (`id`) dependencies.

   **Example request**:

   .. sourcecode:: http

	  POST /api/jobs/123/dependencies HTTP/1.1
	  Host: localhost

	  [124,125]

   **Example response**:

   .. sourcecode:: http

	  HTTP/1.1 200 OK
	  Content-Type: application/json

	  1

.. http:get:: /api/jobs/(int:id)/log

   Returns the job (`id`) log file.

   **Example request**:

   .. sourcecode:: http

	  GET /api/jobs/123/log HTTP/1.1
	  Host: localhost

   **Example response**:

   .. sourcecode:: http

	  HTTP/1.1 200 OK
	  Content-Type: application/json

	  "Job 123 done"

   :statuscode 200: no error
   :statuscode 500: error


.. http:delete:: /api/jobs

   Delete the jobs.

   **Example request**:

   .. sourcecode:: http

	  DELETE /api/jobs HTTP/1.1
	  Host: localhost

	  [123,124,125]

   **Example response**:

   .. sourcecode:: http

	  HTTP/1.1 200 OK
	  Content-Type: application/json

	  1


.. http:post:: /api/resetjobs

   Reset the jobs. The job status is set to 'WAITING', all the job counters are set to 0.

   **Example request**:

   .. sourcecode:: http

	  POST /api/resetjobs HTTP/1.1
	  Host: localhost

	  [123,124,125]

   **Example response**:

   .. sourcecode:: http

	  HTTP/1.1 200 OK
	  Content-Type: application/json

	  1


.. http:post:: /api/startjobs

   Start the jobs. The job status is set to 'WAITING'.

   **Example request**:

   .. sourcecode:: http

	  POST /api/startjobs HTTP/1.1
	  Host: localhost

	  [123,124,125]

   **Example response**:

   .. sourcecode:: http

	  HTTP/1.1 200 OK
	  Content-Type: application/json

	  1


.. http:post:: /api/pausejobs

   Pause the jobs. The job status is set to 'PAUSED'.

   **Example request**:

   .. sourcecode:: http

	  POST /api/pausejobs HTTP/1.1
	  Host: localhost

	  [123,124,125]

   **Example response**:

   .. sourcecode:: http

	  HTTP/1.1 200 OK
	  Content-Type: application/json

	  1


Workers
*******

.. http:get:: /api/workers

   Returns the workers.

   **Example request**:

   .. sourcecode:: http

	  GET /api/workers HTTP/1.1
	  Host: localhost

   **Example response**:

   .. sourcecode:: http

	  HTTP/1.1 200 OK
	  Content-Type: application/json

	  {
		"name": "worker-1",
		"ip": "127.0.0.1",
		"affinity": "LINUX,WINDOWS",
		"state": "WAITING",
		"ping_time": 123456,
		"finished": 123,
		"error": 21,
		"last_job": 1234,
		"current_event": 1234,
		"cpu": "[0,0,0,0]",
		"free_memory": 123456,
		"total_memory": 1000000,
		"active": 1
	  }

   :statuscode 200: no error
   :statuscode 500: error


.. http:post:: /api/workers

   Modify the workers properties.

   **Example request**:

   .. sourcecode:: http

	  POST /api/workers HTTP/1.1
	  Host: localhost

	  { 
		"worker-1":
		{
			"affinity": "LINUX",
			"active": 0,
		},
		"worker-2":
		{
			"affinity": "LINUX",
			"active": 0,
		}
	  }

   **Example response**:

   .. sourcecode:: http

	  HTTP/1.1 200 OK
	  Content-Type: application/json

	  1

   :statuscode 200: no error
   :statuscode 500: error


.. http:delete:: /api/workers

   Delete the workers.

   **Example request**:

   .. sourcecode:: http

	  DELETE /api/workers HTTP/1.1
	  Host: localhost

	  ["worker-1","worker-2"]

   **Example response**:

   .. sourcecode:: http

	  HTTP/1.1 200 OK
	  Content-Type: application/json

	  1


.. http:post:: /api/stopworkers

   Stop the workers.

   **Example request**:

   .. sourcecode:: http

	  POST /api/stopworkers HTTP/1.1
	  Host: localhost

	  ["worker-1","worker-2"]

   **Example response**:

   .. sourcecode:: http

	  HTTP/1.1 200 OK
	  Content-Type: application/json

	  1


.. http:post:: /api/startworkers

   Start the workers.

   **Example request**:

   .. sourcecode:: http

	  POST /api/startworkers HTTP/1.1
	  Host: localhost

	  ["worker-1","worker-2"]

   **Example response**:

   .. sourcecode:: http

	  HTTP/1.1 200 OK
	  Content-Type: application/json

	  1


Events
******

.. http:get:: /api/events

   Returns some events.

   :param job: returns the events for this job.
   :param worker: returns the events for this worker.
   :param howlong: returns all the events in the last `howlong` seconds.

   **Example request**:

   .. sourcecode:: http

	  GET /api/events?job=123&worker=worker-1&howlong=60 HTTP/1.1
	  Host: localhost

   **Example response**:

   .. sourcecode:: http

	  HTTP/1.1 200 OK
	  Content-Type: application/json

	  {
		"id": 123,
		"worker": "worker-1",
		"job_id": 123,
		"job_title": "Job 123",
		"state": "ERROR",
		"start": 123456,
		"duration": 10
	  }

   :statuscode 200: no error
   :statuscode 500: error


