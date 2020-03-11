# Copyright (c) 2011, SmartFile <btimby@smartfile.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the organization nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import stat
import sys
import time
import warnings

from libarchive import _libarchive
from io import StringIO

PY3 = sys.version_info[0] == 3

# Suggested block size for libarchive. Libarchive may adjust it.
BLOCK_SIZE = 10240

MTIME_FORMAT = ''

# Default encoding scheme.
ENCODING = 'utf-8'

# Functions to initialize read/write for various libarchive supported formats and filters.
FORMATS = {
    None: (_libarchive.archive_read_support_format_all, None),
    'tar': (_libarchive.archive_read_support_format_tar, _libarchive.archive_write_set_format_ustar),
    'pax': (_libarchive.archive_read_support_format_tar, _libarchive.archive_write_set_format_pax),
    'gnu': (_libarchive.archive_read_support_format_gnutar, _libarchive.archive_write_set_format_gnutar),
    'zip': (_libarchive.archive_read_support_format_zip, _libarchive.archive_write_set_format_zip),
    'rar': (_libarchive.archive_read_support_format_rar, None),
    '7zip': (_libarchive.archive_read_support_format_7zip, None),
    'ar': (_libarchive.archive_read_support_format_ar, None),
    'cab': (_libarchive.archive_read_support_format_cab, None),
    'cpio': (_libarchive.archive_read_support_format_cpio, _libarchive.archive_write_set_format_cpio_newc),
    'iso': (_libarchive.archive_read_support_format_iso9660, _libarchive.archive_write_set_format_iso9660),
    'lha': (_libarchive.archive_read_support_format_lha, None),
    'xar': (_libarchive.archive_read_support_format_xar, _libarchive.archive_write_set_format_xar),
}

FILTERS = {
    None: (_libarchive.archive_read_support_filter_all, _libarchive.archive_write_add_filter_none),
    'gz': (_libarchive.archive_read_support_filter_gzip, _libarchive.archive_write_add_filter_gzip),
    'bz2': (_libarchive.archive_read_support_filter_bzip2, _libarchive.archive_write_add_filter_bzip2),
}

# Map file extensions to formats and filters. To support quick detection.
FORMAT_EXTENSIONS = {
    '.tar': 'tar',
    '.zip': 'zip',
    '.rar': 'rar',
    '.7z': '7zip',
    '.ar': 'ar',
    '.cab': 'cab',
    '.rpm': 'cpio',
    '.cpio': 'cpio',
    '.iso': 'iso',
    '.lha': 'lha',
    '.xar': 'xar',
}
FILTER_EXTENSIONS = {
    '.gz': 'gz',
    '.bz2': 'bz2',
}


class EOF(Exception):
    '''Raised by ArchiveInfo.from_archive() when unable to read the next
    archive header.'''
    pass


def get_error(archive):
    '''Retrieves the last error description for the given archive instance.'''
    return _libarchive.archive_error_string(archive)


def call_and_check(func, archive, *args):
    '''Executes a libarchive function and raises an exception when appropriate.'''
    ret = func(*args)
    if ret == _libarchive.ARCHIVE_OK:
        return
    elif ret == _libarchive.ARCHIVE_WARN:
        warnings.warn('Warning executing function: %s.' % get_error(archive), RuntimeWarning)
    elif ret == _libarchive.ARCHIVE_EOF:
        raise EOF()
    else:
        raise Exception('Fatal error executing function, message is: %s.' % get_error(archive))


def get_func(name, items, index):
    item = items.get(name, None)
    if item is None:
        return None
    return item[index]


def guess_format(filename):
    if isinstance(filename, int):
        filename = ext = ''
    else:
        filename, ext = os.path.splitext(filename)
    filter = FILTER_EXTENSIONS.get(ext)
    if filter:
        filename, ext = os.path.splitext(filename)
    format = FORMAT_EXTENSIONS.get(ext)
    return format, filter


def is_archive_name(filename, formats=None):
    '''Quick check to see if the given file has an extension indiciating that it is
    an archive. The format parameter can be used to limit what archive format is acceptable.
    If omitted, all supported archive formats will be checked.

    This function will return the name of the most likely archive format, None if the file is
    unlikely to be an archive.'''
    if formats is None:
        formats = list(FORMAT_EXTENSIONS.values())
    format, filter = guess_format(filename)
    if format in formats:
        return format


def is_archive(f, formats=(None, ), filters=(None, )):
    '''Check to see if the given file is actually an archive. The format parameter
    can be used to specify which archive format is acceptable. If ommitted, all supported
    archive formats will be checked. It opens the file using libarchive. If no error is
    received, the file was successfully detected by the libarchive bidding process.

    This procedure is quite costly, so you should avoid calling it unless you are reasonably
    sure that the given file is an archive. In other words, you may wish to filter large
    numbers of file names using is_archive_name() before double-checking the positives with
    this function.

    This function will return True if the file can be opened as an archive using the given
    format(s)/filter(s).'''
    if isinstance(f, str):
        f = open(f, 'r')
    a = _libarchive.archive_read_new()
    for format in formats:
        format = get_func(format, FORMATS, 0)
        if format is None:
            return False
        format(a)
    for filter in filters:
        filter = get_func(filter, FILTERS, 0)
        if filter is None:
            return False
        filter(a)
    try:
        try:
            call_and_check(_libarchive.archive_read_open_fd, a, a, f.fileno(), BLOCK_SIZE)
            return True
        except:
            return False
    finally:
        _libarchive.archive_read_close(a)
        _libarchive.archive_read_free(a)
        f.close()


class EntryReadStream(object):
    '''A file-like object for reading an entry from the archive.'''
    def __init__(self, archive, size):
        self.archive = archive
        self.closed = False
        self.size = size
        self.bytes = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return

    def __iter__(self):
        if self.closed:
            return
        while True:
            data = self.read(BLOCK_SIZE)
            if not data:
                break
            yield data

    def __len__(self):
        return self.size

    def tell(self):
        return self.bytes

    def read(self, bytes=-1):
        if self.closed:
            return
        if self.bytes == self.size:
            # EOF already reached.
            return
        if bytes < 0:
            bytes = self.size - self.bytes
        elif self.bytes + bytes > self.size:
            # Limit read to remaining bytes
            bytes = self.size - self.bytes
        # Read requested bytes
        data = _libarchive.archive_read_data_into_str(self.archive._a, bytes)
        self.bytes += len(data)
        return data

    def close(self):
        if self.closed:
            return
        # Call archive.close() with _defer True to let it know we have been
        # closed and it is now safe to actually close.
        self.archive.close(_defer=True)
        self.archive = None
        self.closed = True


class EntryWriteStream(object):
    '''A file-like object for writing an entry to an archive.

    If the size is known ahead of time and provided, then the file contents
    are not buffered but flushed directly to the archive. If size is omitted,
    then the file contents are buffered and flushed in the close() method.'''
    def __init__(self, archive, pathname, size=None):
        self.archive = archive
        self.entry = Entry(pathname=pathname, mtime=time.time(), mode=stat.S_IFREG)
        if size is None:
            self.buffer = StringIO()
        else:
            self.buffer = None
            self.entry.size = size
            self.entry.to_archive(self.archive)
        self.bytes = 0
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __del__(self):
        self.close()

    def __len__(self):
        return self.bytes

    def tell(self):
        return self.bytes

    def write(self, data):
        if self.closed:
            raise Exception('Cannot write to closed stream.')
        if self.buffer:
            self.buffer.write(data)
        else:
            _libarchive.archive_write_data_from_str(self.archive._a, data.encode('utf-8'))
        self.bytes += len(data)

    def close(self):
        if self.closed:
            return
        if self.buffer:
            self.entry.size = self.buffer.tell()
            self.entry.to_archive(self.archive)
            _libarchive.archive_write_data_from_str(self.archive._a, self.buffer.getvalue().encode('utf-8'))
        _libarchive.archive_write_finish_entry(self.archive._a)

        # Call archive.close() with _defer True to let it know we have been
        # closed and it is now safe to actually close.
        self.archive.close(_defer=True)
        self.archive = None
        self.closed = True


class Entry(object):
    '''An entry within an archive. Represents the header data and it's location within the archive.'''
    def __init__(self, pathname=None, size=None, mtime=None, mode=None, hpos=None, encoding=ENCODING):
        self.pathname = pathname
        self.size = size
        self.mtime = mtime
        self.mode = mode
        self.hpos = hpos
        self.encoding = encoding

    @property
    def header_position(self):
        return self.hpos

    @classmethod
    def from_archive(cls, archive, encoding=ENCODING):
        '''Instantiates an Entry class and sets all the properties from an archive header.'''
        e = _libarchive.archive_entry_new()
        try:
            call_and_check(_libarchive.archive_read_next_header2, archive._a, archive._a, e)
            mode = _libarchive.archive_entry_filetype(e)
            mode |= _libarchive.archive_entry_perm(e)

            if PY3:
                pathname = _libarchive.archive_entry_pathname(e)
            else:
                pathname = _libarchive.archive_entry_pathname(e).decode(encoding)

            entry = cls(
                pathname=pathname,
                size=_libarchive.archive_entry_size(e),
                mtime=_libarchive.archive_entry_mtime(e),
                mode=mode,
                hpos=archive.header_position,
            )
        finally:
            _libarchive.archive_entry_free(e)
        return entry

    @classmethod
    def from_file(cls, f, entry=None, encoding=ENCODING):
        '''Instantiates an Entry class and sets all the properties from a file on the file system.
        f can be a file-like object or a path.'''
        if entry is None:
            entry = cls(encoding=encoding)
        if entry.pathname is None:
            if isinstance(f, str):
                st = os.stat(f)
                entry.pathname = f
                entry.size = st.st_size
                entry.mtime = st.st_mtime
                entry.mode = st.st_mode
            elif hasattr(f, 'fileno'):
                st = os.fstat(f.fileno())
                entry.pathname = getattr(f, 'name', None)
                entry.size = st.st_size
                entry.mtime = st.st_mtime
                entry.mode = st.st_mode
            else:
                entry.pathname = getattr(f, 'pathname', None)
                entry.size = getattr(f, 'size', 0)
                entry.mtime = getattr(f, 'mtime', time.time())
                entry.mode = stat.S_IFREG
        return entry

    def to_archive(self, archive):
        '''Creates an archive header and writes it to the given archive.'''
        e = _libarchive.archive_entry_new()
        try:
            if PY3:
                _libarchive.archive_entry_set_pathname(e, self.pathname)
            else:
                _libarchive.archive_entry_set_pathname(e, self.pathname.encode(self.encoding))
            _libarchive.archive_entry_set_filetype(e, stat.S_IFMT(self.mode))
            _libarchive.archive_entry_set_perm(e, stat.S_IMODE(self.mode))
            _libarchive.archive_entry_set_size(e, self.size)
            _libarchive.archive_entry_set_mtime(e, self.mtime, 0)
            call_and_check(_libarchive.archive_write_header, archive._a, archive._a, e)
            #self.hpos = archive.header_position
        finally:
            _libarchive.archive_entry_free(e)

    def isdir(self):
        return stat.S_ISDIR(self.mode)

    def isfile(self):
        return stat.S_ISREG(self.mode)

    def issym(self):
        return stat.S_ISLNK(self.mode)

    def isfifo(self):
        return stat.S_ISFIFO(self.mode)

    def ischr(self):
        return stat.S_ISCHR(self.mode)

    def isblk(self):
        return stat.S_ISBLK(self.mode)


class Archive(object):
    '''A low-level archive reader which provides forward-only iteration. Consider
    this a light-weight pythonic libarchive wrapper.'''
    def __init__(self, f, mode='r', format=None, filter=None, entry_class=Entry, encoding=ENCODING, blocksize=BLOCK_SIZE):
        assert mode in ('r', 'w', 'wb', 'a'), 'Mode should be "r", "w", "wb", or "a".'
        self._stream = None
        self.encoding = encoding
        self.blocksize = blocksize
        if isinstance(f, str):
            self.filename = f
            f = open(f, mode)
            # Only close it if we opened it...
            self._defer_close = True
        elif hasattr(f, 'fileno'):
            self.filename = getattr(f, 'name', None)
            # Leave the fd alone, caller should manage it...
            self._defer_close = False
        else:
            raise Exception('Provided file is not path or open file.')
        self.f = f
        self.mode = mode
        # Guess the format/filter from file name (if not provided)
        if self.filename:
            if format is None:
                format = guess_format(self.filename)[0]
            if filter is None:
                filter = guess_format(self.filename)[1]
        self.format = format
        self.filter = filter
        # The class to use for entries.
        self.entry_class = entry_class
        # Select filter/format functions.
        if self.mode == 'r':
            self.format_func = get_func(self.format, FORMATS, 0)
            if self.format_func is None:
                raise Exception('Unsupported format %s' % format)
            self.filter_func = get_func(self.filter, FILTERS, 0)
            if self.filter_func is None:
                raise Exception('Unsupported filter %s' % filter)
        else:
            # TODO: how to support appending?
            if self.format is None:
                raise Exception('You must specify a format for writing.')
            self.format_func = get_func(self.format, FORMATS, 1)
            if self.format_func is None:
                raise Exception('Unsupported format %s' % format)
            self.filter_func = get_func(self.filter, FILTERS, 1)
            if self.filter_func is None:
                raise Exception('Unsupported filter %s' % filter)
        # Open the archive, apply filter/format functions.
        self.init()

    def __iter__(self):
        while True:
            try:
                yield self.entry_class.from_archive(self, encoding=self.encoding)
            except EOF:
                break

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.denit()

    def __del__(self):
        self.close()

    def init(self):
        if self.mode == 'r':
            self._a = _libarchive.archive_read_new()
        else:
            self._a = _libarchive.archive_write_new()
        self.format_func(self._a)
        self.filter_func(self._a)
        if self.mode == 'r':
            call_and_check(_libarchive.archive_read_open_fd, self._a, self._a, self.f.fileno(), self.blocksize)
        else:
            call_and_check(_libarchive.archive_write_open_fd, self._a, self._a, self.f.fileno())

    def denit(self):
        '''Closes and deallocates the archive reader/writer.'''
        if getattr(self, '_a', None) is None:
            return
        try:
            if self.mode == 'r':
                _libarchive.archive_read_close(self._a)
                _libarchive.archive_read_free(self._a)
            elif self.mode == 'w':
                _libarchive.archive_write_close(self._a)
                _libarchive.archive_write_free(self._a)
        finally:
            # We only want one try at this...
            self._a = None

    def close(self, _defer=False):
        # _defer == True is how a stream can notify Archive that the stream is
        # now closed.  Calling it directly in not recommended.
        if _defer:
            # This call came from our open stream.
            self._stream = None
            if not self._defer_close:
                # We are not yet ready to close.
                return
        if self._stream is not None:
            # We have a stream open! don't close, but remember we were asked to.
            self._defer_close = True
            return
        self.denit()
        # If there is a file attached...
        if hasattr(self, 'f'):
            # Make sure it is not already closed...
            if getattr(self.f, 'closed', False):
                return
            # Flush it if not read-only...
            if self.f.mode != 'r' and self.f.mode != 'rb':
                self.f.flush()
                os.fsync(self.f.fileno())
            # and then close it, if we opened it...
            if getattr(self, '_close', None):
                self.f.close()

    @property
    def header_position(self):
        '''The position within the file.'''
        return _libarchive.archive_read_header_position(self._a)

    def iterpaths(self):
        for entry in self:
            yield entry.pathname

    def read(self, size):
        '''Read current archive entry contents into string.'''
        return _libarchive.archive_read_data_into_str(self._a, size)

    def readpath(self, f):
        '''Write current archive entry contents to file. f can be a file-like object or
        a path.'''
        if isinstance(f, str):
            basedir = os.path.basename(f)
            if not os.path.exists(basedir):
                os.makedirs(basedir)
            f = open(f, 'w')
        return _libarchive.archive_read_data_into_fd(self._a, f.fileno())

    def readstream(self, size):
        '''Returns a file-like object for reading current archive entry contents.'''
        self._stream = EntryReadStream(self, size)
        return self._stream

    def write(self, member, data=None):
        '''Writes a string buffer to the archive as the given entry.'''
        if isinstance(member, str):
            member = self.entry_class(pathname=member, encoding=self.encoding)
        if data:
            member.size = len(data)
        member.to_archive(self)

        if data:
            if PY3:
                if isinstance(data, bytes):
                    result = _libarchive.archive_write_data_from_str(self._a, data)
                else:
                    result = _libarchive.archive_write_data_from_str(self._a, data.encode('utf8'))
            else:
                result = _libarchive.archive_write_data_from_str(self._a, data)
        _libarchive.archive_write_finish_entry(self._a)

    def writepath(self, f, pathname=None, folder=False):
        '''Writes a file to the archive. f can be a file-like object or a path. Uses
        write() to do the actual writing.'''
        member = self.entry_class.from_file(f, encoding=self.encoding)
        if isinstance(f, str):
            if os.path.isfile(f):
                f = open(f, 'r')
        if pathname:
            member.pathname = pathname
        if folder and not member.isdir():
            member.mode = stat.S_IFDIR

        if hasattr(f, 'read'):
            # TODO: optimize this to write directly from f to archive.
            self.write(member, data=f.read())
        else:
            self.write(member)

    def writestream(self, pathname, size=None):
        '''Returns a file-like object for writing a new entry.'''
        self._stream = EntryWriteStream(self, pathname, size)
        return self._stream

    def printlist(self, s=sys.stdout):
        for entry in self:
            s.write(entry.size)
            s.write('\t')
            s.write(entry.mtime.strftime(MTIME_FORMAT))
            s.write('\t')
            s.write(entry.pathname)
        s.flush()


class SeekableArchive(Archive):
    '''A class that provides random-access to archive entries. It does this by using one
    or many Archive instances to seek to the correct location. The best performance will
    occur when reading archive entries in the order in which they appear in the archive.
    Reading out of order will cause the archive to be closed and opened each time a
    reverse seek is needed.'''
    def __init__(self, f, **kwargs):
        self._stream = None
        # Convert file to open file. We need this to reopen the archive.
        mode = kwargs.setdefault('mode', 'r')
        if isinstance(f, str):
            f = open(f, mode)
        super(SeekableArchive, self).__init__(f, **kwargs)
        self.entries = []
        self.eof = False

    def __iter__(self):
        for entry in self.entries:
            yield entry
        if not self.eof:
            try:
                for entry in super(SeekableArchive, self).__iter__():
                    self.entries.append(entry)
                    yield entry
            except StopIteration:
                self.eof = True

    def reopen(self):
        '''Seeks the underlying fd to 0 position, then opens the archive. If the archive
        is already open, this will effectively re-open it (rewind to the beginning).'''
        self.denit()
        self.f.seek(0)
        self.init()

    def getentry(self, pathname):
        '''Take a name or entry object and returns an entry object.'''
        for entry in self:
            if entry.pathname == pathname:
                return entry
        raise KeyError(pathname)

    def seek(self, entry):
        '''Seeks the archive to the requested entry. Will reopen if necessary.'''
        move = entry.header_position - self.header_position
        if move != 0:
            if move < 0:
                # can't move back, re-open archive:
                self.reopen()
            # move to proper position in stream
            for curr in super(SeekableArchive, self).__iter__():
                if curr.header_position == entry.header_position:
                    break

    def read(self, member):
        '''Return the requested archive entry contents as a string.'''
        entry = self.getentry(member)
        self.seek(entry)
        return super(SeekableArchive, self).read(entry.size)

    def readpath(self, member, f):
        entry = self.getentry(member)
        self.seek(entry)
        return super(SeekableArchive, self).readpath(f)

    def readstream(self, member):
        '''Returns a file-like object for reading requested archive entry contents.'''
        entry = self.getentry(member)
        self.seek(entry)
        self._stream = EntryReadStream(self, entry.size)
        return self._stream
