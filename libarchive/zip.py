import os, time
from libarchive import is_archive, Entry, SeekableArchive
from zipfile import ZIP_STORED, ZIP_DEFLATED


def is_zipfile(filename):
    return is_archive(filename, formats=('zip', ))


class ZipEntry(Entry):
    def __init__(self, *args, **kwargs):
        super(ZipEntry, self).__init__(*args, **kwargs)

    def get_filename(self):
        return self.pathname

    def set_filename(self, value):
        self.pathname = value

    filename = property(get_filename, set_filename)

    def get_file_size(self):
        return self.size

    def set_file_size(self, value):
        assert isinstance(value, int), 'Please provide size as int or long.'
        self.size = value

    file_size = property(get_file_size, set_file_size)

    def get_date_time(self):
        return time.localtime(self.mtime)[0:6]

    def set_date_time(self, value):
        assert isinstance(value, tuple), 'mtime should be tuple (year, month, day, hour, minute, second).'
        assert len(value) == 6, 'mtime should be tuple (year, month, day, hour, minute, second).'
        self.mtime = time.mktime(value + (0, 0, 0))

    date_time = property(get_date_time, set_date_time)

    header_offset = Entry.header_position

    def _get_missing(self):
        raise NotImplemented()

    def _set_missing(self, value):
        raise NotImplemented()

    compress_type = property(_get_missing, _set_missing)
    comment = property(_get_missing, _set_missing)
    extra = property(_get_missing, _set_missing)
    create_system = property(_get_missing, _set_missing)
    create_version = property(_get_missing, _set_missing)
    extract_version = property(_get_missing, _set_missing)
    reserved = property(_get_missing, _set_missing)
    flag_bits = property(_get_missing, _set_missing)
    volume = property(_get_missing, _set_missing)
    internal_attr = property(_get_missing, _set_missing)
    external_attr = property(_get_missing, _set_missing)
    CRC = property(_get_missing, _set_missing)
    compress_size = property(_get_missing, _set_missing)


class ZipFile(SeekableArchive):
    def __init__(self, f, mode='r', compression=ZIP_DEFLATED, allowZip64=False):
        super(ZipFile, self).__init__(f, mode=mode, format='zip', entry_class=ZipEntry, encoding='CP437')
        if mode == 'w' and compression == ZIP_STORED:
            # Disable compression for writing.
            _libarchive.archive_write_set_format_option(self.archive._a, "zip", "compression", "store")
        self.compression = compression

    getinfo     = SeekableArchive.getentry

    def namelist(self):
        return list(self.iterpaths)

    def infolist(self):
        return list(self)

    def open(self, name, mode, pwd=None):
        if pwd:
            raise NotImplemented('Encryption not supported.')
        if mode == 'r':
            return self.readstream(name)
        else:
            return self.writestream(name)

    def extract(self, name, path=None, pwd=None):
        if pwd:
            raise NotImplemented('Encryption not supported.')
        if not path:
            path = os.getcwd()
        return self.readpath(name, os.path.join(path, name))

    def extractall(self, path, names=None, pwd=None):
        if pwd:
            raise NotImplemented('Encryption not supported.')
        if not names:
            names = self.namelist()
        if names:
            for name in names:
                self.extract(name, path)

    def read(self, name, pwd=None):
        if pwd:
            raise NotImplemented('Encryption not supported.')
        return self.read(name)

    def writestr(self, member, data, compress_type=None):
        if compress_type != self.compression:
            raise Exception('Cannot change compression type for individual entries.')
        return self.write(member, data)

    def setpassword(self, pwd):
        raise NotImplemented('Encryption not supported.')

    def testzip(self):
        raise NotImplemented()

    def _get_missing(self):
        raise NotImplemented()

    def _set_missing(self, value):
        raise NotImplemented()

    comment = property(_get_missing, _set_missing)
