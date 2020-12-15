"""Module for disk object."""

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


from __future__ import print_function

from qarnot import get_url, raise_on_error
from qarnot.exceptions import *
import posixpath
import os
import os.path
import time
import hashlib
import datetime
import threading
import itertools

try:
    from progressbar import AnimatedMarker, Bar, ETA, Percentage, AdaptiveETA, ProgressBar, AdaptiveTransferSpeed
except:
    pass


class Disk(object):
    """Represents a resource/result disk on the cluster.

    This class is the interface to manage resources or results from a
    :class:`qarnot.task.Task`.

    .. note::
       A :class:`Disk` must be created with
       :meth:`qarnot.connection.Connection.create_disk`
       or retrieved with :meth:`qarnot.connection.Connection.disks` or `qarnot.connection.Connection.retrieve_disk`.

    .. note::
       Paths given as 'remote' arguments,
       (or as path arguments for :func:`Disk.directory`)
       **must** be valid unix-like paths.
    """

    # Creation
    def __init__(self, connection, description, lock=False,
                 tags=None):
        """
        Create a disk on a cluster.

        :param :class:`qarnot.connection.Connection` connection: represents the cluster on which to create the disk
        :param str description: a short description of the disk
        :param bool lock: prevents the disk to be removed accidentally
        :param list(str) tags: Custom tags

        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        """
        self._uuid = None
        self._description = description
        self._file_count = 0
        self._used_space_bytes = 0
        self._locked = lock

        self._connection = connection
        self._filethreads = {}  # A dictionary containing key:value where key is
        #  the remote destination on disk, and value a running thread.
        self._filecache = {}  # A dictionary containing key:value where key is
        #  the remote destination on disk, and value an opened Python File.
        self._add_mode = UploadMode.blocking
        self._tags = tags
        self._auto_update = True
        self._last_auto_update_state = self._auto_update
        self._update_cache_time = 5
        self._last_cache = time.time()

    def create(self):
        """Create the Disk on the REST API.
        .. note:: This method should not be used unless if the object was created with the constructor.
        """
        data = {
            "description": self._description,
            "locked": self._locked
            }
        if self._tags is not None:
            data["tags"] = self._tags
        response = self._connection._post(get_url('disk folder'), json=data)
        if response.status_code == 403:
            raise MaxDiskException(response.json()['message'])
        else:
            raise_on_error(response)

        self._uuid = response.json()['uuid']
        self.update()

    @classmethod
    def _retrieve(cls, connection, disk_uuid):
        """Retrieve information of a disk on a cluster.

        :param :class:`qarnot.connection.Connection` connection: the cluster
            to get the disk from
        :param str disk_uuid: the UUID of the disk to retrieve

        :rtype: :class:`qarnot.disk.Disk`
        :returns: The retrieved disk.

        :raises qarnot.exceptions.MissingDiskException: the disk is not on the server
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        """
        response = connection._get(get_url('disk info', name=disk_uuid))

        if response.status_code == 404:
            raise MissingDiskException(response.json()['message'])
        raise_on_error(response)

        return cls.from_json(connection, response.json())

    @classmethod
    def from_json(cls, connection, json_disk):
        """Create a Disk object from a json disk

        :param qarnot.connection.Connection connection: the cluster connection
        :param dict json_disk: Dictionary representing the disk
        """
        disk = cls(connection,
                   json_disk['description'],
                   lock=json_disk['locked'],
                   tags=json_disk.get('tags'))
        disk._update(json_disk)
        return disk

    # Disk Management
    def update(self, flushcache=False):
        """
        Update the disk object from the REST Api.
        The flushcache parameter can be used to force the update, otherwise a cached version of the object
        will be served when accessing properties of the object.

        :raises qarnot.exceptions.MissingDiskException: the disk is not on the server
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        """
        if self._uuid is None:
            return

        now = time.time()
        if (now - self._last_cache) < self._update_cache_time and not flushcache:
            return

        response = self._connection._get(get_url('disk info', name=self._uuid))
        if response.status_code == 404:
            raise MissingDiskException(response.json()['message'])
        raise_on_error(response)

        self._update(response.json())
        self._last_cache = time.time()

    def _update(self, json_disk):
        """ Update local disk object from json
        :type json_disk: dict
        """
        self._uuid = json_disk["uuid"]
        self._description = json_disk["description"]
        self._file_count = json_disk["fileCount"]
        self._used_space_bytes = json_disk["usedSpaceBytes"]
        self._locked = json_disk["locked"]
        self._file_count = json_disk["fileCount"]
        self._used_space_bytes = json_disk["usedSpaceBytes"]
        self._tags = json_disk.get("tags", None)

    def delete(self):
        """Delete the disk represented by this :class:`Disk`.

        :raises qarnot.exceptions.MissingDiskException: the disk is not on the server
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        """
        response = self._connection._delete(
            get_url('disk info', name=self._uuid))

        if response.status_code == 404:
            raise MissingDiskException(response.json()['message'])
        if response.status_code == 403:
            raise LockedDiskException(response.json()['message'])
        raise_on_error(response)

    def get_archive(self, extension='zip', local=None):
        """Get an archive of this disk's content.

        :param str extension: in {'tar', 'tgz', 'zip'},
          format of the archive to get
        :param str local: name of the file to output to

        :rtype: :class:`str`
        :returns:
         The filename of the retrieved archive.

        :raises qarnot.exceptions.MissingDiskException: the disk is not on the server
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises ValueError: invalid extension format
        """
        response = self._connection._get(
            get_url('get disk', name=self._uuid, ext=extension),
            stream=True)

        if response.status_code == 404:
            raise MissingDiskException(response.json()['message'])
        elif response.status_code == 400:
            raise ValueError('invalid file format : {0}', extension)
        else:
            raise_on_error(response)

        local = local or ".".join([self._uuid, extension])
        if os.path.isdir(local):
            local = os.path.join(local, ".".join([self._uuid, extension]))

        with open(local, 'wb') as f_local:
            for elt in response.iter_content():
                f_local.write(elt)
        return local

    def list_files(self):
        """List files on the whole disk.

        :rtype: List of :class:`FileInfo`.
        :returns: List of the files on the disk.

        :raises qarnot.exceptions.MissingDiskException: the disk is not on the server
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        """

        self.flush()
        response = self._connection._get(
            get_url('tree disk', name=self._uuid))
        if response.status_code == 404:
            raise MissingDiskException(response.json()['message'])
        raise_on_error(response)
        return [FileInfo(**f) for f in response.json()]

    def directory(self, directory=''):
        """List files in a directory of the disk. Doesn't go through
        subdirectories.

        :param str directory: path of the directory to inspect.
          Must be unix-like.

        :rtype: List of :class:`FileInfo`.
        :returns: Files in the given directory on the :class:`Disk`.

        :raises qarnot.exceptions.MissingDiskException: the disk is not on the server
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials

        .. note::
           Paths in results are relative to the *directory* argument.
        """

        self.flush()

        response = self._connection._get(
            get_url('ls disk', name=self._uuid, path=directory))
        if response.status_code == 404:
            if response.json()['message'] == 'no such disk':
                raise MissingDiskException(response.json()['message'])
        raise_on_error(response)
        return [FileInfo(**f) for f in response.json()]

    def sync_directory(self, directory, verbose=False):
        """Synchronize a local directory with the remote disks.

        :param str directory: The local directory to use for synchronization
        :param bool verbose: Print information about synchronization operations

        .. warning::
           Local changes are reflected on the server, a file present on the
           disk but not in the local directory will be deleted from the disk.

           A file present in the directory but not in the disk will be uploaded.

        .. note::
           The following parameters are used to determine whether
           synchronization is required :

              * name
              * size
              * sha1sum
        """
        if not directory.endswith('/'):
            directory = directory + '/'

        filesdict = {}
        for root, dirs, files in os.walk(directory):
            for file_ in files:
                filepath = os.path.join(root, file_)
                name = filepath[len(directory) - 1:]
                filesdict[name] = filepath
            for dir_ in dirs:
                filepath = os.path.join(root, dir_)
                name = filepath[len(directory) - 1:]
                if not name.endswith('/'):
                    name += '/'
                filesdict[name] = filepath

        self.sync_files(filesdict, verbose)

    def sync_files(self, files, verbose=False, ignore_directories=False):
        """Synchronize files  with the remote disks.

        :param dict files: Dictionary of synchronized files
        :param bool verbose: Print information about synchronization operations
        :param bool ignore_directories: Ignore directories when looking for changes

        Dictionary key is the remote file path while value is the local file
        path.

        .. warning::
           Local changes are reflected on the server, a file present on the
           disk but
           not in the local directory will be deleted from the disk.

           A file present in the directory but not in the disk will be uploaded.

        .. note::
           The following parameters are used to determine whether
           synchronization is required :

              * name
              * size
              * sha1sum
        """
        def generate_file_sha1(filepath, blocksize=2**20):
            """Generate SHA1 from file"""
            sha1 = hashlib.sha1()
            with open(filepath, "rb") as file_:
                while True:
                    buf = file_.read(blocksize)
                    if not buf:
                        break
                    sha1.update(buf)
            return sha1.hexdigest()

        def create_qfi(name, filepath):
            """Create a QFI from a file"""
            if not name.startswith('/'):
                name = '/' + name
            mtime = os.path.getmtime(filepath)
            dtutc = datetime.datetime.utcfromtimestamp(mtime)
            dtutc = dtutc.replace(microsecond=0)

            type = 'directory' if os.path.isdir(filepath) else 'file'
            sha1 = generate_file_sha1(filepath) if type is 'file' else 'N/A'
            size = os.stat(filepath).st_size if type is 'file' else 0
            qfi = FileInfo(dtutc, name, size, type, sha1)
            qfi.filepath = filepath
            return qfi

        localfiles = []
        for name, filepath in files.items():
            qfi = create_qfi(name, filepath)
            localfiles.append(qfi)

        if ignore_directories:
            local = set([x for x in localfiles if not x.directory])
            remote = set([x for x in self.list_files() if not x.directory])
        else:
            local = set(localfiles)
            remote = set(self.list_files())
        adds = local - remote
        removes = remote - local

        sadds = sorted(adds, key=lambda x: x.sha1sum)
        groupedadds = [list(g) for _, g in itertools.groupby(
            sadds, lambda x: x.sha1sum)]

        for file_ in removes:
            renames = [x for x in adds if x.sha1sum == file_.sha1sum and not x.directory and not file_.directory]
            if len(renames) > 0:
                for dup in renames:
                    if verbose:
                        print("Copy", file_.name, "to", dup.name)
                    self.add_link(file_.name, dup.name)
            if verbose:
                print("remove ", file_.name)
            self.delete_file(file_.name, force=True)

        remote = self.list_files()

        for entry in groupedadds:
            try:
                rem = next(x for x in remote if x.sha1sum == entry[0].sha1sum and not x.directory and not entry[0].directory)
                if rem.name == entry[0].name:
                    continue
                if verbose:
                    print("Link:", rem.name, "<-", entry[0].name)
                self.add_link(rem.name, entry[0].name)
            except StopIteration:
                if verbose:
                    print("Upload:", entry[0].name)
                self.add_file(entry[0].filepath, entry[0].name)
            if len(entry) > 1:  # duplicate files
                for link in entry[1:]:
                    if not link.directory:
                        if verbose:
                            print("Link:", entry[0].name, "<-", link.name)
                        self.add_link(entry[0].name, link.name)
                    else:
                        if verbose:
                            print("Add dir" + link.filepath + " " + str(link.name))
                        self.add_file(link.filepath, link.name)

    def flush(self):
        """Ensure all files added through :meth:`add_file`/:meth:`add_directory`
        are on the disk.

        :raises qarnot.exceptions.MissingDiskException: the disk is not on the server
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises TypeError: trying to write on a R/O disk
        :raises IOError: user space quota reached
        """
        for thread in self._filethreads.values():
            thread.join()

        self._filethreads.clear()

        for remote, file_ in self._filecache.items():
            self._add_file(file_, remote)

        self._filecache.clear()

    def move(self, source, dest):
        """Move a file or a directory inside a disk.
        Missing destination path directories can be created.
        Trailing '/' for directories affect behavior.

        :param str source: name of the source file
        :param str dest: name of the destination file

        .. warning::
            No clobber on move. If dest exist move will fail.

        :raises qarnot.exceptions.MissingDiskException: the disk is not on the server
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        """

        data = [
            {
                "source": source,
                "dest": dest
            }
        ]
        url = get_url('move disk', name=self._uuid)
        response = self._connection._post(url, json=data)

        raise_on_error(response)
        self.update(True)

    def add_link(self, target, linkname):
        """Create link between files on the disk

        :param str target: name of the existing file to duplicate
        :param str linkname: name of the created file

        .. warning::
           File size is counted twice, this method is meant to save upload
           time, not space.

        :raises qarnot.exceptions.MissingDiskException: the disk is not on the server
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        """
        data = [
            {
                "target": target,
                "linkName": linkname
            }
        ]
        url = get_url('link disk', name=self._uuid)
        response = self._connection._post(url, json=data)

        raise_on_error(response)
        self.update(True)

    def _is_executable(self, file):
        try:
            return os.access(file.name, os.X_OK)
        except IOError:
            return False

    def add_file(self, local_or_file, remote=None, mode=None, **kwargs):
        """Add a local file or a Python File on the disk.

        .. note::
           You can also use **disk[remote] = local**

        .. warning::
           In non blocking mode, you may receive an exception during an other
           operation (like :meth:`flush`).

        :param local_or_file: path of the local file or an opened Python File
        :type local_or_file: str or File
        :param str remote: name of the remote file
          (defaults to *local_or_file*)
        :param mode: mode with which to add the file
          (defaults to :attr:`~UploadMode.blocking` if not set by
          :attr:`Disk.add_mode`)
        :type mode: :class:`UploadMode`

        :raises qarnot.exceptions.MissingDiskException: the disk is not on the server
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises TypeError: trying to write on a R/O disk
        :raises IOError: user space quota reached
        :raises ValueError: file could not be created
        """
        mode = mode or self._add_mode

        if isinstance(local_or_file, str):
            if os.path.isdir(local_or_file):
                dest = remote or os.path.basename(local_or_file)
                url = get_url('update file', name=self._uuid, path=os.path.dirname(dest))
                response = self._connection._post(
                    url,
                    )
                if response.status_code == 404:
                    raise MissingDiskException(response.json()['message'])
                raise_on_error(response)
                return
            else:
                file_ = open(local_or_file, 'rb')
        else:
            file_ = local_or_file

        dest = remote or os.path.basename(file_.name)
        if isinstance(dest, FileInfo):
            dest = dest.name

        # Ensure 2 threads do not write on the same file
        previous = self._filethreads.get(dest)
        if previous is not None:
            previous.join()
            del self._filethreads[dest]

        # Do not delay a file added differently
        if dest in self._filecache:
            self._filecache[dest].close()
            del self._filecache[dest]

        if mode is UploadMode.blocking:
            return self._add_file(file_, dest, **kwargs)
        elif mode is UploadMode.lazy:
            self._filecache[dest] = file_
        else:
            thread = threading.Thread(None, self._add_file, dest, (file_, dest), **kwargs)
            thread.start()
            self._filethreads[dest] = thread

    def _add_file(self, file_, dest, **kwargs):
        """Add a file on the disk.

        :param File file_: an opened Python File
        :param str dest: name of the remote file (defaults to filename)

        :raises qarnot.exceptions.MissingDiskException: the disk is not on the server
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        """

        try:
            file_.seek(0)
        except AttributeError:
            pass

        if dest.endswith('/'):
            dest = os.path.join(dest, os.path.basename(file_.name))
        url = get_url('update file', name=self._uuid, path=os.path.dirname(dest))

        try:
            # If requests_toolbelt is installed, we can use its
            # MultipartEncoder to stream the upload and save memory overuse
            from requests_toolbelt import MultipartEncoder  # noqa
            m = MultipartEncoder(
                fields={'filedata': (os.path.basename(dest), file_)})
            response = self._connection._post(
                url,
                data=m,
                headers={'Content-Type': m.content_type})
        except ImportError:
            response = self._connection._post(
                url,
                files={'filedata': (os.path.basename(dest), file_)})

        if response.status_code == 404:
            raise MissingDiskException(response.json()['message'])
        raise_on_error(response)

        # Update file settings
        if 'executable' not in kwargs:
            kwargs['executable'] = self._is_executable(file_)
        self.update_file_settings(dest, **kwargs)
        self.update(True)

    def add_directory(self, local, remote="", mode=None):
        """ Add a directory to the disk. Does not follow symlinks.
        File hierarchy is preserved.

        .. note::
           You can also use **disk[remote] = local**

        .. warning::
           In non blocking mode, you may receive an exception during an other
           operation (like :meth:`flush`).

        :param str local: path of the local directory to add
        :param str remote: path of the directory on remote node
          (defaults to *local*)
        :param mode: the mode with which to add the directory
          (defaults to :attr:`~Disk.add_mode`)
        :type mode: :class:`UploadMode`

        :raises qarnot.exceptions.MissingDiskException: the disk is not on the server
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises ValueError: one or more file(s) could not be created
        :raises IOError: not a valid directory
        """

        if not os.path.isdir(local):
            raise IOError("Not a valid directory")
        if not remote.endswith('/'):
            remote += '/'
        for dirpath, _, files in os.walk(local):
            remote_loc = dirpath.replace(local, remote, 1)
            for filename in files:
                self.add_file(os.path.join(dirpath, filename),
                              posixpath.join(remote_loc, filename), mode)

    def get_file_iterator(self, remote, chunk_size=4096, progress=None):
        """Get a file iterator from the disk.

        .. note::
           This function is a generator, and thus can be used in a for loop

        :param remote: the name of the remote file or a QFileInfo
        :type remote: str or FileInfo
        :param int chunk_size: Size of chunks to be yield

        :raises qarnot.exceptions.MissingDiskException: the disk is not on the server
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises ValueError: no such file
        """

        progressbar = None

        def _cb(c, total, remote):
            c = max(0, min(c, 100))
            progressbar.update(c)

        if isinstance(remote, FileInfo):
            remote = remote.name

        # Ensure file is done uploading
        pending = self._filethreads.get(remote)
        if pending is not None:
            pending.join()

        if remote in self._filecache:
            try:
                self._filecache[remote].seek(0)
            except AttributeError:
                pass
            while True:
                chunk = self._filecache[remote].read(chunk_size)
                if not chunk:
                    break
                yield chunk
        else:
            response = self._connection._get(
                get_url('update file', name=self._uuid, path=remote),
                stream=True)

            if response.status_code == 404:
                if response.json()['message'] == "No such disk":
                    raise MissingDiskException(response.json()['message'])
            raise_on_error(response)

            total_length = float(response.headers.get('content-length'))
            if progress is not None:
                if progress is True:
                    progress = _cb
                    try:
                        widgets = [
                            remote,
                            ' ', Percentage(),
                            ' ', AnimatedMarker(),
                            ' ', Bar(),
                            ' ', AdaptiveETA(),
                            ' ', AdaptiveTransferSpeed(unit='B')
                        ]
                        progressbar = ProgressBar(widgets=widgets, max_value=total_length)
                    except Exception as e:
                        print(str(e))
                        progress = None
            elif progress is False:
                progress = None

            count = 0
            for chunk in response.iter_content(chunk_size):
                count += len(chunk)
                if progress is not None:
                    progress(count, total_length, remote)
                yield chunk
        if progress:
            progressbar.finish()

    def get_all_files(self, output_dir, progress=None):
        """Get all files the disk.

        :param str output_dir: local directory for the retrieved files.
        :param progress: can be a callback (read,total,filename)  or True to display a progress bar
        :type progress: bool or function(float, float, str)
        :raises qarnot.exceptions.MissingDiskException: the disk is not on the server
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials

        .. warning:: Will override *output_dir* content.

        """

        for file_info in self:
            outpath = os.path.normpath(file_info.name.lstrip('/'))
            self.get_file(file_info, os.path.join(output_dir,
                                                  outpath), progress)

    def get_file(self, remote, local=None, progress=None):
        """Get a file from the disk.

        .. note::
           You can also use **disk[file]**

        :param remote: the name of the remote file or a QFileInfo
        :type remote: str or FileInfo
        :param str local: local name of the retrieved file  (defaults to *remote*)
        :param progress: can be a callback (read,total,filename)  or True to display a progress bar
        :type progress: bool or function(float, float, str)
        :rtype: :class:`str`
        :returns: The name of the output file.

        :raises qarnot.exceptions.MissingDiskException: the disk is not on the server
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises ValueError: no such file
          (:exc:`KeyError` with disk[file] syntax)
        """

        def make_dirs(_local):
            """Make directory if needed"""
            directory = os.path.dirname(_local)
            if directory != '' and not os.path.exists(directory):
                os.makedirs(directory)

        if isinstance(remote, FileInfo):
            if remote.directory:
                return
            remote = remote.name

        if local is None:
            local = os.path.basename(remote)

        if os.path.isdir(local):
            local = os.path.join(local, os.path.basename(remote))

        make_dirs(local)

        if os.path.isdir(local):
            return
        with open(local, 'wb') as f_local:
            for chunk in self.get_file_iterator(remote, progress=progress):
                f_local.write(chunk)
        return local

    def update_file_settings(self, remote_path, **kwargs):
        settings = dict(**kwargs)

        if len(settings) < 1:
            return

        response = self._connection._put(
            get_url('update file', name=self._uuid, path=remote_path),
            json=settings)

        if response.status_code == 404:
                if response.json()['message'] == "No such disk":
                    raise MissingDiskException(response.json()['message'])
        raise_on_error(response)

    def delete_file(self, remote, force=False):
        """Delete a file from the disk.

        .. note::
           You can also use **del disk[file]**

        :param str remote: the name of the remote file
        :param bool force: ignore missing files

        :raises qarnot.exceptions.MissingDiskException: the disk is not on the server
        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials
        :raises ValueError: no such file
          (:exc:`KeyError` with disk['file'] syntax)

        """
        dest = remote.name if isinstance(remote, FileInfo) else remote

        # Ensure 2 threads do not write on the same file
        pending = self._filethreads.get(dest)
        if pending is not None:
            pending.join()

        # Remove the file from local cache if present
        if dest in self._filecache:
            self._filecache[dest].close()
            del self._filecache[dest]
            # The file is not present on the disk so just return
            return

        response = self._connection._delete(
            get_url('update file', name=self._uuid, path=dest))

        if response.status_code == 404:
            if response.json()['message'] == "No such disk":
                raise MissingDiskException(response.json()['message'])
        if force and response.status_code == 404:
            pass
        else:
            raise_on_error(response)
        self.update(True)

    def commit(self):
        """Replicate local changes on the current object instance to the REST API

        :raises qarnot.exceptions.QarnotGenericException: API general error, see message for details
        :raises qarnot.exceptions.UnauthorizedException: invalid credentials

        .. note:: When updating disks' properties, auto update will be disabled until commit is called.
        """
        data = {
            "description": self._description,
            "locked": self._locked
        }
        if self._tags is not None:
            data["tags"] = self._tags

        self._auto_update = self._last_auto_update_state
        resp = self._connection._put(get_url('disk info', name=self._uuid),
                                     json=data)
        if resp.status_code == 404:
            raise MissingDiskException(resp.json()['message'])
        raise_on_error(resp)
        self.update(True)

    @property
    def uuid(self):
        """:type: :class:`str`

        :getter: Returns this disk's uuid

        The disk's UUID."""
        return self._uuid

    @property
    def tags(self):
        """:type: :class:list(`str`)

        :getter: Returns this disk's tags
        :setter: Sets this disk's tags


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
    def add_mode(self):
        """:type: :class:`UploadMode`

        :getter: Returns this disk's add mode
        :setter: Sets this disk's add mode


        Default mode for adding files.
        """
        return self._add_mode

    @add_mode.setter
    def add_mode(self, value):
        """Add mode setter"""
        self._add_mode = value

    @property
    def description(self):
        """:type: :class:`str`

        :getter: Returns this disk's description
        :setter: Sets this disk's description

        The disk's description.
        """
        if self._auto_update:
            self.update()
        return self._description

    @description.setter
    def description(self, value):
        """Description setter"""
        self._description = value
        self._auto_update = False

    @property
    def file_count(self):
        """:type: :class:`int`

        :getter: Returns this disk's file count

        The number of files on the disk.
        """
        if self._auto_update:
            self.update()
        return self._file_count

    @property
    def used_space_bytes(self):
        """:type: :class:`int`

        :getter: Returns this disk's used space in bytes

        The total space used on the disk in bytes.
        """
        if self._auto_update:
            self.update()
        return self._used_space_bytes

    @property
    def locked(self):
        """:type: :class:`bool`

        :getter: Returns this disk's locked state
        :setter: Sets this disk's locked state


        The disk's lock state. If True, prevents the disk to be removed
        by a subsequent :meth:`qarnot.connection.Connection.create_task` with *force*
        set to True.
        """
        if self._auto_update:
            self.update()
        return self._locked

    @locked.setter
    def locked(self, value):
        """Change disk's lock state."""
        self._locked = value
        self._auto_update = False

    @property
    def auto_update(self):
        """:type: :class:`bool`

        :getter: Returns this disk's auto update state
        :setter: Sets this disk's auto update state


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

    def __str__(self):
        return (
            ("[LOCKED]     - " if self.locked else "[NON LOCKED] - ") +
            self.uuid + " - " + self.description
        )

    # Operators
    def __getitem__(self, filename):
        """x.__getitem__(y) <==> x[y]"""
        try:
            return self.get_file(filename)
        except ValueError:
            raise KeyError(filename)

    def __setitem__(self, remote, filename):
        """x.__setitem__(i, y) <==> x[i]=y"""
        if os.path.isdir(filename):
            return self.add_directory(filename, remote)
        return self.add_file(filename, remote)

    def __delitem__(self, filename):
        """x.__delitem__(y) <==> del x[y]"""
        try:
            return self.delete_file(filename)
        except ValueError:
            raise KeyError(filename)

    def __contains__(self, item):
        """D.__contains__(k) -> True if D has a key k, else False"""
        if isinstance(item, FileInfo):
            item = item.name
        return item in [f.name for f in self.list_files()]

    def __iter__(self):
        """x.__iter__() <==> iter(x)"""
        return iter(self.list_files())

    def __eq__(self, other):
        """x.__eq__(y) <==> x == y"""
        if isinstance(other, self.__class__):
            return self._uuid == other._uuid
        return False

    def __ne__(self, other):
        """x.__ne__(y) <==> x != y"""
        return not self.__eq__(other)


# Utility Classes
class FileInfo(object):
    """Information about a file."""
    def __init__(self, lastChange, name, size, fileFlags, sha1Sum):

        self.lastchange = None
        """:type: :class:`datetime`

        UTC Last change time of the file on the :class:`Disk`."""

        if isinstance(lastChange, datetime.datetime):
            self.lastchange = lastChange
        else:
            self.lastchange = datetime.datetime.strptime(lastChange,
                                                         "%Y-%m-%dT%H:%M:%SZ")

        self.name = name
        """:type: :class:`str`

        Path of the file on the :class:`Disk`."""
        self.size = size
        """:type: :class:`int`

        Size of the file on the :class:`Disk` (in Bytes)."""
        self.directory = fileFlags == 'directory'
        """:type: :class:`bool`

        Is the file a directory."""

        self.sha1sum = sha1Sum
        """:type: :class:`str`

        SHA1 Sum of the file."""

        if not self.directory:
            self.executable = fileFlags == 'executableFile'
            """:type: :class:`bool`

            Is the file executable."""

        self.filepath = None  # Only for sync

    def __repr__(self):
        template = 'FileInfo(lastchange={0}, name={1}, size={2}, '\
                   'directory={3}, sha1sum={4})'
        return template.format(self.lastchange, self.name, self.size,
                               self.directory, self.sha1sum)

    def __eq__(self, other):
        return (self.name == other.name and
                self.size == other.size and
                self.directory == other.directory and
                self.sha1sum == other.sha1sum)

    def __hash__(self):
        return (hash(self.name) ^
                hash(self.size) ^
                hash(self.directory) ^
                hash(self.sha1sum))


class UploadMode(object):
    """How to add files on a :class:`Disk`."""
    blocking = 0
    """Call to :func:`~Disk.add_file` :func:`~Disk.add_directory`
    or blocks until file is done uploading."""
    background = 1
    """Launch a background thread for uploading."""
    lazy = 2
    """Actual uploading is made by the :func:`~Disk.flush` method call."""
