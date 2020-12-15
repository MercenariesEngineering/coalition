Web interface
=============

With a web browser visit::

  http://<the-coalition-server-IP-or-hostname>:19211

If LDAP is configured in **coalition.ini**, you will be asked for a username and a password. Once logged in, some permissions are granted to you according to the LDAP policies.

By defaut no LDAP is required and any action are authorized.

You can select multiple lines while pressing <control> or <shift> key and mouse clic.

A double clic on a job will get you to the job log page.

The job page will remember your last jobs filtering criteria via localstorage so that you can refresh the page without loosing your customisations. Clear you browser's localstorage or click the button "reset filter" to revert to the default display.

In cloud mode, you can manually terminate worker instances with the "terminate" button in the workers tab.
