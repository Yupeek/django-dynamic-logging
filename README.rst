=====================
django-dynamic-loging
=====================

allow to change the logging configuration for running production website.
you found a bug, and the current stacktrace is not enouth ? first, you should
change the settings LOGGING to make it more verbose (with something like LEVEL: 'DEBUG')

but, the bad thing, is that you must:
1. connect to your production server
2. change the settings in live
3. make sure no synthax error
4. restart the service (with downtime)
5. do not forget to rollback after some time to prevent performance issues.

stable branche

.. image:: https://img.shields.io/travis/Yupeek/django-dynamic-logging/master.svg
    :target: https://travis-ci.org/Yupeek/django-dynamic-logging

.. image:: https://readthedocs.org/projects/django-dynamic-logging/badge/?version=latest
    :target: http://django-dynamic-logging.readthedocs.org/en/latest/

.. image:: https://coveralls.io/repos/github/Yupeek/django-dynamic-logging/badge.svg?branch=master
    :target: https://coveralls.io/github/Yupeek/django-dynamic-logging?branch=master

.. image:: https://img.shields.io/pypi/v/django-dynamic-logging.svg
    :target: https://pypi.python.org/pypi/django-dynamic-logging
    :alt: Latest PyPI version

.. image:: https://img.shields.io/pypi/dm/django-dynamic-logging.svg
    :target: https://pypi.python.org/pypi/django-dynamic-logging
    :alt: Number of PyPI downloads per month

.. image:: https://requires.io/github/Yupeek/django-dynamic-logging/requirements.svg?branch=master
     :target: https://requires.io/github/Yupeek/django-dynamic-logging/requirements/?branch=master
     :alt: Requirements Status

development status

.. image:: https://img.shields.io/travis/Yupeek/django-dynamic-logging/develop.svg
    :target: https://travis-ci.org/Yupeek/django-dynamic-logging

.. image:: https://coveralls.io/repos/github/Yupeek/django-dynamic-logging/badge.svg?branch=develop
    :target: https://coveralls.io/github/Yupeek/django-dynamic-logging?branch=develop

.. image:: https://requires.io/github/Yupeek/django-dynamic-logging/requirements.svg?branch=develop
     :target: https://requires.io/github/Yupeek/django-dynamic-logging/requirements/?branch=develop
     :alt: Requirements Status


Installation
------------

1. Install using pip:

   ``pip install django-dynamic-logging``

2. Alternatively, you can install download or clone this repo and call

    ``pip install -e .``.

requirements
------------

the supported versions is the same as current django

- python 2.7, 3.4, 3.5
- django 1.8, 1.9, 1.10

configuration
-------------

add `dynamic-logging` to your INSTALLED_APPS

