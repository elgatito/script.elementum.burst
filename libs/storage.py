# coding: utf-8
"""
    Taken from xmbcwift2 module
    xbmcswift2.storage
    ~~~~~~~~~~~~~~~~~~

    This module contains persistent storage classes.

    :copyright: (c) 2012 by Jonathan Beluch
    :license: GPLv3, see LICENSE for more details.
"""
import os
import csv
import xbmc
import json
import time
import uuid
import shutil
import collections
from datetime import datetime
from datetime import timedelta
from quasar.provider import log


try:
    import cPickle as pickle
except ImportError:
    import pickle


class _PersistentDictMixin(object):
    """ Persistent dictionary with an API compatible with shelve and anydbm.

    The dict is kept in memory, so the dictionary operations run as fast as
    a regular dictionary.

    Write to disk is delayed until close or sync (similar to gdbm's fast mode).

    Input file format is automatically discovered.
    Output file format is selectable between pickle, json, and csv.
    All three serialization formats are backed by fast C implementations.
    """

    initial_update = collections.MutableMapping.update

    def __init__(self, filename, flag='c', mode=None, file_format='pickle'):
        self.flag = flag  # r=readonly, c=create, or n=new
        self.mode = mode  # None or an octal triple like 0644
        self.file_format = file_format  # 'csv', 'json', or 'pickle'
        self.filename = filename
        if flag != 'n' and os.access(filename, os.R_OK):
            log.debug('Reading %s storage from disk at "%s"', self.file_format, self.filename)
            file_obj = open(filename, 'rb' if file_format == 'pickle' else 'r')
            with file_obj:
                self.load(file_obj)

    def sync(self):
        """
        Write the dict to disk
        """
        if self.flag == 'r':
            return

        temp_name = self.filename + str(uuid.uuid4())
        file_obj = open(temp_name, 'wb' if self.file_format == 'pickle' else 'w')
        try:
            self.dump(file_obj)

        except Exception:
            os.remove(temp_name)
            raise

        finally:
            file_obj.close()

        shutil.move(temp_name, self.filename)  # atomic commit
        if self.mode is not None:
            os.chmod(self.filename, self.mode)

    def close(self):
        """
        Calls sync
        """
        self.sync()

    def __enter__(self):
        return self

    def __exit__(self):
        self.close()

    def dump(self, file_obj):
        """
        Handles the writing of the dict to the file object
        """
        if self.file_format == 'csv':
            csv.writer(file_obj).writerows(self.raw_dict().items())

        elif self.file_format == 'json':
            json.dump(self.raw_dict(), file_obj, separators=(',', ':'))

        elif self.file_format == 'pickle':
            pickle.dump(dict(self.raw_dict()), file_obj, 2)

        else:
            raise NotImplementedError('Unknown format: ' + repr(self.file_format))

    def load(self, file_obj):
        """
        Load the dict from the file object
        """
        # try formats from most restrictive to least restrictive
        for loader in (pickle.load, json.load, csv.reader):
            file_obj.seek(0)
            try:
                return self.initial_update(loader(file_obj))

            except:
                pass
        raise ValueError('File not in a supported format')

    def raw_dict(self):
        """
        Returns the underlying dict
        """
        raise NotImplementedError


class _Storage(collections.MutableMapping, _PersistentDictMixin):
    """Storage that acts like a dict but also can persist to disk.

    :param filename: An absolute filepath to reprsent the storage on disk. The
                     storage will loaded from this file if it already exists,
                     otherwise the file will be created.
    :param file_format: 'pickle', 'json' or 'csv'. pickle is the default. Be
                        aware that json and csv have limited support for python
                        objets.

    .. warning:: Currently there are no limitations on the size of the storage.
                 Please be sure to call :meth:`~xbmcswift2._Storage.clear`
                 periodically.
    """

    def __init__(self, filename, file_format='pickle'):
        """
        Acceptable formats are 'csv', 'json' and 'pickle'.
        """
        self._items = {}
        _PersistentDictMixin.__init__(self, filename, file_format=file_format)

    def __setitem__(self, key, val):
        self._items.__setitem__(key, val)

    def __getitem__(self, key):
        return self._items.__getitem__(key)

    def __delitem__(self, key):
        self._items.__delitem__(key)

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return self._items.__len__

    def raw_dict(self):
        """
        Returns the wrapped dict
        """
        return self._items

    # it check if the value exist in the key
    def has(self, key):
        return self.get(key, None) is not None

    def dump(self, file_obj):
        super(_Storage, self).dump(file_obj)

    def add(self, key, value=""):
        self[key] = value

    def remove(self, key):
        if self.has(key):
            del self[key]

    def clear(self):
        super(_Storage, self).clear()
        self.sync()


class TimedStorage(_Storage):
    """
    A dict with the ability to persist to disk and TTL for items.
    """

    def __init__(self, filename, file_format='pickle', ttl=None):
        """
        TTL if provided should be a datetime.timedelta. Any entries
        older than the provided TTL will be removed upon load and upon item
        access.
        """
        self.TTL = ttl
        _Storage.__init__(self, filename, file_format=file_format)

    def __call__(self, filename, file_format='pickle', ttl=None):
        self.__init__(filename, file_format, ttl)

    def __setitem__(self, key, val, raw=False):
        if raw:
            self._items[key] = val

        else:
            self._items[key] = (val, time.time())

    def __getitem__(self, key):
        val, timestamp = self._items[key]
        if self.TTL and (datetime.utcnow() - datetime.utcfromtimestamp(timestamp) > self.TTL):
            del self._items[key]
            return self._items[key][0]  # Will raise KeyError

        return val

    def initial_update(self, mapping):
        """
        Initially fills the underlying dictionary with keys, values and
        timestamps.
        """
        for key, val in mapping.items():
            _, timestamp = val
            if not self.TTL or (datetime.utcnow() - datetime.utcfromtimestamp(timestamp) < self.TTL):
                self.__setitem__(key, val, raw=True)


class Storage:
    _unsynced_storages = {}
    _storage_path = ""

    def __init__(self):
        pass

    @classmethod
    def open(cls, item="", ttl=60 * 24, force=False, storage_path=xbmc.translatePath("special://temp")):
        cls._storage_path = os.path.join(storage_path, ".storage")
        if not os.path.isdir(cls._storage_path):
            os.makedirs(cls._storage_path)

        return cls.__get_storage(name=item, ttl=ttl, force=force)

    @classmethod
    def list_storages(cls):
        """
        Returns a list of existing stores. The returned names can then be
        used to call get_storage().
        """
        # Filter out any storages used by xbmc swift2 so caller doesn't corrupt
        # them.
        return [name for name in os.listdir(cls._storage_path) if not name.startswith('.')]

    @classmethod
    def __get_storage(cls, name='main', file_format='pickle', ttl=None, force=False):
        """
        Returns a storage for the given name. The returned storage is a
        fully functioning python dictionary and is designed to be used that
        way. It is usually not necessary for the caller to load or save the
        storage manually. If the storage does not already exist, it will be
        created.

        .. seealso:: :class:`xbmcswift2.TimedStorage` for more details.

        :param name: The name  of the storage to retrieve.
        :param file_format: Choices are 'pickle', 'csv', and 'json'. Pickle is
                            recommended as it supports python objects.

                            .. note:: If a storage already exists for the given
                                      name, the file_format parameter is
                                      ignored. The format will be determined by
                                      the existing storage file.
        :param ttl: The time to live for storage items specified in minutes or None
                    for no expiration. Since storage items aren't expired until a
                    storage is loaded form disk, it is possible to call
                    get_storage() with a different TTL than when the storage was
                    created. The currently specified TTL is always honored.
        :param force: if it reads always from the disk
        """

        if not hasattr(cls, '_unsynced_storages'):
            cls._unsynced_storages = {}
        filename = os.path.join(cls._storage_path, name)
        try:
            if force:
                raise KeyError

            storage = cls._unsynced_storages[filename]
            log.debug('Loaded storage "%s" from memory', name)

        except KeyError:
            if ttl:
                ttl = timedelta(minutes=ttl)

            try:
                storage = TimedStorage(filename, file_format, ttl)

            except ValueError:
                # Thrown when the storage file is corrupted and can't be read.
                # recreate storage.
                log.error('Error storage "%s" from disk', name)
                os.remove(filename)
                storage = TimedStorage(filename, file_format, ttl)

            cls._unsynced_storages[filename] = storage
            log.debug('Loaded storage "%s" from disk', name)

        return storage
