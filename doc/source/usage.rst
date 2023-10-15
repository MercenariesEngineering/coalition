Jobs
====

A job is a simple command to run on one of the workers. Each job has an ID chosen by the server.

A job can be submitted to the server using control.py or a HTTP request.
Job attributes

A job may have different attributes. For example, the job attribute cmd is the command to execute.

The different job attributes used to initialise a job are:

 - **cmd**: the command to run
 - **title**: the title to display in the user interface
 - **dir**: the job's working directory
 - **env**: an environment for the command
 - **parent**: the parent job ID
 - **priority**: the job's priority
 - **dependencies**: the job's dependencies on other jobs
 - **timeout**: the job's timeout in seconds
 - **retry**: how many time to retry this job
 - **affinity**: the job affinities to match
 - **url**: the url to open with the Open link
 - **user**: the user name/email of the owner of this job
 - **globalprogress**: the job progression pattern
 - **localprogress**: the second job progression pattern

Job execution
-------------

A new job is in the **WAITING** state.

When a worker run a job, it set the current working directory to dir and run the command cmd. The job is then in the **WORKING** state. If the command returns with the exit code 0, the job is put in the state **FINISHED**. If not, the job is put in the state **ERROR**.

If the job is in the **ERROR** state, the server will retry to run this job up to retry times.

If the job duration exceeds timeout, the server will kill this job and set it in the **ERROR** state.

Job display
-----------

The title attribute is displayed in the user interface.

The url attribute is the url to open with the Open link in the user interface.

By default, the web browser blocks the URLs on local files.

On Firefox, `it is possible to override this behavior <http://kb.mozillazine.org/Links_to_local_pages_don%27t_work>`.

Job environment
---------------

An environment can be provided with a job using the **env** attribute. An environment is a string containing all the variables and their values. The separator is the string **"\n"** (a '\' character followed be a 'n' character, not an end of line character).

Here is a string you can use with the **env** attribute::

  "USER=mylogin\nPATH=mypath"

Job hierarchy
-------------

The hierarchy is useful to organize and schedule the different jobs.

A job can be the parent of some children jobs. In this case, the parent job won't run any command. Even if the attribute **cmd** has been provided.

The parent attribute can be specified to create a job into a previously created parent job.

The parent attribute can be the parent job ID (an integer), a job title (a string) or a path of job titles. Exemples::

    parent=12345 : add the new job to the job #12345
    parent="departments" : add the new job to the job named "departments"
    parent="departments|render" : add the new job to the job named "render" inside the job named "departments"

Job dependencies
----------------

The dependencies attributes is a job ID list of the different jobs to finish before to run this job.

A list can be provided like this : "1,3,5".

Job affinities
--------------

Affinities are used to associate some jobs to a subset of workers.

The affinity attribute is a list of strings, separated by comas.

If a job has an affinity attribute, only the workers with the affinities matching all the job's affinities will be able to run this job.

For example, let's say a job has the following affinity : "LINUX,24GB". Here is a summary of which worker affinities configuration match the job's one::

    | Job affinites | Worker affinities | Match | |:------------------|:----------------------|:----------| | "LINUX,24GB" | "LINUX" | NO | | "LINUX,24GB" | "24GB" | NO | | "LINUX,24GB" | "LINUX,24GB" | YES | | "LINUX,24GB" | "LINUX,24GB,GL" | YES |

Job owner
---------

The user attributes is the user name of the owner of the job. If the emails are activated, the emails regarding this job will be sent at user.

If LDAP is configured, the job will be executed with the user rights.

Job log
-------

The job's log is the output of the command's stdout and stderr streams. The log is sent by the worker to the server.

The server stores the log in the logs/ directory, in a file named ID.log with ID the ID of the job.

Job progression
---------------

The globalprogress attribute is a pattern that is used to extract the job progression out of the job's logs. Here are some examples of logs and patterns::

    | Log | Pattern | Progression | |:--------|:------------|:----------------| | 25 | %percent | 25% | | (50) | (%percent) | 50% | | 0.75 | %one | 75% | | P:1 | P:%one | 100% |

The localprogress attribute can be used with globalprogress to specify a second level of the job progression.

Server
======

The coalition server collects the jobs and distributes them to the differents workers.

Run the server

Add a job
---------

It is possible to add a job to the server using control.py or a HTTP request.

If the job is added, the new job ID is returned.
Using control.py

You can use control.py to add jobs to the server::

    python control.py --cmd="echo toto" --priority=1000 --affinity="linux" --retry=10 http://127.0.0.1:19211 add

Using a HTTP request
--------------------

To add a job using the HTTP interface, simply GET or POST the url http://host:port/xmlrpc/addjob with any job attributes.

Example::

    http://127.0.0.1:19211/xmlrpc/addjob?title=job&cmd=echo toto&priority=1000&affinity=linux&retry=10
