#!/usr/bin/env python
#
# Copyright (c) 2015, SmartFile <tcunningham@smartfile.com>
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

from os import environ

try:
    from setuptools import setup, Extension
    from setuptools.command.build_ext import build_ext
except ImportError:
    from distutils.core import setup, Extension
    from distutils.command.build_ext import build_ext


name = 'python-libarchive'
version = '4.0.1'
release = '1'
versrel = version + '-' + release
readme = 'README.rst'
download_url = "http://" + name + ".googlecode.com/files/" + name + "-" + \
                                                          versrel + ".tar.gz"
long_description = open(readme).read()

class build_ext_extra(build_ext, object):
    """
    Extend build_ext allowing extra_compile_args and extra_link_args to be set
    on the command-line.
    """
    user_options = build_ext.user_options
    user_options.append(
        ('extra-compile-args=', None,
         'Extra arguments passed directly to the compiler')
        )
    user_options.append(
        ('extra-link-args=', None,
         'Extra arguments passed directly to the linker')
        )

    def initialize_options(self):
        build_ext.initialize_options(self)
        self.extra_compile_args = None
        self.extra_link_args = None

    def build_extension(self, ext):
        if self.extra_compile_args:
            ext.extra_compile_args.append(self.extra_compile_args)
        if self.extra_link_args:
            ext.extra_link_args.append(self.extra_link_args)
        super(build_ext_extra, self).build_extension(ext)


# Use a provided libarchive else default to hard-coded path.
libarchivePrefix = environ.get('LIBARCHIVE_PREFIX')
if libarchivePrefix:
    extra_compile_args = ['-I{0}/include'.format(libarchivePrefix)]
    extra_link_args = ['-Wl,-rpath={0}/lib'.format(libarchivePrefix)]
    environ['LDFLAGS'] = '-L{0}/lib {1}'.format(libarchivePrefix,
                                                environ.get('LDFLAGS', ''))
else:
    extra_compile_args = []
    extra_link_args = ['-l:libarchive.so.13']

__libarchive = Extension(name='libarchive.__libarchive',
                        sources=['libarchive/_libarchive_wrap.c'],
                        libraries=['archive'],
                        extra_compile_args=extra_compile_args,
                        extra_link_args=extra_link_args,
                        include_dirs=['libarchive'],
                        )


setup(name = name,
      version = versrel,
      description = 'A libarchive wrapper for Python.',
      long_description = long_description,
      license = 'BSD-style license',
      platforms = ['any'],
      author = 'Ben Timby, Travis Cunningham, Ryan Johnston, SmartFile',
      author_email = 'tcunningham@smartfile.com',
      url = 'https://github.com/smartfile/python-libarchive',
      download_url = download_url,
      packages = ['libarchive'],
      classifiers = [
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'Operating System :: OS Independent',
          'Programming Language :: C',
          'Programming Language :: Python',
          'Topic :: System :: Archiving :: Compression',
          'Topic :: Software Development :: Libraries :: Python Modules',
      ],
      cmdclass = {
        'build_ext': build_ext_extra,
      },
      ext_modules = [__libarchive],
      )
