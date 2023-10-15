============
Installation
============

Installing the server
=====================
.. _installing a server:

The *Coalition server* can be installed on a localhost or on a remote host. Please remember that communication between server and workers is not encrypted, so if the server is installed on localhost and workers on remote machines, using a VPN or a VLAN is a good idea.

*Coalition* works with python2.7.

Debian like, Ubuntu, etc. via system packages
---------------------------------------------

Logged as a priviledged user, in a shell prompt, run::

  apt-get install -y \
      python2.7 \
      python-httplib2 \
      python-configparser \
      python-twisted \
      python-mysqldb \
      python-ldap \
      python-sphinx \
      python-sphinxcontrib-httpdomain
  
  cd /usr/local/bin
  git clone https://github.com/MercenariesEngineering/coalition.git
  cd coalition
  cp _coalition.ini coalition.ini

Edit the section *[server]* in the file *coalition.ini* according to your needs.

You may want to fine tune the installation using:

 - a dedicated system user and group to isolate the process and file ownership;
 - a `systemd service definition file <https://wiki.archlinux.org/index.php/Systemd>`_;
 - any system service monitoring daemon.

Via pip, the python package manager
-----------------------------------

Using a `python virtual environment <https://virtualenv.pypa.io/en/stable/>`_ is advised in this case, although not mandatory.

Logged as a priviledged user, in a shell prompt, run::

  cd /usr/local/bin
  git clone https://github.com/MercenariesEngineering/coalition.git
  cd coalition
  pip install -r requirements.txt
  cp _coalition.ini coalition.ini

Edit the section *[server]* in the file *coalition.ini* according to your needs.

You may want to fine tune the installation using:

 - a dedicated system user and group to isolate the process and file ownership;
 - a `systemd service definition file <https://wiki.archlinux.org/index.php/Systemd>`_;
 - any system service monitoring daemon.

Windows
-------

You need to manually install python-ldap, and pywin32 (which provides win32pdh). The easiest way to install python-ldap is from `Christoph Gohlke <https://www.lfd.uci.edu/~gohlke/pythonlibs/>`_'s prebuilt binaries. 

Download **python_ldap‑3.2.0‑cp27‑cp27m‑win_amd64.whl** from https://www.lfd.uci.edu/~gohlke/pythonlibs/
::
  cd <download_folder>
  pip install python_ldap-3.2.0-cp27-cp27m-win_amd64.whl
  pip install pywin32

Then install coalition's dependencies with pip
::
  git clone https://github.com/MercenariesEngineering/coalition.git
  cd coalition
  pip install -r requirements.txt
  cp _coalition.ini coalition.ini

Edit the section [server] in the file coalition.ini according to your needs.

coalition.ini configuration file
--------------------------------
This configuration file contains two sections: **[server]** that will be used in server mode, and **[worker]** that will be used while running in worker mode.

.. include:: ../../_coalition.ini
   :literal:

Cloud mode
----------

A coalition server must be installed and the cloud provider needs configuration. See *cloud mode documentation page* for details.

Database
--------

A database must be setup for the coalition server. To initialize it the firest time, run::

  python server.py --verbose --init

The database can be reset on demand. All data are lost::

  python server.py --verbose --reset

See also the next section about migrations.

Update coalition to a new release
---------------------------------

If you update the coalition source code with a more recent coalition release, the new coalition features may need a database schema update. If it's the case, you will be informed by a message while trying to run the server::

  python server.py --verbose --init
  # ...
  # The database requires migration

In this case, you should use the *--migrate* option to explicitely reconfigure the database::

  python server.py --verbose --init
  # ...
  # Migration was sucessful

Running the server
------------------
When all has been set up, run::

  python server.py

To see available command line arguments, run::

  python server.py --help

On windows, use one those options::

  python server.py --console
  python server.py --service


Installing a worker
===================

The same procedure than above in `installing a server`_ applies, except for configuration and running.

Configuration
-------------
Edit the section *[worker]* of the configuration file *coalition.ini* according to your needs.

You may want to fine tune the installation using:

 - a dedicated system user and group to isolate the process and file ownership;
 - a `systemd service definition file <https://wiki.archlinux.org/index.php/Systemd>`_;
 - any system service monitoring daemon.

Running a worker
----------------
Run::

  python worker.py --verbose


