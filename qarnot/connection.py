"""Module describing a connection."""


# Copyright 2016 Qarnot computing
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from qarnot import get_url, raise_on_error
from qarnot.disk import Disk
from qarnot.task import Task
from qarnot.exceptions import *
import requests
import sys
import warnings
import os
from json import dumps as json_dumps
from requests.exceptions import ConnectionError
if sys.version_info[0] >= 3:  # module renamed in py3
    import configparser as config  # pylint: disable=import-error
else:
    import ConfigParser as config  # pylint: disable=import-error


#########
# class #
#########

class Connection(object):
    """Represents the couple cluster/user to which submit tasks.
    """
    def __init__(self, fileconf=None, client_token=None, cluster_url=None, cluster_unsafe=False, cluster_timeout=None):
        """Create a connection to a cluster with given config file, options or environment variables.
        Available environment variable are
        `QARNOT_CLUSTER_URL`, `QARNOT_CLUSTER_UNSAFE`, `QARNOT_CLUSTER_TIMEOUT` and `QARNOT_CLIENT_TOKEN`.

        :param fileconf: path to a qarnot configuration file or a corresponding dict
        :type fileconf: str or dict
        :param str client_token: API Token
        :param str cluster_url: (optional) Cluster url.
        :param bool cluster_unsafe: (optional) Disable certificate check
        :param int cluster_timeout: (optional) Timeout value for every request

        Configuration sample:

        .. code-block:: ini

           [cluster]
           # url of the REST API
           url=https://localhost
           # No SSL verification ?
           unsafe=False
           [client]
           # auth string of the client
           token=login

        """
        self._http = requests.session()

        if fileconf is not None:
            if isinstance(fileconf, dict):
                warnings.warn("Dict config should be replaced by constructor explicit arguments.")
                self.cluster = None
                if fileconf.get('cluster_url'):
                    self.cluster = fileconf.get('cluster_url')
                auth = fileconf.get('client_auth')
                self.timeout = fileconf.get('cluster_timeout')
                if fileconf.get('cluster_unsafe'):
                    self._http.verify = False
            else:
                cfg = config.ConfigParser()
                with open(fileconf) as cfgfile:
                    cfg.readfp(cfgfile)

                    self.cluster = None
                    if cfg.has_option('cluster', 'url'):
                        self.cluster = cfg.get('cluster', 'url')

                    if cfg.has_option('client', 'token'):
                        auth = cfg.get('client', 'token')
                    elif cfg.has_option('client', 'auth'):
                        warnings.warn('auth is deprecated, use token instead.')
                        auth = cfg.get('client', 'auth')
                    else:
                        auth = None
                    self.timeout = None
                    if cfg.has_option('cluster', 'timeout'):
                        self.timeout = cfg.getint('cluster', 'timeout')
                    if cfg.has_option('cluster', 'unsafe') \
                       and cfg.getboolean('cluster', 'unsafe'):
                        self._http.verify = False
        else:
            self.cluster = cluster_url
            self.timeout = cluster_timeout
            self._http.verify = not cluster_unsafe
            auth = client_token

        if self.cluster is None:
            self.cluster = os.getenv("QARNOT_CLUSTER_URL")

        if auth is None:
            auth = os.getenv("QARNOT_CLIENT_TOKEN")

        if os.getenv("QARNOT_CLUSTER_UNSAFE") is not None:
            self._http.verify = not os.getenv("QARNOT_CLUSTER_UNSAFE") in ["true", "True", "1"]

        if os.getenv("QARNOT_CLUSTER_TIMEOUT") is not None:
            self.timeout = int(os.getenv("QARNOT_CLUSTER_TIMEOUT"))

        if auth is None:
            raise QarnotGenericException("Token is mandatory.")
        self._http.headers.update({"Authorization": auth})

        if self.cluster is None:
            self.cluster = "https://api.qarnot.com"
        resp = self._get('/')
        raise_on_error(resp)

    def _get(self, url, **kwargs):
        """Perform a GET request on the cluster.

        :param str url:
          relative url of the file (according to the cluster url)

        :rtype: :class:`requests.Response`
        :returns: The response to the given request.

        :raises qarnot.exceptions.UnauthorizedException: invalid credentials

        .. note:: Additional keyword arguments are passed to the underlying
           :func:`requests.Session.get`.
        """
        while True:
            try:
                ret = self._http.get(self.cluster + url, timeout=self.timeout,
                                     **kwargs)
                if ret.status_code == 401:
                    raise UnauthorizedException()
                return ret
            except ConnectionError as exception:

                if str(exception) == "('Connection aborted.', BadStatusLine(\"\'\'\",))":
                    pass
                else:
                    raise

    def _patch(self, url, json=None, **kwargs):
        """perform a PATCH request on the cluster

        :param url: :class:`str`,
          relative url of the file (according to the cluster url)
        :param json: the data to json serialize and post

        :rtype: :class:`requests.Response`
        :returns: The response to the given request.

        :raises qarnot.exceptions.UnauthorizedException: invalid credentials

        .. note:: Additional keyword arguments are passed to the underlying
           :attr:`requests.Session.post()`.
        """
        while True:
            try:
                if json is not None:
                    if 'headers' not in kwargs:
                        kwargs['headers'] = dict()
                    kwargs['headers']['Content-Type'] = 'application/json'
                    kwargs['data'] = json_dumps(json)
                ret = self._http.patch(self.cluster + url,
                                       timeout=self.timeout, **kwargs)
                if ret.status_code == 401:
                    raise UnauthorizedException()
                return ret
            except ConnectionError as exception:
                if str(exception) == "('Connection aborted.', BadStatusLine(\"\'\'\",))":
                    pass
                else:
                    raise

    def _post(self, url, json=None, *args, **kwargs):
        """perform a POST request on the cluster

        :param url: :class:`str`,
          relative url of the file (according to the cluster url)
        :param json: the data to json serialize and post

        :rtype: :class:`requests.Response`
        :returns: The response to the given request.

        :raises qarnot.exceptions.UnauthorizedException: invalid credentials

        .. note:: Additional keyword arguments are passed to the underlying
           :attr:`requests.Session.post()`.
        """
        while True:
            try:
                if json is not None:
                    if 'headers' not in kwargs:
                        kwargs['headers'] = dict()
                    kwargs['headers']['Content-Type'] = 'application/json'
                    kwargs['data'] = json_dumps(json)
                ret = self._http.post(self.cluster + url,
                                      timeout=self.timeout, *args, **kwargs)
                if ret.status_code == 401:
                    raise UnauthorizedException()
                return ret
            except ConnectionError as exception:
                if str(exception) == "('Connection aborted.', BadStatusLine(\"\'\'\",))":
                    pass
                else:
                    raise

    def _delete(self, url, **kwargs):
        """Perform a DELETE request on the cluster.

        :param url: :class:`str`,
          relative url of the file (according to the cluster url)

        :rtype: :class:`requests.Response`
        :returns: The response to the given request.

        :raises qarnot.exceptions.UnauthorizedException: invalid credentials

        .. note:: Additional keyword arguments are passed to the underlying
          :attr:`requests.Session.delete()`.
        """

        while True:
            try:
                ret = self._http.delete(self.cluster + url,
                                        timeout=self.timeout, **kwargs)
                if ret.status_code == 401:
                    raise UnauthorizedException()
                return ret
            except ConnectionError as exception:
                if str(exception) == "('Connection aborted.', BadStatusLine(\"\'\'\",))":
                    pass
                else:
                    raise

    def _put(self, url, json=None, **kwargs):
        """Performs a PUT on the cluster."""
        while True:
            try:
                if json is not None:
                    if 'headers' not in kwargs:
                        kwargs['headers'] = dict()
                    kwargs['headers']['Content-Type'] = 'application/json'
                    kwargs['data'] = json_dumps(json)
                ret = self._http.put(self.cluster + url,
                                     timeout=self.timeout, **kwargs)
                if ret.status_code == 401:
                    raise UnauthorizedException()
                return ret
            except ConnectionError as exception:
                if str(exception) == "('Connection aborted.', BadStatusLine(\"\'\'\",))":
                    pass
                else:
                    raise

    @property
    def user_info(self):
        """Get information of the current user on the cluster.

        :rtype: :class:`UserInfo`
        :returns: Requested information.

        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        """
        resp = self._get(get_url('user'))
        raise_on_error(resp)
        ret = resp.json()
        return UserInfo(ret)

    def disks(self):
        """Get the list of disks on this cluster for this user.

        :rtype: List of :class:`~qarnot.disk.Disk`.
        :returns: Disks on the cluster owned by the user.


        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        """
        response = self._get(get_url('disk folder'))
        raise_on_error(response)
        disks = [Disk.from_json(self, data) for data in response.json()]
        return disks

    def tasks(self):
        """Get the list of tasks stored on this cluster for this user.

        :rtype: List of :class:`~qarnot.task.Task`.
        :returns: Tasks stored on the cluster owned by the user.

        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        """
        response = self._get(get_url('tasks'))
        raise_on_error(response)
        return [Task.from_json(self, task) for task in response.json()]

    def retrieve_task(self, uuid):
        """Retrieve a :class:`qarnot.task.Task` from its uuid

        :param str uuid: Desired task uuid
        :rtype: :class:`~qarnot.task.Task`
        :returns: Existing task defined by the given uuid
        :raises qarnot.exceptions.MissingTaskException: task does not exist
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        """

        response = self._get(get_url('task update', uuid=uuid))
        if response.status_code == 404:
            raise MissingTaskException(response.json()['message'])
        raise_on_error(response)
        return Task.from_json(self, response.json())

    def retrieve_or_create_disk(self, description):
        """Retrieve a :class:`~qarnot.disk.Disk` from its description, or create a new one.

        .. note:: Description are not unique, if multiple description match, an exception will be raised


        :param str description: a short description of the disk
        :rtype: :class:`~qarnot.disk.Disk`
        :returns: Existing or newly created disk defined by the given description
        :raises ValueError: no such disk
        :raises qarnot.exceptions.MaxDiskException: disk quota reached
        :raises qarnot.exceptions.MissingDiskException: disk does not exist
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        """

        disks = self.disks()

        matches = [d for d in disks if d.description == description]
        matchcount = len(matches)
        if matchcount == 0:
            return self.create_disk(description)
        elif matchcount == 1:
            return matches[0]
        else:
            raise QarnotGenericException("No unique match for given description.")

    def retrieve_disk(self, uuid):
        """Retrieve a :class:`~qarnot.disk.Disk` from its uuid

        :param str uuid: Desired disk uuid
        :rtype: :class:`~qarnot.disk.Disk`
        :returns: Existing disk defined by the given uuid
        :raises ValueError: no such disk
        :raises qarnot.exceptions.MissingDiskException: disk does not exist
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        """

        response = self._get(get_url('disk info', name=uuid))
        if response.status_code == 404:
            raise MissingDiskException(response.json()['message'])
        raise_on_error(response)
        return Disk.from_json(self, response.json())

    def create_disk(self, description, lock=False, tags=None):
        """Create a new :class:`~qarnot.disk.Disk`.

        :param str description: a short description of the disk
        :param bool lock: prevents the disk to be removed accidentally
        :param list(str) tags: custom tags

        :rtype: :class:`qarnot.disk.Disk`
        :returns: The created :class:`~qarnot.disk.Disk`.

        :raises qarnot.exceptions.MaxDiskException: disk quota reached
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        """
        disk = Disk(self, description, lock=lock, tags=tags)
        disk.create()
        return disk

    def create_task(self, name, profile, instancecount_or_range=1):
        """Create a new :class:`~qarnot.task.Task`.

        :param str name: given name of the task
        :param str profile: which profile to use with this task
        :param instancecount_or_range: number of instances, or ranges on which to run task. Defaults to 1.
        :type instancecount_or_range: int or str
        :rtype: :class:`~qarnot.task.Task`
        :returns: The created :class:`~qarnot.task.Task`.

        .. note:: See available profiles with :meth:`profiles`.
        """
        return Task(self, name, profile, instancecount_or_range)

    def profiles(self):
        """Get list of profiles available on the cluster.

        :rtype: List of :class:`Profile`

        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        """

        url = get_url('profiles')
        response = self._get(url)
        raise_on_error(response)
        profiles_list = []
        for p in response.json():
            url = get_url('profile details', profile=p)
            response2 = self._get(url)
            if response2.status_code == 404:
                continue
            profiles_list.append(Profile(response2.json()))
        return profiles_list

    def retrieve_profile(self, name):
        """Get details of a profile from its name.

        :rtype: :class:`Profile`

        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        """

        url = get_url('profile details', profile=name)
        response = self._get(url)
        raise_on_error(response)
        if response.status_code == 404:
            raise QarnotGenericException(response.json()['message'])
        return Profile(response.json())


###################
# utility Classes #
###################

class UserInfo(object):
    """Information about a qarnot user."""

    def __init__(self, info):
        self.email = info.get('email', '')
        """:type: :class:`str`

        User email address."""

        self.disk_count = info['diskCount']
        """:type: :class:`int`

        Number of disks owned by the user."""
        self.max_disk = info['maxDisk']
        """:type: :class:`int`

        Maximum number of disks allowed (resource and result disks)."""
        self.quota_bytes = info['quotaBytes']
        """:type: :class:`int`

        Total storage space allowed for the user's disks (in Bytes)."""
        self.used_quota_bytes = info['usedQuotaBytes']
        """:type: :class:`int`

        Total storage space used by the user's disks (in Bytes)."""
        self.task_count = info['taskCount']
        """:type: :class:`int`

        Total number of tasks belonging to the user."""
        self.max_task = info['maxTask']
        """:type: :class:`int`

        Maximum number of tasks the user is allowed to create."""
        self.running_task_count = info['runningTaskCount']
        """:type: :class:`int`

        Number of tasks currently in 'Submitted' state."""
        self.max_running_task = info['maxRunningTask']
        """:type: :class:`int`

        Maximum number of running tasks."""
        self.max_instances = info['maxInstances']
        """:type: :class:`int`

        Maximum number of instances."""


class Profile(object):
    """Information about a profile."""
    def __init__(self, info):
        self.name = info['name']
        """:type: :class:`str`

        Name of the profile."""
        self.constants = tuple((cst['name'], cst['value'])
                               for cst in info['constants'])
        """:type: List of (:class:`str`, :class:`str`)

        List of couples (name, value) representing constants for this profile
        and their default values."""

    def __repr__(self):
        return 'Profile(name=%s, constants=%r}' % (self.name, self.constants)
