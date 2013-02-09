# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 The Python Software Foundation.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
from __future__ import absolute_import

import os
import re
import sys

if sys.version_info[0] < 3:
    from StringIO import StringIO
    string_types = basestring,
    text_type = unicode
    from types import FileType as file_type
    import __builtin__ as builtins
    import ConfigParser as configparser
    from ._backport import shutil
    from urlparse import urlparse, urlunparse, urljoin, urlsplit, urlunsplit
    from urllib import (urlretrieve, quote as _quote, unquote, url2pathname,
                        pathname2url, ContentTooShortError)

    def quote(s):
        if isinstance(s, unicode):
            s = s.encode('utf-8')
        return _quote(s)

    import urllib2
    from urllib2 import (Request, urlopen, URLError, HTTPError,
                         HTTPBasicAuthHandler, HTTPPasswordMgr,
                         HTTPSHandler, HTTPHandler, build_opener)
    import httplib
    import xmlrpclib
    import Queue as queue
    from HTMLParser import HTMLParser
    import htmlentitydefs
    raw_input = raw_input
    from itertools import ifilter as filter
    from itertools import ifilterfalse as filterfalse

    _userprog = None
    def splituser(host):
        """splituser('user[:passwd]@host[:port]') --> 'user[:passwd]', 'host[:port]'."""
        global _userprog
        if _userprog is None:
            import re
            _userprog = re.compile('^(.*)@(.*)$')

        match = _userprog.match(host)
        if match: return match.group(1, 2)
        return None, host

    class CertificateError(ValueError):
        pass


    def _dnsname_to_pat(dn):
        pats = []
        for frag in dn.split(r'.'):
            if frag == '*':
                # When '*' is a fragment by itself, it matches a non-empty
                # dotless fragment.
                pats.append('[^.]+')
            else:
                # Otherwise, '*' matches any dotless fragment.
                frag = re.escape(frag)
                pats.append(frag.replace(r'\*', '[^.]*'))
        return re.compile(r'\A' + r'\.'.join(pats) + r'\Z', re.IGNORECASE)


    def match_hostname(cert, hostname):
        """Verify that *cert* (in decoded format as returned by
        SSLSocket.getpeercert()) matches the *hostname*.  RFC 2818 rules
        are mostly followed, but IP addresses are not accepted for *hostname*.

        CertificateError is raised on failure. On success, the function
        returns nothing.
        """
        if not cert:
            raise ValueError("empty or no certificate")
        dnsnames = []
        san = cert.get('subjectAltName', ())
        for key, value in san:
            if key == 'DNS':
                if _dnsname_to_pat(value).match(hostname):
                    return
                dnsnames.append(value)
        if not dnsnames:
            # The subject is only checked when there is no dNSName entry
            # in subjectAltName
            for sub in cert.get('subject', ()):
                for key, value in sub:
                    # XXX according to RFC 2818, the most specific Common Name
                    # must be used.
                    if key == 'commonName':
                        if _dnsname_to_pat(value).match(hostname):
                            return
                        dnsnames.append(value)
        if len(dnsnames) > 1:
            raise CertificateError("hostname %r "
                "doesn't match either of %s"
                % (hostname, ', '.join(map(repr, dnsnames))))
        elif len(dnsnames) == 1:
            raise CertificateError("hostname %r "
                "doesn't match %r"
                % (hostname, dnsnames[0]))
        else:
            raise CertificateError("no appropriate commonName or "
                "subjectAltName fields were found")


else:
    from io import StringIO
    string_types = str,
    text_type = str
    from io import TextIOWrapper as file_type
    import builtins
    import configparser
    import shutil
    from urllib.parse import (urlparse, urlunparse, urljoin, splituser, quote,
                              unquote, urlsplit, urlunsplit)
    from urllib.request import (urlopen, urlretrieve, Request, url2pathname,
                                pathname2url,
                                HTTPBasicAuthHandler, HTTPPasswordMgr,
                                HTTPSHandler, HTTPHandler, build_opener)
    from urllib.error import HTTPError, URLError, ContentTooShortError
    import http.client as httplib
    import urllib.request as urllib2
    import xmlrpc.client as xmlrpclib
    import queue
    from html.parser import HTMLParser
    import html.entities as htmlentitydefs
    raw_input = input
    from itertools import filterfalse
    filter = filter

    from ssl import match_hostname, CertificateError

try:
    from platform import python_implementation
except ImportError: # pragma: no cover
    def python_implementation():
        """Return a string identifying the Python implementation."""
        if 'PyPy' in sys.version:
            return 'PyPy'
        if os.name == 'java':
            return 'Jython'
        if sys.version.startswith('IronPython'):
            return 'IronPython'
        return 'CPython'

try:
    import sysconfig
except ImportError: # pragma: no cover
    from ._backport import sysconfig

try:
    callable = callable
except NameError:   # pragma: no cover
    from collections import Callable

    def callable(obj):
        return isinstance(obj, Callable)


try:
    fsencode = os.fsencode
except AttributeError:  # pragma: no cover
    def fsencode(filename):
        if isinstance(filename, bytes):
            return filename
        elif isinstance(filename, str):
            return filename.encode(sys.getfilesystemencoding())
        else:
            raise TypeError("expect bytes or str, not %s" %
                            type(filename).__name__)

try:
    from tokenize import detect_encoding
except ImportError: # pragma: no cover
    from codecs import BOM_UTF8, lookup
    import re

    cookie_re = re.compile("coding[:=]\s*([-\w.]+)")

    def _get_normal_name(orig_enc):
        """Imitates get_normal_name in tokenizer.c."""
        # Only care about the first 12 characters.
        enc = orig_enc[:12].lower().replace("_", "-")
        if enc == "utf-8" or enc.startswith("utf-8-"):
            return "utf-8"
        if enc in ("latin-1", "iso-8859-1", "iso-latin-1") or \
           enc.startswith(("latin-1-", "iso-8859-1-", "iso-latin-1-")):
            return "iso-8859-1"
        return orig_enc

    def detect_encoding(readline):
        """
        The detect_encoding() function is used to detect the encoding that should
        be used to decode a Python source file.  It requires one argment, readline,
        in the same way as the tokenize() generator.

        It will call readline a maximum of twice, and return the encoding used
        (as a string) and a list of any lines (left as bytes) it has read in.

        It detects the encoding from the presence of a utf-8 bom or an encoding
        cookie as specified in pep-0263.  If both a bom and a cookie are present,
        but disagree, a SyntaxError will be raised.  If the encoding cookie is an
        invalid charset, raise a SyntaxError.  Note that if a utf-8 bom is found,
        'utf-8-sig' is returned.

        If no encoding is specified, then the default of 'utf-8' will be returned.
        """
        try:
            filename = readline.__self__.name
        except AttributeError:
            filename = None
        bom_found = False
        encoding = None
        default = 'utf-8'
        def read_or_stop():
            try:
                return readline()
            except StopIteration:
                return b''

        def find_cookie(line):
            try:
                # Decode as UTF-8. Either the line is an encoding declaration,
                # in which case it should be pure ASCII, or it must be UTF-8
                # per default encoding.
                line_string = line.decode('utf-8')
            except UnicodeDecodeError:
                msg = "invalid or missing encoding declaration"
                if filename is not None:
                    msg = '{} for {!r}'.format(msg, filename)
                raise SyntaxError(msg)

            matches = cookie_re.findall(line_string)
            if not matches:
                return None
            encoding = _get_normal_name(matches[0])
            try:
                codec = lookup(encoding)
            except LookupError:
                # This behaviour mimics the Python interpreter
                if filename is None:
                    msg = "unknown encoding: " + encoding
                else:
                    msg = "unknown encoding for {!r}: {}".format(filename,
                            encoding)
                raise SyntaxError(msg)

            if bom_found:
                if codec.name != 'utf-8':
                    # This behaviour mimics the Python interpreter
                    if filename is None:
                        msg = 'encoding problem: utf-8'
                    else:
                        msg = 'encoding problem for {!r}: utf-8'.format(filename)
                    raise SyntaxError(msg)
                encoding += '-sig'
            return encoding

        first = read_or_stop()
        if first.startswith(BOM_UTF8):
            bom_found = True
            first = first[3:]
            default = 'utf-8-sig'
        if not first:
            return default, []

        encoding = find_cookie(first)
        if encoding:
            return encoding, [first]

        second = read_or_stop()
        if not second:
            return default, [first]

        encoding = find_cookie(second)
        if encoding:
            return encoding, [first, second]

        return default, [first, second]

# For converting & <-> &amp; etc.
try:
    from html import escape
except ImportError:
    from cgi import escape
unescape = HTMLParser().unescape

try:
    from collections import ChainMap
except ImportError: # pragma: no cover
    from collections import MutableMapping

    try:
        from reprlib import recursive_repr as _recursive_repr
    except ImportError:
        def _recursive_repr(fillvalue='...'):
            '''
            Decorator to make a repr function return fillvalue for a recursive
            call
            '''

            def decorating_function(user_function):
                repr_running = set()

                def wrapper(self):
                    key = id(self), get_ident()
                    if key in repr_running:
                        return fillvalue
                    repr_running.add(key)
                    try:
                        result = user_function(self)
                    finally:
                        repr_running.discard(key)
                    return result

                # Can't use functools.wraps() here because of bootstrap issues
                wrapper.__module__ = getattr(user_function, '__module__')
                wrapper.__doc__ = getattr(user_function, '__doc__')
                wrapper.__name__ = getattr(user_function, '__name__')
                wrapper.__annotations__ = getattr(user_function, '__annotations__', {})
                return wrapper

            return decorating_function

    class ChainMap(MutableMapping):
        ''' A ChainMap groups multiple dicts (or other mappings) together
        to create a single, updateable view.

        The underlying mappings are stored in a list.  That list is public and can
        accessed or updated using the *maps* attribute.  There is no other state.

        Lookups search the underlying mappings successively until a key is found.
        In contrast, writes, updates, and deletions only operate on the first
        mapping.

        '''

        def __init__(self, *maps):
            '''Initialize a ChainMap by setting *maps* to the given mappings.
            If no mappings are provided, a single empty dictionary is used.

            '''
            self.maps = list(maps) or [{}]          # always at least one map

        def __missing__(self, key):
            raise KeyError(key)

        def __getitem__(self, key):
            for mapping in self.maps:
                try:
                    return mapping[key]             # can't use 'key in mapping' with defaultdict
                except KeyError:
                    pass
            return self.__missing__(key)            # support subclasses that define __missing__

        def get(self, key, default=None):
            return self[key] if key in self else default

        def __len__(self):
            return len(set().union(*self.maps))     # reuses stored hash values if possible

        def __iter__(self):
            return iter(set().union(*self.maps))

        def __contains__(self, key):
            return any(key in m for m in self.maps)

        def __bool__(self):
            return any(self.maps)

        @_recursive_repr()
        def __repr__(self):
            return '{0.__class__.__name__}({1})'.format(
                self, ', '.join(map(repr, self.maps)))

        @classmethod
        def fromkeys(cls, iterable, *args):
            'Create a ChainMap with a single dict created from the iterable.'
            return cls(dict.fromkeys(iterable, *args))

        def copy(self):
            'New ChainMap or subclass with a new copy of maps[0] and refs to maps[1:]'
            return self.__class__(self.maps[0].copy(), *self.maps[1:])

        __copy__ = copy

        def new_child(self):                        # like Django's Context.push()
            'New ChainMap with a new dict followed by all previous maps.'
            return self.__class__({}, *self.maps)

        @property
        def parents(self):                          # like Django's Context.pop()
            'New ChainMap from maps[1:].'
            return self.__class__(*self.maps[1:])

        def __setitem__(self, key, value):
            self.maps[0][key] = value

        def __delitem__(self, key):
            try:
                del self.maps[0][key]
            except KeyError:
                raise KeyError('Key not found in the first mapping: {!r}'.format(key))

        def popitem(self):
            'Remove and return an item pair from maps[0]. Raise KeyError is maps[0] is empty.'
            try:
                return self.maps[0].popitem()
            except KeyError:
                raise KeyError('No keys found in the first mapping.')

        def pop(self, key, *args):
            'Remove *key* from maps[0] and return its value. Raise KeyError if *key* not in maps[0].'
            try:
                return self.maps[0].pop(key, *args)
            except KeyError:
                raise KeyError('Key not found in the first mapping: {!r}'.format(key))

        def clear(self):
            'Clear maps[0], leaving maps[1:] intact.'
            self.maps[0].clear()

try:
    from imp import cache_from_source
except ImportError: # pragma: no cover
    def cache_from_source(path, debug_override=None):
        assert path.endswith('.py')
        if debug_override is None:
            debug_override = __debug__
        if debug_override:
            suffix = 'c'
        else:
            suffix = 'o'
        return path + suffix

try:
    from collections import OrderedDict
except ImportError: # pragma: no cover
## {{{ http://code.activestate.com/recipes/576693/ (r9)
# Backport of OrderedDict() class that runs on Python 2.4, 2.5, 2.6, 2.7 and pypy.
# Passes Python2.7's test suite and incorporates all the latest updates.
    try:
        from thread import get_ident as _get_ident
    except ImportError:
        from dummy_thread import get_ident as _get_ident

    try:
        from _abcoll import KeysView, ValuesView, ItemsView
    except ImportError:
        pass


    class OrderedDict(dict):
        'Dictionary that remembers insertion order'
        # An inherited dict maps keys to values.
        # The inherited dict provides __getitem__, __len__, __contains__, and get.
        # The remaining methods are order-aware.
        # Big-O running times for all methods are the same as for regular dictionaries.

        # The internal self.__map dictionary maps keys to links in a doubly linked list.
        # The circular doubly linked list starts and ends with a sentinel element.
        # The sentinel element never gets deleted (this simplifies the algorithm).
        # Each link is stored as a list of length three:  [PREV, NEXT, KEY].

        def __init__(self, *args, **kwds):
            '''Initialize an ordered dictionary.  Signature is the same as for
            regular dictionaries, but keyword arguments are not recommended
            because their insertion order is arbitrary.

            '''
            if len(args) > 1:
                raise TypeError('expected at most 1 arguments, got %d' % len(args))
            try:
                self.__root
            except AttributeError:
                self.__root = root = []                     # sentinel node
                root[:] = [root, root, None]
                self.__map = {}
            self.__update(*args, **kwds)

        def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
            'od.__setitem__(i, y) <==> od[i]=y'
            # Setting a new item creates a new link which goes at the end of the linked
            # list, and the inherited dictionary is updated with the new key/value pair.
            if key not in self:
                root = self.__root
                last = root[0]
                last[1] = root[0] = self.__map[key] = [last, root, key]
            dict_setitem(self, key, value)

        def __delitem__(self, key, dict_delitem=dict.__delitem__):
            'od.__delitem__(y) <==> del od[y]'
            # Deleting an existing item uses self.__map to find the link which is
            # then removed by updating the links in the predecessor and successor nodes.
            dict_delitem(self, key)
            link_prev, link_next, key = self.__map.pop(key)
            link_prev[1] = link_next
            link_next[0] = link_prev

        def __iter__(self):
            'od.__iter__() <==> iter(od)'
            root = self.__root
            curr = root[1]
            while curr is not root:
                yield curr[2]
                curr = curr[1]

        def __reversed__(self):
            'od.__reversed__() <==> reversed(od)'
            root = self.__root
            curr = root[0]
            while curr is not root:
                yield curr[2]
                curr = curr[0]

        def clear(self):
            'od.clear() -> None.  Remove all items from od.'
            try:
                for node in self.__map.itervalues():
                    del node[:]
                root = self.__root
                root[:] = [root, root, None]
                self.__map.clear()
            except AttributeError:
                pass
            dict.clear(self)

        def popitem(self, last=True):
            '''od.popitem() -> (k, v), return and remove a (key, value) pair.
            Pairs are returned in LIFO order if last is true or FIFO order if false.

            '''
            if not self:
                raise KeyError('dictionary is empty')
            root = self.__root
            if last:
                link = root[0]
                link_prev = link[0]
                link_prev[1] = root
                root[0] = link_prev
            else:
                link = root[1]
                link_next = link[1]
                root[1] = link_next
                link_next[0] = root
            key = link[2]
            del self.__map[key]
            value = dict.pop(self, key)
            return key, value

        # -- the following methods do not depend on the internal structure --

        def keys(self):
            'od.keys() -> list of keys in od'
            return list(self)

        def values(self):
            'od.values() -> list of values in od'
            return [self[key] for key in self]

        def items(self):
            'od.items() -> list of (key, value) pairs in od'
            return [(key, self[key]) for key in self]

        def iterkeys(self):
            'od.iterkeys() -> an iterator over the keys in od'
            return iter(self)

        def itervalues(self):
            'od.itervalues -> an iterator over the values in od'
            for k in self:
                yield self[k]

        def iteritems(self):
            'od.iteritems -> an iterator over the (key, value) items in od'
            for k in self:
                yield (k, self[k])

        def update(*args, **kwds):
            '''od.update(E, **F) -> None.  Update od from dict/iterable E and F.

            If E is a dict instance, does:           for k in E: od[k] = E[k]
            If E has a .keys() method, does:         for k in E.keys(): od[k] = E[k]
            Or if E is an iterable of items, does:   for k, v in E: od[k] = v
            In either case, this is followed by:     for k, v in F.items(): od[k] = v

            '''
            if len(args) > 2:
                raise TypeError('update() takes at most 2 positional '
                                'arguments (%d given)' % (len(args),))
            elif not args:
                raise TypeError('update() takes at least 1 argument (0 given)')
            self = args[0]
            # Make progressively weaker assumptions about "other"
            other = ()
            if len(args) == 2:
                other = args[1]
            if isinstance(other, dict):
                for key in other:
                    self[key] = other[key]
            elif hasattr(other, 'keys'):
                for key in other.keys():
                    self[key] = other[key]
            else:
                for key, value in other:
                    self[key] = value
            for key, value in kwds.items():
                self[key] = value

        __update = update  # let subclasses override update without breaking __init__

        __marker = object()

        def pop(self, key, default=__marker):
            '''od.pop(k[,d]) -> v, remove specified key and return the corresponding value.
            If key is not found, d is returned if given, otherwise KeyError is raised.

            '''
            if key in self:
                result = self[key]
                del self[key]
                return result
            if default is self.__marker:
                raise KeyError(key)
            return default

        def setdefault(self, key, default=None):
            'od.setdefault(k[,d]) -> od.get(k,d), also set od[k]=d if k not in od'
            if key in self:
                return self[key]
            self[key] = default
            return default

        def __repr__(self, _repr_running=None):
            'od.__repr__() <==> repr(od)'
            if not _repr_running: _repr_running = {}
            call_key = id(self), _get_ident()
            if call_key in _repr_running:
                return '...'
            _repr_running[call_key] = 1
            try:
                if not self:
                    return '%s()' % (self.__class__.__name__,)
                return '%s(%r)' % (self.__class__.__name__, self.items())
            finally:
                del _repr_running[call_key]

        def __reduce__(self):
            'Return state information for pickling'
            items = [[k, self[k]] for k in self]
            inst_dict = vars(self).copy()
            for k in vars(OrderedDict()):
                inst_dict.pop(k, None)
            if inst_dict:
                return (self.__class__, (items,), inst_dict)
            return self.__class__, (items,)

        def copy(self):
            'od.copy() -> a shallow copy of od'
            return self.__class__(self)

        @classmethod
        def fromkeys(cls, iterable, value=None):
            '''OD.fromkeys(S[, v]) -> New ordered dictionary with keys from S
            and values equal to v (which defaults to None).

            '''
            d = cls()
            for key in iterable:
                d[key] = value
            return d

        def __eq__(self, other):
            '''od.__eq__(y) <==> od==y.  Comparison to another OD is order-sensitive
            while comparison to a regular mapping is order-insensitive.

            '''
            if isinstance(other, OrderedDict):
                return len(self)==len(other) and self.items() == other.items()
            return dict.__eq__(self, other)

        def __ne__(self, other):
            return not self == other

        # -- the following methods are only used in Python 2.7 --

        def viewkeys(self):
            "od.viewkeys() -> a set-like object providing a view on od's keys"
            return KeysView(self)

        def viewvalues(self):
            "od.viewvalues() -> an object providing a view on od's values"
            return ValuesView(self)

        def viewitems(self):
            "od.viewitems() -> a set-like object providing a view on od's items"
            return ItemsView(self)
