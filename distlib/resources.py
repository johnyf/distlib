# -*- coding: utf-8 -*-
#
# Copyright (C) 2013 Vinay Sajip.
# Licensed to the Python Software Foundation under a contributor agreement.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
from __future__ import unicode_literals

import bisect
import io
import logging
import os
import shutil
import sys
import zipimport

from . import DistlibException
from .util import cached_property, get_cache_base, path_to_cache_dir

logger = logging.getLogger(__name__)

class Cache(object):
    """
    A class implementing a cache for resources that need to live in the file system
    e.g. shared libraries.
    """

    def __init__(self, base=None):
        """
        Initialise an instance.

        :param base: The base directory where the cache should be located. If
                     not specified, this will be the ``resource-cache``
                     directory under whatever :func:`get_cache_base` returns.
        """
        if base is None:
            base = os.path.join(get_cache_base(), 'resource-cache')
            # we use 'isdir' instead of 'exists', because we want to
            # fail if there's a file with that name
            if not os.path.isdir(base):
                os.makedirs(base)
        self.base = os.path.abspath(os.path.normpath(base))

    def prefix_to_dir(self, prefix):
        """
        Converts a resource prefix to a directory name in the cache.
        """
        return path_to_cache_dir(prefix)

    def is_stale(self, resource, path):
        """
        Is the cache stale for the given resource?

        :param resource: The :class:`Resource` being cached.
        :param path: The path of the resource in the cache.
        :return: True if the cache is stale.
        """
        # Cache invalidation is a hard problem :-)
        return True

    def get(self, resource):
        """
        Get a resource into the cache,

        :param resource: A :class:`Resource` instance.
        :return: The pathname of the resource in the cache.
        """
        prefix, path = resource.finder.get_cache_info(resource)
        if prefix is None:
            result = path
        else:
            result = os.path.join(self.base, self.prefix_to_dir(prefix), path)
            dirname = os.path.dirname(result)
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            if not os.path.exists(result):
                stale = True
            else:
                stale = self.is_stale(resource, path)
            if stale:
                # write the bytes of the resource to the cache location
                with open(result, 'wb') as f:
                    f.write(resource.bytes)
        return result

    def clear(self):
        """
        Clear the cache.
        """
        not_removed = []
        for fn in os.listdir(self.base):
            fn = os.path.join(self.base, fn)
            try:
                if os.path.islink(fn) or os.path.isfile(fn):
                    os.remove(fn)
                elif os.path.isdir(fn):
                    shutil.rmtree(fn)
            except Exception:
                not_removed.append(fn)
        return not_removed

cache = Cache()

class ResourceBase(object):
    def __init__(self, finder, name):
        self.finder = finder
        self.name = name

class Resource(ResourceBase):
    """
    A class representing an in-package resource, such as a data file. This is
    not normally instantiated by user code, but rather by a
    :class:`ResourceFinder` which manages the resource.
    """
    is_container = False # Backwards compatibility

    def as_stream(self):
        "Get the resource as a stream. Not a property, as not idempotent."
        return self.finder.get_stream(self)

    @cached_property
    def file_path(self):
        return cache.get(self)

    @cached_property
    def bytes(self):
        return self.finder.get_bytes(self)

    @cached_property
    def size(self):
        return self.finder.get_size(self)

class ResourceContainer(ResourceBase):
    is_container = True # Backwards compatibility

    @cached_property
    def resources(self):
        return self.finder.get_resources(self)

class ResourceFinder(object):
    """
    Resource finder for file system resources.
    """
    def __init__(self, module):
        self.module = module
        self.loader = getattr(module, '__loader__', None)
        self.base = os.path.dirname(getattr(module, '__file__', ''))

    def _make_path(self, resource_name):
        parts = resource_name.split('/')
        parts.insert(0, self.base)
        return os.path.join(*parts)

    def _find(self, path):
        return os.path.exists(path)

    def get_cache_info(self, resource):
        return None, resource.path

    def find(self, resource_name):
        path = self._make_path(resource_name)
        if not self._find(path):
            result = None
        else:
            if self._is_directory(path):
                result = ResourceContainer(self, resource_name)
            else:
                result = Resource(self, resource_name)
            result.path = path
        return result

    def get_stream(self, resource):
        return open(resource.path, 'rb')

    def get_bytes(self, resource):
        with open(resource.path, 'rb') as f:
            return f.read()

    def get_size(self, resource):
        return os.path.getsize(resource.path)

    def get_resources(self, resource):
        def allowed(f):
            return f != '__pycache__' and not f.endswith(('.pyc', '.pyo'))
        return set([f for f in os.listdir(resource.path) if allowed(f)])

    def is_container(self, resource):
        return self._is_directory(resource.path)

    _is_directory = staticmethod(os.path.isdir)

class ZipResourceFinder(ResourceFinder):
    """
    Resource finder for resources in .zip files.
    """
    def __init__(self, module):
        super(ZipResourceFinder, self).__init__(module)
        archive = self.loader.archive
        self.prefix_len = 1 + len(archive)
        # PyPy doesn't have a _files attr on zipimporter, and you can't set one
        if hasattr(self.loader, '_files'):
            self._files = self.loader._files
        else:
            self._files = zipimport._zip_directory_cache[archive]
        self.index = sorted(self._files)

    def _find(self, path):
        path = path[self.prefix_len:]
        if path in self._files:
            result = True
        else:
            if path[-1] != os.sep:
                path = path + os.sep
            i = bisect.bisect(self.index, path)
            try:
                result = self.index[i].startswith(path)
            except IndexError:
                result = False
        if not result:
            logger.debug('_find failed: %r %r', path, self.loader.prefix)
        else:
            logger.debug('_find worked: %r %r', path, self.loader.prefix)
        return result

    def get_cache_info(self, resource):
        prefix = self.loader.archive
        path = resource.path[1 + len(prefix):]
        return prefix, path

    def get_bytes(self, resource):
        return self.loader.get_data(resource.path)

    def get_stream(self, resource):
        return io.BytesIO(self.get_bytes(resource))

    def get_size(self, resource):
        path = resource.path[self.prefix_len:]
        return self._files[path][3]

    def get_resources(self, resource):
        path = resource.path[self.prefix_len:]
        if path[-1] != os.sep:
            path += os.sep
        plen = len(path)
        result = set()
        i = bisect.bisect(self.index, path)
        while i < len(self.index):
            if not self.index[i].startswith(path):
                break
            s = self.index[i][plen:]
            result.add(s.split(os.sep, 1)[0])   # only immediate children
            i += 1
        return result

    def _is_directory(self, path):
        path = path[self.prefix_len:]
        if path[-1] != os.sep:
            path += os.sep
        i = bisect.bisect(self.index, path)
        try:
            result = self.index[i].startswith(path)
        except IndexError:
            result = False
        return result

_finder_registry = {
    type(None): ResourceFinder,
    zipimport.zipimporter: ZipResourceFinder
}

try:
    import _frozen_importlib
    _finder_registry[_frozen_importlib.SourceFileLoader] = ResourceFinder
except (ImportError, AttributeError):
    pass

def register_finder(loader, finder_maker):
    _finder_registry[type(loader)] = finder_maker

_finder_cache = {}

def finder(package):
    """
    Return a resource finder for a package.
    :param package: The name of the package.
    :return: A :class:`ResourceFinder` instance for the package.
    """
    if package in _finder_cache:
        result = _finder_cache[package]
    else:
        if package not in sys.modules:
            __import__(package)
        module = sys.modules[package]
        path = getattr(module, '__path__', None)
        if path is None:
            raise DistlibException('You cannot get a finder for a module, '
                                   'only for a package')
        loader = getattr(module, '__loader__', None)
        finder_maker = _finder_registry.get(type(loader))
        if finder_maker is None:
            raise DistlibException('Unable to locate finder for %r' % package)
        result = finder_maker(module)
        _finder_cache[package] = result
    return result
