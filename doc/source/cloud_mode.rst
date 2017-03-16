==========
Cloud mode
==========

In this setup, the coalition server is allowed to start and delete instances so that all the jobs get done with minimum costs.

Configuration
=============

Amazon Cloud
------------

First, an initial setup is required on the cloud provider side. We provide here a minimal working setup. It can of course be enriched by your specificid needs and policy.

1. **Amazon account**

   To be allowed to manage cloud instances (ie. starting and terminating), the coalition server needs authentication.

   - from you amazon cloud account, visit the section *Manage security credentials*
   - get an access Keys (ID and Secret key) as text file

  You might prefer to create a dedicated user instead of your global user account.

2. **Virtual Private Cloud (VPC)**

   For the workers and the server to communicate securely, we use a common VPC:

   - create a new VPC

3. **Security Groups**

   The coalition's server and workers communication port defaults to 19211. The server should be accessible by the user (to interact with the API and/or web frontend) and from workers. The server can be hosted in the office or in the cloud, according to your network policy. Here, the server is instanciated in the cloud, belongs to the security group *sg-coalition* and the workers belong to the security group *sg-worker*. The workers should be accessible from the server only. So, the security groups and inbound rules are like those:

   - create a security group *sg-coalition*

     - Inbound Rules: TCP 19211 sg-worker
     - Inbound Rules: TCP 19211 office-public-IP

   - create security group *sg- worker*

     - Inbound Rules: TCP 19211 sg-coalition

4. **Bucket**

   As workers are instanciated on demand, they need to fetch startup configuration files somewhere. Besides, as the workers might produce some data files (for example in a renderfarm usecase), those files must be saved in a filer. We create a bucket for that:

   - create a bucket
   - prepare the startup configuration files in the bucket

     - create a directory **srv**
     - copy the coalition source code into the **srv** directory:

       - download `coalition source code <https://github.com/MercenariesEngineering/coalition/archive/master.zip>`_ as a zip file (or use the git source you got while installing the server)
       - unzip the file
       - recompress and pack it as a tar compressed file
       - copy **coalition.tar.gz** to the bucket: **srv/coalition.tar.gz**

     - in this setup, we build a `guerilla render <http://www.guerillarender.com/>`_ cloud renderfarm, so the worker needs the guerilla render binary:

       - copy **guerilla_render_2.0.0a13_linux64.tar.gz** to **srv/guerilla_render_2.0.0a13_linux64.tar.gz**

Coalition server
----------------

Now that the cloud provider has been set up, the coalition server has to be configured accordingly.

 - install a coalition server as explained in *Installation* documentation page
 - edit the file **coalition.ini** in the **[Server]** section and set::
   
     servermode = aws

 - copy the file **_cloud_aws.ini** to **cloud_aws.ini**
 - edit the file **cloud_aws.ini**

The configuration file **cloud_aws.ini** is self-explanatory. Set the options with your own amazon parameters:

.. include:: ../../_cloud_aws.ini
   :literal:

Running coalition
=================
The coalition server is now ready to manage workers in the amazon cloud.

  - start the server
  - visit the web interface **http://<server_adress>:19211**
  - add some jobs

Workers will automagically be instanciated, getting job to do, working and terminated according to the configuration until there are no more jobs in waiting state on the server.

Additional documentation for programmers
========================================

python cloud module
-------------------

cloud.common
''''''''''''

.. automodule:: cloud.common
    :members:

cloud.aws
'''''''''

.. automodule:: cloud.aws
    :members:

Amazon specific templates
-------------------------

cloud/aws_worker_cloud_init.template
''''''''''''''''''''''''''''''''''''

.. include:: ../../cloud/aws_worker_cloud_init.template
   :literal:

cloud/aws_worker_spot_launchspecification.json.template
'''''''''''''''''''''''''''''''''''''''''''''''''''''''

.. include:: ../../cloud/aws_worker_spot_launchspecification.json.template
   :literal:

..
  Google cloud specific templates
  -------------------------------
  
  cloud/gcloud_worker_cloud_init.template
  '''''''''''''''''''''''''''''''''''''''
  
  .. include:: ../../cloud/glcoud_worker_cloud_init.template
  
  
  Qarnot specific templates
  -------------------------
  
  cloud/qarnot_worker_cloud_init.template
  '''''''''''''''''''''''''''''''''''''''
  
  .. include:: ../../cloud/qarnot_worker_cloud_init.template
  
  
  IBM cloud specific templates
  ----------------------------
  cloud/ibm_worker_cloud_init.template
  ''''''''''''''''''''''''''''''''''''
  
  .. include:: ../../cloud/ibm_worker_cloud_init.template
  
