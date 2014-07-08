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

import os, unittest, tempfile, random, string, subprocess

from libarchive import is_archive_name, is_archive
from libarchive.zip import is_zipfile, ZipFile, ZipEntry

TMPDIR = tempfile.mkdtemp()
ZIPCMD = '/usr/bin/zip'
ZIPFILE = 'test.zip'
ZIPPATH = os.path.join(TMPDIR, ZIPFILE)

FILENAMES = [
    'test1.txt',
    'foo',
    # TODO: test non-ASCII chars.
    #'álért.txt',
]

def make_temp_files():
    print TMPDIR
    if not os.path.exists(ZIPPATH):
        for name in FILENAMES:
            file(os.path.join(TMPDIR, name), 'w').write(''.join(random.sample(string.printable, 10)))

def make_temp_archive():
    if not os.access(ZIPCMD, os.X_OK):
        raise AssertionError('Cannot execute %s.' % ZIPCMD)
    cmd = [ZIPCMD, ZIPFILE]
    make_temp_files()
    cmd.extend(FILENAMES)
    os.chdir(TMPDIR)
    subprocess.call(cmd)


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

    def test_iszipfile(self):
        self.assertEqual(is_zipfile('/dev/null'), False)
        self.assertEqual(is_zipfile(ZIPPATH), True)

    def test_iterate(self):
        f = file(ZIPPATH, mode='r')
        z = ZipFile(f, 'r')
        count = 0
        for e in z:
            count += 1
        self.assertEqual(count, len(FILENAMES), 'Did not enumerate correct number of items in archive.')

    def test_deferred_close_by_archive(self):
        """ Test archive deferred close without a stream. """
        f = file(ZIPPATH, mode='r')
        z = ZipFile(f, 'r')
        self.assertIsNotNone(z._a)
        self.assertIsNone(z._stream)
        z.close()
        self.assertIsNone(z._a)

    def test_deferred_close_by_stream(self):
        """ Ensure archive closes self if stream is closed first. """
        f = file(ZIPPATH, mode='r')
        z = ZipFile(f, 'r')
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
        f = file(ZIPPATH, mode='r')
        z = ZipFile(f, 'r')
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
        f = file(ZIPPATH, mode='r')
        z = ZipFile(f, 'r')
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

    def test_writepath(self):
        f = file(ZIPPATH, mode='w')
        z = ZipFile(f, 'w')
        for fname in FILENAMES:
            z.writepath(file(os.path.join(TMPDIR, fname), 'r'))
        z.close()

    def test_writestream(self):
        f = file(ZIPPATH, mode='w')
        z = ZipFile(f, 'w')
        for fname in FILENAMES:
            full_path = os.path.join(TMPDIR, fname)
            i = file(full_path)
            o = z.writestream(fname)
            while True:
                data = i.read(1)
                if not data:
                    break
                o.write(data)
            o.close()
            i.close()
        z.close()

    def test_writestream_unbuffered(self):
        f = file(ZIPPATH, mode='w')
        z = ZipFile(f, 'w')
        for fname in FILENAMES:
            full_path = os.path.join(TMPDIR, fname)
            i = file(full_path)
            o = z.writestream(fname, os.path.getsize(full_path))
            while True:
                data = i.read(1)
                if not data:
                    break
                o.write(data)
            o.close()
            i.close()
        z.close()

    def test_deferred_close_by_archive(self):
        """ Test archive deferred close without a stream. """
        f = file(ZIPPATH, mode='w')
        z = ZipFile(f, 'w')
        o = z.writestream(FILENAMES[0])
        z.close()
        self.assertIsNotNone(z._a)
        self.assertIsNotNone(z._stream)
        o.write('testdata')
        o.close()
        self.assertIsNone(z._a)
        self.assertIsNone(z._stream)
        z.close()

if __name__ == '__main__':
    unittest.main()
