Contribute
==========

Development platform
--------------------

Coalition is `free software LGPL licensed <https://en.wikipedia.org/wiki/GNU_Lesser_General_Public_License>`_ and `hosted on github <https://github.com/MercenariesEngineering/coalition>`_. Feel free to participate via a github account.

Running tests
-------------

The test suite requires a database. To prevent a database overwriting, you should **first backup your current database or change the database reference in the coalition.ini** configuration file.

Run::

  # Intialize a fresh database
  python server.py --init

  # Run the tests
  python tests/main_tests.py

The status of the tests must show no errors.

A **.travis.yml** file is provided for automated testing via `travis testing platform <https://travis-ci.org>`_.

Build documentation
-------------------

Go to the **coalition/doc** directory and run::

    ./build.sh
