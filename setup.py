#!/usr/bin/env python
"""
giftwrap
======

giftwrap is a simple Python library providing a DSL for building Debian 
packages for deployment.
"""

# Hack to prevent stupid "TypeError: 'NoneType' object is not callable" error
# in multiprocessing/util.py _exit_function when running `python
# setup.py test` (see
# http://www.eby-sarna.com/pipermail/peak/2010-May/003357.html)
try:
    import multiprocessing
except ImportError:
    pass

from setuptools import setup, find_packages

tests_require = [
    'nose',
    'rednose'
]

install_requires = [
#    'fabric'
]

setup(
    name = 'giftwrap',
    version = '1.0.0',
    author = 'Nick Bruun',
    author_email = 'nick@bruun.co',
    url = 'http://github.com/nickbruun/giftwrap',
    description = 'giftwrap provides a DSL for building Debian packages',
    long_description = __doc__,
    packages = find_packages(exclude = ['tests', 
                                        '.*',
                                        'venv']),
    zip_safe = False,
    install_requires = install_requires,
    tests_require = tests_require,
    extras_require = { 
        'test': tests_require
    },
    test_suite = 'runtests.runtests',
    include_package_data = True,
    classifiers = [
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Topic :: Software Development'
    ],
)
