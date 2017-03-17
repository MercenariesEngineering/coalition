.. |badge-doc| image:: https://readthedocs.org/projects/coalition/badge/?version=latest
   :target: http://coalition.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

.. |badge-size| image:: https://reposs.herokuapp.com/?path=https://github.com/MercenariesEngineering/coalition

.. |badge-version| image:: https://badge.fury.io/gh/AlphonseAllais%2Fcoalition.svg
   :target: https://badge.fury.io/gh/AlphonseAllais%2Fcoalition

.. |badge-coverage| image:: https://coveralls.io/repos/github/AlphonseAllais/coalition/badge.svg?branch=development
   :target: https://coveralls.io/github/AlphonseAllais/coalition?branch=development

.. |badge-tests| image:: https://travis-ci.org/AlphonseAllais/coalition.svg?branch=development

|badge-doc| |badge-size| |badge-version| |bagde-coverage| |badge-tests|

`Full online documentation is avaialble on ReadTheDocs <http://coalition.readthedocs.io/en/latest/>`_.

Coalition
=========

**Coalition** is a lightweight open source **job manager** client-server application whose role is to control **job execution in a set of computers**. A computer is acting as a **server** centralizing the list of jobs to be done. A set of physical (or virtual, eg. in the cloud) computers acting as **workers** shall be deployed, raising the global grid system ressources.

The server waits for incoming workers connections. Workers ask the server for a job to do. When the server is asked by a worker for a job, he decides which job to attribute according to simple **affinity rules**. The worker is now aware of which job it has to do. The worker executes the job. When the job is done, the worker informs the server of the job's execution status and ask for a new job.

*Coalition* should not be used on the public Internet but on **private LANs**, **cloud VLANs** or **VPN** for security reasons.

*Coalition* has been successfully used in production notably for **renderfarms**.

*Coalition* provides:

 - **Broadcast discovery** for workers to find the server whithout configuration;
 - **RESTfull python API** based on `Twisted matrix <https://twistedmatrix.com>`_ for program to program communication;
 - **Cloud ready** configuration to manage starting/termination of workers in the cloud;
 - **Web interface** for humans to control jobs, workers, affinities and view status and logs;
 - **Database** interface for sqlite and mysql;
 - **Logging** system;
 - **Email notification** system;
 - **Access Control List** when connected to a **LDAP** server;
 - **Unittests** of critical code parts;
 - **Source code** and **documentation** on `the development platform <https://github.com/MercenariesEngineering/coalition>`_.


The current stable version are 3.8 and 3.10.

The development version is |current-version|.

.. |current-version| include:: version

