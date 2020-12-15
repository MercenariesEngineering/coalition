"""Module to handle a task."""

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


from os import makedirs, path
import time
import datetime
import warnings
import sys

from qarnot import disk
from qarnot import get_url, raise_on_error
from qarnot.exceptions import *
try:
    from progressbar import AnimatedMarker, Bar, ETA, Percentage, AdaptiveETA, ProgressBar
except:
    pass

RUNNING_DOWNLOADING_STATES = ['Submitted', 'PartiallyDispatched',
                              'FullyDispatched', 'PartiallyExecuting',
                              'FullyExecuting', 'DownloadingResults']


class Task(object):
    """Represents a Qarnot job.

    .. note::
       A :class:`Task` must be created with
       :meth:`qarnot.connection.Connection.create_task`
       or retrieved with :meth:`qarnot.connection.Connection.tasks` or :meth:`qarnot.connection.Connection.retrieve_task`.
    """
    def __init__(self, connection, name, profile, instancecount_or_range):
        """Create a new :class:`Task`.

        :param connection: the cluster on which to send the task
        :type connection: :class:`qarnot.connection.Connection`
        :param name: given name of the task
        :type name: :class:`str`
        :param str profile: which profile (payload) to use with this task

        :param instancecount_or_range: number of instances or ranges on which to run task
        :type instancecount_or_range: int or str
        """
        self._name = name
        self._profile = profile

        if isinstance(instancecount_or_range, int):
            self._instancecount = instancecount_or_range
            self._advanced_range = None
        else:
            self._advanced_range = instancecount_or_range
            self._instancecount = 0

        self._resource_disks = []
        self._result_disk = None
        self._connection = connection
        self.constants = {}
        """
         :type: :class:`dict(str,str)`

         Constants of the task.

        """

        self._auto_update = True
        self._last_auto_update_state = self._auto_update
        self._update_cache_time = 5

        self._last_cache = time.time()
        """
        Dictionary [CST] = val.

        Can be set until :meth:`run` is called

        .. note:: See available constants for a specific profile
              with :meth:`qarnot.connection.Connection.profile_info`.
        """

        self.constraints = {}
        self._state = 'UnSubmitted'  # RO property same for below
        self._uuid = None
        self._snapshots = False
        self._dirty = False
        self._rescount = -1
        self._snapshot_whitelist = None
        self._snapshot_blacklist = None
        self._results_whitelist = None
        self._results_blacklist = None
        self._status = None
        self._tags = []
        self._creation_date = None
        self._errors = None
        self._resource_disks_uuids = []
        self._result_disk_uuid = None

    @classmethod
    def _retrieve(cls, connection, uuid):
        """Retrieve a submitted task given its uuid.

        :param qarnot.connection.Connection connection:
          the cluster to retrieve the task from
        :param str uuid: the uuid of the task to retrieve

        :rtype: Task
        :returns: The retrieved task.

        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.MissingTaskException: no such task
        """
        resp = connection._get(get_url('task update', uuid=uuid))
        if resp.status_code == 404:
            raise MissingTaskException(resp.json()['message'])
        raise_on_error(resp)
        return Task.from_json(connection, resp.json())

    def run(self, output_dir=None, job_timeout=None, live_progress=False, results_progress=None):
        """Submit a task, wait for the results and download them if required.

        :param str output_dir: (optional) path to a directory that will contain the results
        :param float job_timeout: (optional) Number of seconds before the task :meth:`abort` if it is not
          already finished
        :param bool live_progress: (optional) display a live progress
        :param results_progress: (optional) can be a callback (read,total,filename) or True to display a progress bar
        :type results_progress: bool or function(float, float, str)
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.MaxTaskException: Task quota reached
        :raises qarnot.exceptions.NotEnoughCreditsException: Not enough credits
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.MissingDiskException:
          resource disk is not a valid disk

        .. note:: Will ensure all added file are on the resource disk
           regardless of their uploading mode.
        .. note:: If this function is interrupted (script killed for example),
           but the task is submitted, the task will still be executed remotely
           (results will not be downloaded)
        .. warning:: Will override *output_dir* content.
        """
        self.submit()
        self.wait(timeout=job_timeout, live_progress=live_progress)
        if job_timeout is not None:
            self.abort()
        if output_dir is not None:
            self.download_results(output_dir, progress=results_progress)

    def resume(self, output_dir, job_timeout=None, live_progress=False, results_progress=None):
        """Resume waiting for this task if it is still in submitted mode.
        Equivalent to :meth:`wait` + :meth:`download_results`.

        :param str output_dir: path to a directory that will contain the results
        :param float job_timeout: Number of seconds before the task :meth:`abort` if it is not
          already finished
        :param bool live_progress: display a live progress
        :param results_progress: can be a callback (read,total,filename) or True to display a progress bar
        :type results_progress: bool or function(float, float, str)
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.MissingTaskException: task does not exist
        :raises qarnot.exceptions.MissingDiskException:
          resource disk is not a valid disk

        .. note:: Do nothing if the task has not been submitted.
        .. warning:: Will override *output_dir* content.
        """
        if self._uuid is None:
            return output_dir
        self.wait(timeout=job_timeout, live_progress=live_progress)
        self.download_results(output_dir, progress=results_progress)

    def submit(self):
        """Submit task to the cluster if it is not already submitted.

        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.MaxTaskException: Task quota reached
        :raises qarnot.exceptions.NotEnoughCreditsException: Not enough credits
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.MissingDiskException:
          resource disk is not a valid disk

        .. note:: Will ensure all added files are on the resource disk
           regardless of their uploading mode.

        .. note:: To get the results, call :meth:`download_results` once the job is done.
        """
        if self._uuid is not None:
            return self._state
        for rdisk in self.resources:
            rdisk.flush()
        payload = self._to_json()
        resp = self._connection._post(get_url('tasks'), json=payload)

        if resp.status_code == 404:
            raise disk.MissingDiskException(resp.json()['message'])
        elif resp.status_code == 403:
            if resp.json()['message'].startswith('Maximum number of disks reached'):
                raise MaxDiskException(resp.json()['message'])
            else:
                raise MaxTaskException(resp.json()['message'])
        elif resp.status_code == 402:
            raise NotEnoughCreditsException(resp.json()['message'])
        raise_on_error(resp)
        self._uuid = resp.json()['uuid']

        if not isinstance(self._snapshots, bool):
            self.snapshot(self._snapshots)

        self.update(True)

    def abort(self):
        """Abort this task if running.

        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.MissingTaskException: task does not exist
        """
        self.update(True)

        resp = self._connection._post(
            get_url('task abort', uuid=self._uuid))

        if resp.status_code == 404:
            raise MissingTaskException(resp.json()['message'])
        raise_on_error(resp)

        self.update(True)

    def update_resources(self):
        """Update resources for a running task. Be sure to add new resources first.

        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.MissingTaskException: task does not exist
        """

        self.update(True)
        resp = self._connection._patch(
            get_url('task update', uuid=self._uuid))

        if resp.status_code == 404:
            raise MissingTaskException(resp.json()['message'])
        raise_on_error(resp)

        self.update(True)

    def delete(self, purge_resources=False, purge_results=False):
        """Delete this task on the server.

        :param bool purge_resources: parameter value is used to determine if the disk is also deleted.
                Defaults to False.

        :param bool purge_results: parameter value is used to determine if the disk is also deleted.
                Defaults to False.

        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.MissingTaskException: task does not exist
        """
        if self._uuid is None:
            return

        if purge_resources:
            rdisks = []
            for duuid in self._resource_disks_uuids:
                try:
                    d = disk.Disk._retrieve(self._connection, duuid)
                    rdisks.append(d)
                except disk.MissingDiskException as exception:
                    pass

        if purge_results:
            try:
                self.results.update()
            except disk.MissingDiskException as exception:
                purge_results = False

        resp = self._connection._delete(
            get_url('task update', uuid=self._uuid))
        if resp.status_code == 404:
            raise MissingTaskException(resp.json()['message'])
        raise_on_error(resp)

        if purge_resources:
            toremove = []
            for rdisk in rdisks:
                try:
                    rdisk.update()
                    rdisk.delete()
                    toremove.append(rdisk)
                except (disk.MissingDiskException, disk.LockedDiskException) as exception:
                    warnings.warn(str(exception))
            for tr in toremove:
                rdisks.remove(tr)
            self.resources = rdisks

        if purge_results:
            try:
                self._result_disk.delete()
                self._result_disk = None
                self._result_disk_uuid = None
            except (disk.MissingDiskException, disk.LockedDiskException) as exception:
                warnings.warn(str(exception))

        self._state = "Deleted"
        self._uuid = None

    def update(self, flushcache=False):
        """
        Update the task object from the REST Api.
        The flushcache parameter can be used to force the update, otherwise a cached version of the object
        will be served when accessing properties of the object.
        Some methods will flush the cache, like :meth:`submit`, :meth:`abort`, :meth:`wait` and :meth:`instant`.
        Cache behavior is configurable with :attr:`auto_update` and :attr:`update_cache_time`.

        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.MissingTaskException: task does not represent a
          valid one
        """
        if self._uuid is None:
            return

        now = time.time()
        if (now - self._last_cache) < self._update_cache_time and not flushcache:
            return

        resp = self._connection._get(
            get_url('task update', uuid=self._uuid))
        if resp.status_code == 404:
            raise MissingTaskException(resp.json()['message'])

        raise_on_error(resp)
        self._update(resp.json())
        self._last_cache = time.time()

    def _update(self, json_task):
        """Update this task from retrieved info."""
        self._name = json_task['name']
        self._profile = json_task['profile']
        self._instancecount = json_task.get('instanceCount')
        self._advanced_range = json_task.get('advancedRanges')
        self._resource_disks_uuids = json_task['resourceDisks']
        if len(self._resource_disks_uuids) != len(self._resource_disks):
            del self._resource_disks[:]
        self._result_disk_uuid = json_task['resultDisk']
        if 'status' in json_task:
            self._status = json_task['status']
        self._creation_date = datetime.datetime.strptime(json_task['creationDate'], "%Y-%m-%dT%H:%M:%SZ")
        if 'errors' in json_task:
            self._errors = [Error(d) for d in json_task['errors']]
        else:
            self._errors = []
        for constant in json_task['constants']:
            self.constants[constant.get('key')] = constant.get('value')
        self._uuid = json_task['uuid']
        self._state = json_task['state']
        self._tags = json_task.get('tags', None)
        if self._rescount < json_task['resultsCount']:
            self._dirty = True
        self._rescount = json_task['resultsCount']
        if 'resultsBlacklist' in json_task:
            self._results_blacklist = json_task['resultsBlacklist']
        if 'resultsWhitelist' in json_task:
            self._results_whitelist = json_task['resultsWhitelist']
        if 'snapshotWhitelist' in json_task:
            self._snapshot_whitelist = json_task['snapshotWhitelist']
        if 'snapshotBlacklist' in json_task:
            self._snapshot_blacklist = json_task['snapshotBlacklist']

    @classmethod
    def from_json(cls, connection, json_task):
        """Create a Task object from a json task.

        :param qarnot.connection.Connection connection: the cluster connection
        :param dict json_task: Dictionary representing the task
        :returns: The created :class:`~qarnot.task.Task`.
        """
        if 'instanceCount' in json_task:
            instancecount_or_range = json_task['instanceCount']
        else:
            instancecount_or_range = json_task['advancedRanges']
        new_task = cls(connection,
                       json_task['name'],
                       json_task['profile'],
                       instancecount_or_range)
        new_task._update(json_task)
        return new_task

    def commit(self):
        """Replicate local changes on the current object instance to the REST API

        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials

        .. note:: When updating disks' properties, auto update will be disabled until commit is called.
        """
        data = self._to_json()
        resp = self._connection._put(get_url('task update', uuid=self._uuid), json=data)
        self._auto_update = self._last_auto_update_state
        if resp.status_code == 404:
            raise MissingTaskException(resp.json()['message'])

        raise_on_error(resp)

    def wait(self, timeout=None, live_progress=False):
        """Wait for this task until it is completed.

        :param float timeout: maximum time (in seconds) to wait before returning
           (None => no timeout)
        :param bool live_progress: display a live progress

        :rtype: :class:`bool`
        :returns: Is the task finished

        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.MissingTaskException: task does not represent a valid
          one
        """

        live_progress = live_progress and sys.stdout.isatty()

        if live_progress:
            try:
                widgets = [
                    Percentage(),
                    ' ', AnimatedMarker(),
                    ' ', Bar(),
                    ' ', AdaptiveETA()
                ]
                progressbar = ProgressBar(widgets=widgets, max_value=100)
            except Exception as e:
                live_progress = False

        start = time.time()
        if self._uuid is None:
            self.update(True)
            return False

        nap = min(10, timeout) if timeout is not None else 10

        self.update(True)
        while self._state in RUNNING_DOWNLOADING_STATES:
            if live_progress:
                n = 0
                progress = 0
                while True:
                    time.sleep(1)
                    n += 1
                    if n >= nap:
                        break
                    progress = self.status.execution_progress if self.status is not None else 0
                    progress = max(0, min(progress, 100))
                    progressbar.update(progress)
            else:
                time.sleep(nap)

            self.update(True)

            if timeout is not None:
                elapsed = time.time() - start
                if timeout <= elapsed:
                    self.update()
                    return False
                else:
                    nap = min(10, timeout - elapsed)
        self.update(True)
        if live_progress:
            progressbar.finish()
        return True

    def snapshot(self, interval):
        """Start snapshooting results.
        If called, this task's results will be periodically
        updated, instead of only being available at the end.

        Snapshots will be taken every *interval* second from the time
        the task is submitted.

        :param int interval: the interval in seconds at which to take snapshots

        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.MissingTaskException: task does not represent a
          valid one

        .. note:: To get the temporary results, call :meth:`download_results`.
        """
        if self._uuid is None:
            self._snapshots = interval
            return
        resp = self._connection._post(get_url('task snapshot', uuid=self._uuid),
                                      json={"interval": interval})

        if resp.status_code == 400:
            raise ValueError(interval)
        elif resp.status_code == 404:
            raise MissingTaskException(resp.json()['message'])

        raise_on_error(resp)

        self._snapshots = True

    def instant(self):
        """Make a snapshot of the current task.

        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.MissingTaskException: task does not exist

        .. note:: To get the temporary results, call :meth:`download_results`.
        """
        if self._uuid is None:
            return

        resp = self._connection._post(get_url('task instant', uuid=self._uuid),
                                      json=None)

        if resp.status_code == 404:
            raise MissingTaskException(resp.json()['message'])
        raise_on_error(resp)

        self.update(True)

    @property
    def state(self):
        """:type: :class:`str`
        :getter: return this task's state

        State of the task.

        Value is in
           * UnSubmitted
           * Submitted
           * PartiallyDispatched
           * FullyDispatched
           * PartiallyExecuting
           * FullyExecuting
           * DownloadingResults
           * Cancelled
           * Success
           * Failure

        .. warning::
           this is the state of the task when the object was retrieved,
           call :meth:`update` for up to date value.
        """
        if self._auto_update:
            self.update()
        return self._state

    @property
    def resources(self):
        """:type: list(:class:`~qarnot.disk.Disk`)
        :getter: Returns this task's resources disks
        :setter: Sets this task's resources disks

        Represents resource files.
        """
        if self._auto_update:
            self.update()

        if not self._resource_disks:
            for duuid in self._resource_disks_uuids:
                d = disk.Disk._retrieve(self._connection,
                                        duuid)
                self._resource_disks.append(d)

        return self._resource_disks

    @resources.setter
    def resources(self, value):
        """This is a setter."""
        self._resource_disks = value

    @property
    def results(self):
        """:type: :class:`~qarnot.disk.Disk`
        :getter: Returns this task's results disk
        :setter: Sets this task's results disk

        Represents results files."""
        if self._result_disk is None:
            self._result_disk = disk.Disk._retrieve(self._connection,
                                                    self._result_disk_uuid)

        if self._auto_update:
            self.update()

        return self._result_disk

    @results.setter
    def results(self, value):
        """ This is a setter."""
        self._result_disk = value

    def download_results(self, output_dir, progress=None):
        """Download results in given *output_dir*.

        :param str output_dir: local directory for the retrieved files.
        :param progress: can be a callback (read,total,filename)  or True to display a progress bar
        :type progress: bool or function(float, float, str)
        :raises qarnot.exceptions.MissingDiskException: the disk is not on the server
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials

        .. warning:: Will override *output_dir* content.

        """

        if self._uuid is not None:
            self.update()

        if not path.exists(output_dir):
            makedirs(output_dir)

        if self._dirty:
            self.results.get_all_files(output_dir, progress=progress)

    def stdout(self):
        """Get the standard output of the task
        since the submission of the task.

        :rtype: :class:`str`
        :returns: The standard output.

        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.MissingTaskException: task does not exist

        .. note:: The buffer is circular, if stdout is too big, prefer calling
          :meth:`fresh_stdout` regularly.
        """
        if self._uuid is None:
            return ""
        resp = self._connection._get(
            get_url('task stdout', uuid=self._uuid))

        if resp.status_code == 404:
            raise MissingTaskException(resp.json()['message'])

        raise_on_error(resp)

        return resp.text

    def fresh_stdout(self):
        """Get what has been written on the standard output since last time
        this function was called or since the task has been submitted.

        :rtype: :class:`str`
        :returns: The new output since last call.

        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.MissingTaskException: task does not exist
        """
        if self._uuid is None:
            return ""
        resp = self._connection._post(
            get_url('task stdout', uuid=self._uuid))

        if resp.status_code == 404:
            raise MissingTaskException(resp.json()['message'])

        raise_on_error(resp)
        return resp.text

    def stderr(self):
        """Get the standard error of the task
        since the submission of the task.

        :rtype: :class:`str`
        :returns: The standard error.

        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.MissingTaskException: task does not exist

        .. note:: The buffer is circular, if stderr is too big, prefer calling
          :meth:`fresh_stderr` regularly.
        """
        if self._uuid is None:
            return ""
        resp = self._connection._get(
            get_url('task stderr', uuid=self._uuid))

        if resp.status_code == 404:
            raise MissingTaskException(resp.json()['message'])

        raise_on_error(resp)
        return resp.text

    def fresh_stderr(self):
        """Get what has been written on the standard error since last time
        this function was called or since the task has been submitted.

        :rtype: :class:`str`
        :returns: The new error messages since last call.

        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises qarnot.exceptions.MissingTaskException: task does not exist
        """
        if self._uuid is None:
            return ""
        resp = self._connection._post(
            get_url('task stderr', uuid=self._uuid))

        if resp.status_code == 404:
            raise MissingTaskException(resp.json()['message'])

        raise_on_error(resp)
        return resp.text

    @property
    def uuid(self):
        """:type: :class:`str`
        :getter: Returns this task's uuid

        The task's uuid.

        Automatically set when a task is submitted.
        """
        return self._uuid

    @property
    def name(self):
        """:type: :class:`str`
        :getter: Returns this task's name
        :setter: Sets this task's name

        The task's name.

        Can be set until task is submitted.
        """
        return self._name

    @name.setter
    def name(self, value):
        """Setter for name."""
        if self.uuid is not None:
            raise AttributeError("can't set attribute on a launched task")
        else:
            self._name = value

    @property
    def tags(self):
        """:type: :class:list(`str`)
        :getter: Returns this task's tags
        :setter: Sets this task's tags

        Custom tags.
        """
        if self._auto_update:
            self.update()

        return self._tags

    @tags.setter
    def tags(self, value):
        self._tags = value
        self._auto_update = False

    @property
    def profile(self):
        """:type: :class:`str`
        :getter: Returns this task's profile
        :setter: Sets this task's profile

        The profile to run the task with.

        Can be set until :meth:`run` is called.
        """
        return self._profile

    @profile.setter
    def profile(self, value):
        """setter for profile"""
        if self.uuid is not None:
            raise AttributeError("can't set attribute on a launched task")
        else:
            self._profile = value

    @property
    def instancecount(self):
        """:type: :class:`int`
        :getter: Returns this task's instance count
        :setter: Sets this task's instance count

        Number of instances needed for the task.

        Can be set until :meth:`run` is called.

        :raises AttributeError: if :attr:`advanced_range` is not None when setting this property

        .. warning:: This property is mutually exclusive with :attr:`advanced_range`
        """
        return self._instancecount

    @instancecount.setter
    def instancecount(self, value):
        """Setter for instancecount."""
        if self.uuid is not None:
            raise AttributeError("can't set attribute on a launched task")

        if self.advanced_range is not None:
            raise AttributeError("Can't set instancecount if advanced_range is not None")
        self._instancecount = value

    @property
    def advanced_range(self):
        """:type: :class:`str`
        :getter: Returns this task's advanced range
        :setter: Sets this task's advanced range

        Advanced instances range selection.

        Allows to select which instances will be computed.
        Should be None or match the following extended regular expression
        """r"""**"([0-9]+|[0-9]+-[0-9]+)(,([0-9]+|[0-9]+-[0-9]+))+"**
        eg: 1,3-8,9,12-19

        Can be set until :meth:`run` is called.

        :raises AttributeError: if :attr:`instancecount` is not 0 when setting this property

        .. warning:: This property is mutually exclusive with :attr:`instancecount`
        """
        return self._advanced_range

    @advanced_range.setter
    def advanced_range(self, value):
        """Setter for advanced_range."""
        if self.uuid is not None:
            raise AttributeError("can't set attribute on a launched task")
        if self.instancecount != 0:
            raise AttributeError("Can't set advanced_range if instancecount is not 0")
        self._advanced_range = value

    @property
    def snapshot_whitelist(self):
        """:type: :class:`str`
        :getter: Returns this task's snapshot whitelist
        :setter: Sets this task's snapshot whitelist

        Snapshot white list (regex) for :meth:`snapshot` and :meth:`instant`

        Can be set until task is submitted.
        """
        return self._snapshot_whitelist

    @snapshot_whitelist.setter
    def snapshot_whitelist(self, value):
        """Setter for snapshot whitelist, this can only be set before tasks submission
        """
        if self.uuid is not None:
            raise AttributeError("can't set attribute on a launched task")
        self._snapshot_whitelist = value

    @property
    def snapshot_blacklist(self):
        """:type: :class:`str`
        :getter: Returns this task's snapshot blacklist
        :setter: Sets this task's snapshot blacklist

        Snapshot black list (regex) for :meth:`snapshot` :meth:`instant`

        Can be set until task is submitted.
        """
        return self._snapshot_blacklist

    @snapshot_blacklist.setter
    def snapshot_blacklist(self, value):
        """Setter for snapshot blacklist, this can only be set before tasks submission
        """
        if self.uuid is not None:
            raise AttributeError("can't set attribute on a launched task")
        self._snapshot_blacklist = value

    @property
    def results_whitelist(self):
        """:type: :class:`str`
        :getter: Returns this task's results whitelist
        :setter: Sets this task's results whitelist

        Results whitelist (regex)

        Can be set until task is submitted.
        """
        return self._results_whitelist

    @results_whitelist.setter
    def results_whitelist(self, value):
        """Setter for results whitelist, this can only be set before tasks submission
        """
        if self.uuid is not None:
            raise AttributeError("can't set attribute on a launched task")
        self._results_whitelist = value

    @property
    def results_blacklist(self):
        """:type: :class:`str`
        :getter: Returns this task's results blacklist
        :setter: Sets this task's results blacklist

        Results blacklist (regex)

        Can be set until task is submitted.
        """
        if self._auto_update:
            self.update()

        return self._results_blacklist

    @results_blacklist.setter
    def results_blacklist(self, value):
        """Setter for results blacklist, this can only be set before tasks submission
        """
        if self.uuid is not None:
            raise AttributeError("can't set attribute on a launched task")
        self._results_blacklist = value

    @property
    def status(self):
        """:type: :class:`TaskStatus`
        :getter: Returns this task's status

        Status of the task
        """
        if self._auto_update:
            self.update()

        if self._status:
            return TaskStatus(self._status)
        return self._status

    @property
    def creation_date(self):
        """:type: :class:`str`

        :getter: Returns this task's creation date

        Creation date of the task (UTC Time)
        """
        return self._creation_date

    @property
    def errors(self):
        """:type: list(:class:`Error`)
        :getter: Returns this task's errors if any.

        Error reason if any, empty string if none
        """
        if self._auto_update:
            self.update()

        return self._errors

    @property
    def auto_update(self):
        """:type: :class:`bool`

        :getter: Returns this task's auto update state
        :setter: Sets this task's auto update state

        Auto update state, default to True
        When auto update is disabled properties will always return cached value
        for the object and a call to :meth:`update` will be required to get latest values from the REST Api.
        """
        return self._auto_update

    @auto_update.setter
    def auto_update(self, value):
        """Setter for auto_update feature
        """
        self._auto_update = value
        self._last_auto_update_state = self._auto_update

    @property
    def update_cache_time(self):
        """:type: :class:`int`

        :getter: Returns this task's auto update state
        :setter: Sets this task's auto update state

        Cache expiration time, default to 5s
        """
        return self._update_cache_time

    @update_cache_time.setter
    def update_cache_time(self, value):
        """Setter for update_cache_time
        """
        self._update_cache_time = value

    def _to_json(self):
        """Get a dict ready to be json packed from this task."""
        const_list = [
            {'key': key, 'value': value}
            for key, value in self.constants.items()
        ]
        constr_list = [
            {'key': key, 'value': value}
            for key, value in self.constraints.items()
        ]

        self._resource_disks_uuids = [x.uuid for x in self._resource_disks]
        json_task = {
            'name': self._name,
            'profile': self._profile,
            'resourceDisks': self._resource_disks_uuids,
            'constants': const_list,
            'constraints': constr_list
        }

        if self._result_disk is not None:
            json_task['resultDisk'] = self._result_disk.uuid

        if self._advanced_range is not None:
            json_task['advancedRanges'] = self._advanced_range
        else:
            json_task['instanceCount'] = self._instancecount

        json_task["tags"] = self._tags

        if self._snapshot_whitelist is not None:
            json_task['snapshotWhitelist'] = self._snapshot_whitelist
        if self._snapshot_blacklist is not None:
            json_task['snapshotBlacklist'] = self._snapshot_blacklist
        if self._results_whitelist is not None:
            json_task['resultsWhitelist'] = self._results_whitelist
        if self._results_blacklist is not None:
            json_task['resultsBlacklist'] = self._results_blacklist
        return json_task

    def __str__(self):
        return '{0} - {1} - {2} - InstanceCount : {3} - {4} - Resources : {5} - Results : {6}'\
            .format(self.name,
                    self._uuid,
                    self._profile,
                    self._instancecount,
                    self.state,
                    (self._resource_disks_uuids if self._resource_disks is not None else ""),
                    (self._result_disk.uuid if self._result_disk is not None else ""))

    # Context manager
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if (exc_type is None) or exc_type != MissingTaskException:
            self.delete()
        return False


class Error(object):
    """Task error

    .. note:: Read-only class
    """
    def __init__(self, json):
        self.code = json['code']
        """:type: :class:`str`

        Error code."""

        self.message = json['message']
        """:type: :class:`str`

        Error message."""

        self.debug = json['debug']
        """:type: :class:`str`

        Optional extra debug information"""

    def __str__(self):
        if sys.version_info > (3, 0):
            return ', '.join("{0}={1}".format(key, val) for (key, val) in self.__dict__.items())
        else:
            return ', '.join("{0}={1}".format(key, val) for (key, val) in self.__dict__.iteritems())  # pylint: disable=no-member


# Status
class TaskStatus(object):
    """Task status

    .. note:: Read-only class
    """
    def __init__(self, json):
        self.download_progress = json['downloadProgress']
        """:type: :class:`float`

        Resources download progress to the instances."""

        self.execution_progress = json['executionProgress']
        """:type: :class:`float`

        Task execution progress."""

        self.upload_progress = json['uploadProgress']
        """:type: :class:`float`

        Task results upload progress to the API."""

        self.instance_count = json['instanceCount']
        """:type: :class:`int`

        Number of running instances."""

        self.download_time = json['downloadTime']
        """:type: :class:`str`

        Resources download time to the instances."""

        self.download_time_sec = json['downloadTimeSec']
        """:type: :class:`float`

        Resources download time to the instances in seconds."""

        self.environment_time = json['environmentTime']
        """:type: :class:`str`

        Environment time to the instances."""

        self.environment_time_sec = json['environmentTimeSec']
        """:type: :class:`float`

        Environment time to the instances in seconds."""

        self.execution_time = json['executionTime']
        """:type: :class:`str`

        Task execution time."""

        self.execution_time_sec = json['executionTimeSec']
        """:type: :class:`float`

        Task execution time in seconds."""

        self.upload_time = json['uploadTime']
        """:type: :class:`str`

        Task results upload time to the API."""

        self.upload_time_sec = json['uploadTimeSec']
        """:type: :class:`float`

        Task results upload time to the API in seconds."""

        self.wall_time = json["wallTime"]
        """:type: :class:`str`

        Wall time of the task."""

        self.wall_time_sec = json["wallTimeSec"]
        """:type: :class:`float`

        Wall time of the task in seconds."""

        self.succeeded_range = json['succeededRange']
        """:type: :class:`str`

        Successful instances range."""

        self.executed_range = json['executedRange']
        """:type: :class:`str`

        Executed instances range."""

        self.failed_range = json['failedRange']
        """:type: :class:`str`

        Failed instances range."""

        self.running_instances_info = None
        """:type: :class:`RunningInstancesInfo`

        Running instances information."""

        if 'runningInstancesInfo' in json and json['runningInstancesInfo'] is not None:
            self.running_instances_info = RunningInstancesInfo(json['runningInstancesInfo'])

    def __str__(self):
        if sys.version_info > (3, 0):
            return ', '.join("{0}={1}".format(key, val) for (key, val) in self.__dict__.items())
        else:
            return ', '.join("{0}={1}".format(key, val) for (key, val) in self.__dict__.iteritems())  # pylint: disable=no-member


class TaskActiveForward(object):
    """Task Active Forward

    .. note:: Read-only class
    """
    def __init__(self, json):
        self.application_port = json['applicationPort']
        """:type: :class:`int`

        Application Port."""

        self.forwarder_port = json['forwarderPort']
        """:type: :class:`int`

        Forwarder Port."""

        self.forwarder_host = json['forwarderHost']
        """:type: :class:`str`

        Forwarder Host."""

        def __str__(self):
            if sys.version_info > (3, 0):
                return ', '.join("{0}={1}".format(key, val) for (key, val) in self.__dict__.items())
            else:
                return ', '.join("{0}={1}".format(key, val) for (key, val) in self.__dict__.iteritems())  # pylint: disable=no-member


class RunningInstancesInfo(object):
    """Running Instances Information

    .. note:: Read-only class
    """
    def __init__(self, json):
        self.per_running_instance_info = []
        """:type: list(:class:`PerRunningInstanceInfo`)

        Per running instances information."""

        if 'perRunningInstanceInfo' in json and json['perRunningInstanceInfo'] is not None:
            self.per_running_instance_info = [PerRunningInstanceInfo(x) for x in json['perRunningInstanceInfo']]

        self.timestamp = json['timestamp']
        """:type: :class:`str`

        Last information update timestamp."""

        self.average_frequency_ghz = json['averageFrequencyGHz']
        """:type: :class:`float`

        Average Frequency in GHz."""

        self.max_frequency_ghz = json['maxFrequencyGHz']
        """:type: :class:`float`

        Maximum Frequency in GHz."""

        self.min_frequency_ghz = json['minFrequencyGHz']
        """:type: :class:`float`

        Minimum Frequency in GHz."""

        self.average_max_frequency_ghz = json['averageMaxFrequencyGHz']
        """:type: :class:`float`

        Average Maximum Frequency in GHz."""

        self.average_cpu_usage = json['averageCpuUsage']
        """:type: :class:`float`

        Average CPU Usage."""

        self.cluster_power_indicator = json['clusterPowerIndicator']
        """:type: :class:`float`

        Cluster Power Indicator."""

        self.average_memory_usage = json['averageMemoryUsage']
        """:type: :class:`float`

        Average Memory Usage."""

        self.average_network_in_kbps = json['averageNetworkInKbps']
        """:type: :class:`float`

        Average Network Input in Kbps."""

        self.average_network_out_kbps = json['averageNetworkOutKbps']
        """:type: :class:`float`

        Average Network Output in Kbps."""

        self.total_network_in_kbps = json['totalNetworkInKbps']
        """:type: :class:`float`

        Total Network Input in Kbps."""

        self.total_network_out_kbps = json['totalNetworkOutKbps']
        """:type: :class:`float`

        Total Network Output in Kbps."""

    def __str__(self):
        if sys.version_info > (3, 0):
            return ', '.join("{0}={1}".format(key, val) for (key, val) in self.__dict__.items())
        else:
            return ', '.join("{0}={1}".format(key, val) for (key, val) in self.__dict__.iteritems())  # pylint: disable=no-member


class PerRunningInstanceInfo(object):
    """Per Running Instance Information

    .. note:: Read-only class
    """
    def __init__(self, json):
        self.phase = json['phase']
        """:type: :class:`str`

        Instance phase."""

        self.instance_id = json['instanceId']
        """:type: :class:`int`

        Instance number."""

        self.max_frequency_ghz = json['maxFrequencyGHz']
        """:type: :class:`float`

        Maximum CPU frequency in GHz."""

        self.current_frequency_ghz = json['currentFrequencyGHz']
        """:type: :class:`float`

        Current CPU frequency in GHz."""

        self.cpu_usage = json['cpuUsage']
        """:type: :class:`float`

        Current CPU usage."""

        self.max_memory_mb = json['maxMemoryMB']
        """:type: :class:`int`

        Maximum memory size in MB."""

        self.current_memory_mb = json['currentMemoryMB']
        """:type: :class:`int`

        Current memory size in MB."""

        self.memory_usage = json['memoryUsage']
        """:type: :class:`float`

        Current memory usage."""

        self.network_in_kbps = json['networkInKbps']
        """:type: :class:`float`

        Network Input in Kbps."""

        self.network_out_kbps = json['networkOutKbps']
        """:type: :class:`float`

        Network Output in Kbps."""

        self.progress = json['progress']
        """:type: :class:`float`

        Instance progress."""

        self.execution_time_sec = json['executionTimeSec']
        """:type: :class:`float`

        Instance execution time in seconds."""

        self.execution_time_ghz = json['executionTimeGHz']
        """:type: :class:`float`

        Instance execution time GHz"""

        self.cpu_model = json['cpuModel']
        """:type: :class:`str`

        CPU model"""

        self.active_forward = []
        """type: list(:class:`TaskActiveForward`)

        Active forwards list."""

        if 'activeForwards' in json:
            self.active_forward = [TaskActiveForward(x) for x in json['activeForwards']]

    def __str__(self):
        if sys.version_info > (3, 0):
            return ', '.join("{0}={1}".format(key, val) for (key, val) in self.__dict__.items())
        else:
            return ', '.join("{0}={1}".format(key, val) for (key, val) in self.__dict__.iteritems())  # pylint: disable=no-member
