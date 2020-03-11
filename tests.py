#!/usr/bin/env python
# coding=utf-8
#
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

import os, unittest, tempfile, random, string, sys
import zipfile
import io

from libarchive import Archive, is_archive_name, is_archive
from libarchive.zip import is_zipfile, ZipFile, ZipEntry

PY3 = sys.version_info[0] == 3

TMPDIR = tempfile.mkdtemp(suffix='.python-libarchive')
ZIPFILE = 'test.zip'
ZIPPATH = os.path.join(TMPDIR, ZIPFILE)

FILENAMES = [
    'test1.txt',
    'foo',
    # TODO: test non-ASCII chars.
    #'álért.txt',
]


def make_temp_files():
    if not os.path.exists(ZIPPATH):
        for name in FILENAMES:
            with open(os.path.join(TMPDIR, name), 'w') as f:
                f.write(''.join(random.sample(string.ascii_letters, 10)))


def make_temp_archive():
    make_temp_files()
    with zipfile.ZipFile(ZIPPATH, mode="w") as z:
        for name in FILENAMES:
            z.write(os.path.join(TMPDIR, name), arcname=name)


class TestIsArchiveName(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(is_archive_name('foo'), None)
        self.assertEqual(is_archive_name('foo.txt'), None)
        self.assertEqual(is_archive_name('foo.txt.gz'), None)
        self.assertEqual(is_archive_name('foo.tar.gz'), 'tar')
        self.assertEqual(is_archive_name('foo.tar.bz2'), 'tar')
        self.assertEqual(is_archive_name('foo.zip'), 'zip')
        self.assertEqual(is_archive_name('foo.rar'), 'rar')
        self.assertEqual(is_archive_name('foo.iso'), 'iso')
        self.assertEqual(is_archive_name('foo.rpm'), 'cpio')


class TestIsArchiveZip(unittest.TestCase):
    def setUp(self):
        make_temp_archive()

    def test_zip(self):
        self.assertEqual(is_archive(ZIPPATH), True)
        self.assertEqual(is_archive(ZIPPATH, formats=('zip', )), True)
        self.assertEqual(is_archive(ZIPPATH, formats=('tar', )), False)


class TestIsArchiveTar(unittest.TestCase):
    def test_tar(self):
        pass


# TODO: incorporate tests from:
# http://hg.python.org/cpython/file/a6e1d926cd98/Lib/test/test_zipfile.py
class TestZipRead(unittest.TestCase):
    def setUp(self):
        make_temp_archive()
        self.f = open(ZIPPATH, mode='r')

    def tearDown(self):
        self.f.close()

    def test_iszipfile(self):
        self.assertEqual(is_zipfile('/dev/null'), False)
        self.assertEqual(is_zipfile(ZIPPATH), True)

    def test_iterate(self):
        z = ZipFile(self.f, 'r')
        count = 0
        for e in z:
            count += 1
        self.assertEqual(count, len(FILENAMES), 'Did not enumerate correct number of items in archive.')

    def test_deferred_close_by_archive(self):
        """ Test archive deferred close without a stream. """
        z = ZipFile(self.f, 'r')
        self.assertIsNotNone(z._a)
        self.assertIsNone(z._stream)
        z.close()
        self.assertIsNone(z._a)

    def test_deferred_close_by_stream(self):
        """ Ensure archive closes self if stream is closed first. """
        z = ZipFile(self.f, 'r')
        stream = z.readstream(FILENAMES[0])
        stream.close()
        # Make sure archive stays open after stream is closed.
        self.assertIsNotNone(z._a)
        self.assertIsNone(z._stream)
        z.close()
        self.assertIsNone(z._a)
        self.assertTrue(stream.closed)

    def test_close_stream_first(self):
        """ Ensure that archive stays open after being closed if a stream is
        open. Further, ensure closing the stream closes the archive. """
        z = ZipFile(self.f, 'r')
        stream = z.readstream(FILENAMES[0])
        z.close()
        try:
            stream.read()
        except:
            self.fail("Reading stream from closed archive failed!")
        stream.close()
        # Now the archive should close.
        self.assertIsNone(z._a)
        self.assertTrue(stream.closed)
        self.assertIsNone(z._stream)

    def test_filenames(self):
        z = ZipFile(self.f, 'r')
        names = []
        for e in z:
            names.append(e.filename)
        self.assertEqual(names, FILENAMES, 'File names differ in archive.')

    #~ def test_non_ascii(self):
        #~ pass

    def test_extract_str(self):
        pass


class TestZipWrite(unittest.TestCase):
    def setUp(self):
        make_temp_files()
        self.f = open(ZIPPATH, mode='w')

    def tearDown(self):
        self.f.close()

    def test_writepath(self):
        z = ZipFile(self.f, 'w')
        for fname in FILENAMES:
            with open(os.path.join(TMPDIR, fname), 'r') as f:
                z.writepath(f)
        z.close()

    def test_writepath_directory(self):
        """ Test writing a directory. """
        z = ZipFile(self.f, 'w')
        z.writepath(None, pathname='/testdir', folder=True)
        z.writepath(None, pathname='/testdir/testinside', folder=True)
        z.close()
        self.f.close()

        f = open(ZIPPATH, mode='r')
        z = ZipFile(f, 'r')

        entries = z.infolist()

        assert len(entries) == 2
        assert entries[0].isdir()
        z.close()
        f.close()

    def test_writestream(self):
        z = ZipFile(self.f, 'w')
        for fname in FILENAMES:
            full_path = os.path.join(TMPDIR, fname)
            i = open(full_path)
            o = z.writestream(fname)
            while True:
                data = i.read(1)
                if not data:
                    break
                if PY3:
                    o.write(data)
                else:
                    o.write(unicode(data))
            o.close()
            i.close()
        z.close()

    def test_writestream_unbuffered(self):
        z = ZipFile(self.f, 'w')
        for fname in FILENAMES:
            full_path = os.path.join(TMPDIR, fname)
            i = open(full_path)
            o = z.writestream(fname, os.path.getsize(full_path))
            while True:
                data = i.read(1)
                if not data:
                    break
                if PY3:
                    o.write(data)
                else:
                    o.write(unicode(data))
            o.close()
            i.close()
        z.close()

    def test_deferred_close_by_archive(self):
        """ Test archive deferred close without a stream. """
        z = ZipFile(self.f, 'w')
        o = z.writestream(FILENAMES[0])
        z.close()
        self.assertIsNotNone(z._a)
        self.assertIsNotNone(z._stream)
        if PY3:
            o.write('testdata')
        else:
            o.write(unicode('testdata'))
        o.close()
        self.assertIsNone(z._a)
        self.assertIsNone(z._stream)
        z.close()


class TestHighLevelAPI(unittest.TestCase):
    def setUp(self):
        make_temp_archive()

    def _test_listing_content(self, f):
        """ Test helper capturing file paths while iterating the archive. """
        found = []
        with Archive(f) as a:
            for entry in a:
                found.append(entry.pathname)

        self.assertEqual(set(found), set(FILENAMES))

    def test_open_by_name(self):
        """ Test an archive opened directly by name. """
        self._test_listing_content(ZIPPATH)

    def test_open_by_named_fobj(self):
        """ Test an archive using a file-like object opened by name. """
        with open(ZIPPATH, 'rb') as f:
            self._test_listing_content(f)

    def test_open_by_unnamed_fobj(self):
        """ Test an archive using file-like object opened by fileno(). """
        with open(ZIPPATH, 'rb') as zf:
            with io.FileIO(zf.fileno(), mode='r', closefd=False) as f:
                self._test_listing_content(f)


if __name__ == '__main__':
    unittest.main()
