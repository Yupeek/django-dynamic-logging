#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

import dynamic_logging

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

version = dynamic_logging.__version__

if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'testsettings'

if sys.argv[-1] == 'publish':
    # os.system('cd docs && make html')
    os.system('python setup.py sdist bdist_wheel upload')
    print("You probably want to also tag the version now:")
    print("  git tag -a %s -m 'version %s'" % (version, version))
    print("  git push --tags")
    sys.exit()

if sys.argv[-1] == 'doc':
    os.system('cd docs && make html')
    sys.exit()

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme_file:
    readme = readme_file.read()

with open(os.path.join(os.path.dirname(__file__), 'test_requirements.txt')) as requirements_file:
    tests_require = requirements_file.readlines()

setup(
    name='django-dynamic-logging',
    version=version,
    description="""django app to manager logging in runtime system""",
    long_description=readme,
    author='Darius BERNARD',
    author_email='darius@yupeek.com',
    url='https://github.com/Yupeek/django-dynamic-logging',
    tests_require=tests_require,
    install_requires=[
        'pytz',
    ],
    packages=[
        'dynamic_logging',
        'dynamic_logging.migrations',
        'dynamic_logging.templatetags',
    ],
    include_package_data=True,
    license="GNU GENERAL PUBLIC LICENSE",
    zip_safe=False,
    keywords='django logging dynamic handlers logger',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries',
        'Topic :: Utilities',
        'Environment :: Web Environment',
        'Framework :: Django',
    ],
)
