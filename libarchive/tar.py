import os
from libarchive import is_archive, Entry, SeekableArchive
from tarfile import DEFAULT_FORMAT, USTAR_FORMAT, GNU_FORMAT, PAX_FORMAT, \
    ENCODING
from tarfile import REGTYPE, SYMTYPE, DIRTYPE, FIFOTYPE, CHRTYPE, BLKTYPE

FORMAT_CONVERSION = {
    USTAR_FORMAT:       'tar',
    GNU_FORMAT:         'gnu',
    PAX_FORMAT:         'pax',
}


def is_tarfile(filename):
    return is_archive(filename, formats=('tar', 'gnu', 'pax'))


def open(**kwargs):
    return TarFile(**kwargs)


class TarInfo(Entry):
    def __init__(self, name):
        super(TarInfo, self).__init__(pathname=name)

    fromtarfile = Entry.from_archive

    def get_name(self):
        return self.pathname

    def set_name(self, value):
        self.pathname = value

    name = property(get_name, set_name)

    @property
    def get_type(self):
        for attr, type in (
                ('isdir', DIRTYPE), ('isfile', REGTYPE), ('issym', SYMTYPE),
                ('isfifo', FIFOTYPE), ('ischr', CHRTYPE), ('isblk', BLKTYPE),
            ):
            if getattr(self, attr)():
                return type

    def _get_missing(self):
        raise NotImplemented()

    def _set_missing(self, value):
        raise NotImplemented()

    pax_headers = property(_get_missing, _set_missing)


class TarFile(SeekableArchive):
    getmember   = SeekableArchive.getentry
    list        = SeekableArchive.printlist
    extract     = SeekableArchive.readpath
    extractfile = SeekableArchive.readstream

    def __init__(self, name=None, mode='r', fileobj=None,
                 format=DEFAULT_FORMAT, tarinfo=TarInfo, encoding=ENCODING):
        if name:
            f = name
        elif fileobj:
            f = fileobj
        try:
            format = FORMAT_CONVERSION.get(format)
        except KeyError:
            raise Exception('Invalid tar format: %s' % format)
        super(TarFile, self).__init__(f, mode=mode, format=format,
                                      entry_class=tarinfo, encoding=encoding)

    def getmembers(self):
        return list(self)

    def getnames(self):
        return list(self.iterpaths)

    def __next__(self):
        raise NotImplementedError
        pass # TODO: how to do this?

    def extract(self, member, path=None):
        if path is None:
            path = os.getcwd()
        if isinstance(member, str):
            f = os.path.join(path, member)
        else:
            f = os.path.join(path, member.pathname)
        return self.readpath(member, f)

    def add(self, name, arcname, recursive=True, exclude=None, filter=None):
        pass # TODO: implement this.

    def addfile(self, tarinfo, fileobj):
        return self.writepath(fileobj, tarinfo)

    def gettarinfo(self, name=None, arcname=None, fileobj=None):
        if name:
            f = name
        elif fileobj:
            f = fileobj
        entry = self.entry_class.from_file(f)
        if arcname:
            entry.pathname = arcname
        return entry

    def _get_missing(self):
        raise NotImplemented()

    def _set_missing(self, value):
        raise NotImplemented()

    pax_headers = property(_get_missing, _set_missing)
