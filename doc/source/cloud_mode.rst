==========
Cloud mode
==========

In this setup, the coalition server is allowed to start and delete instances so that all the jobs get done with minimum costs. Here, we install the coalition server on a dedicated cloud instance (instead of locahost). This way we simplify the network setup as we don't need a VPN or VLAN. 

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

4. **Setup Coalition server as a cloud instance**

Now that the cloud provider has been set up, the coalition server has to be configured accordingly.

 - install a coalition server on a cloud instance as explained in *Installation* documentation page
 - edit the file **coalition.ini** in the **[Server]** section and set::
   
     servermode = aws

 - copy the file **_cloud_aws.ini** to **cloud_aws.ini**
 - edit the file **cloud_aws.ini**

The configuration file **cloud_aws.ini** is self-explanatory. Set the options with your own amazon parameters:

.. include:: ../../_cloud_aws.ini
   :literal:

5. **Bucket**

   As workers are instanciated on demand, they need to fetch startup configuration files somewhere. Besides, as the workers might produce some data files (for example in a renderfarm usecase), those files must be saved in a filer. We create a bucket for that:

   - create a bucket
   - prepare the startup configuration files in the bucket

     - create a directory **srv**
     - copy the coalition source code into the **srv** directory:

       - download `coalition source code <https://github.com/MercenariesEngineering/coalition/archive/master.zip>`_ as a zip file (or use the git source you got while installing the server)
       - unzip the file
       - copy **_coalition.ini** into **coalition.ini** and edit the **[worker]** section
       - recompress and pack it as a tar compressed file
       - copy **coalition.tar.gz** to the bucket: **srv/coalition.tar.gz**

     - in this setup, we build a `guerilla render <http://www.guerillarender.com/>`_ cloud renderfarm, so the worker needs the guerilla render binary:

       - copy **guerilla_render_2.0.0a13_linux64.tar.gz** to **srv/guerilla_render_2.0.0a13_linux64.tar.gz**

Google cloud
------------

1. **Google cloud account**

  - login on `google cloud console <https://console.cloud.google.com>`
  - create a new project eg. **guerilla-cloud**
  - get the json key file for the service account (menu IAM & Admin > Service accounts > Options > Create keys)

2. **Networking**

  We want to be able to visit the coalition server web frontend, so we need to allow remote connection from our office.

  - add a firewall rule allowing office IP on port tcp:19211

3. **Setup Coalition server as a google cloud instance**

Now that the cloud provider has been set up, the coalition server has to be configured accordingly.

 - install a coalition server in a compute cloud instance as explained in *Installation* documentation page

   - as the server will create and delete cloud instances, set the instance **access scope** to **Allow full acees to all Cloud APIs**
   - use a dedicated IP instead of an ephemeral one for permanent reachability
   - ssh access for copying coalition files can be done via google credentials::

   ssh -i ~/.ssh/google_compute_engine <coalition_server_ip>

 - edit the file **coalition.ini** in the **[Server]** section and set::
   
     servermode = gcloud

 - copy the file **_cloud_gcloud.ini** to **cloud_gcloud.ini**
 - edit the file **cloud_gcloud.ini**

The configuration file **cloud_gcloud.ini** is self-explanatory. Set the options with your own google parameters:

.. include:: ../../_cloud_gcloud.ini
   :literal:

4. **Storage**

 As workers are instanciated on demand, they need to fetch startup configuration files somewhere. Besides, as the workers might produce some data files (for example in a renderfarm usecase), those files must be saved in a filer. We create a bucket for that:

   - create a bucket
   - prepare the startup configuration files in the bucket

     - create a directory **srv**
     - copy the coalition source code into the **srv** directory:

       - download `coalition source code <https://github.com/MercenariesEngineering/coalition/archive/master.zip>`_ as a zip file (or use the git source you got while installing the server)
       - unzip the file
       - copy the service user json key file into the coalition directory
       - copy **_coalition.ini** into **coalition.ini** and edit the **[worker]** section
       - recompress and pack it as a tar compressed file
       - copy **coalition.tar.gz** to the bucket: **srv/coalition.tar.gz**

     - in this setup, we build a `guerilla render <http://www.guerillarender.com/>`_ cloud renderfarm, so the worker needs the guerilla render binary:

       - copy **guerilla_render_2.0.0a13_linux64.tar.gz** to **srv/guerilla_render_2.0.0a13_linux64.tar.gz**

Running coalition
=================
The coalition server is now ready to manage workers in the cloud:

  - start the server
  - visit the web interface **http://<server_adress>:19211**
  - add affinities
  - add some jobs

Workers will automagically be instanciated, getting jobs, working and terminated according to the configuration until there are no more jobs in waiting state on the server.

Changing coalition server or worker configuration while running
---------------------------------------------------------------
On the server instance, edit the concerned configuration files **coalition.py** and **cloud_<cloud_provider>.py** and restart the server.

As the configuration for workers is set up in the **bucket**, edit the configuration file **coalition.py** and re-upload the **coalition.tar.gz** to the bucket. Newly started instances will immediately use the new configuration. You might want to manually terminate previous instances. The coalition server does not need restarting in this case since the file names in the bucket are unchanged.

Monitoring the cloud deployment
===============================
The coalition server limits the number of simultaneous instances to the configuration parameter **workerinstancemax** in **coalition.ini**. But if there is a configuration problem (for instance in the workers starting scripts located in the bucket), coalition server might not be reached by the workers. In this case, coalition server will keep starting instances. So, as long as the configuration is not confirmed, you are advised to check in your cloud provider console the the effective number of starting instances. Some limits can also be setup directly in the cloud provider preventing any excessive cloud usage.

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
  
