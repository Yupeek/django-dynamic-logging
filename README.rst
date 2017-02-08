=====================
django-dynamic-loging
=====================

allow to change the logging configuration for running production website from the admin interface.

all you need to do is :
1 - create a logging config [Config model] from a use friendly form
2 - create a timelaps [Trigger model] in which your config is valid (from start_date to end_date, or forever)
3 - enjoy your logging, since you saved the trigger, the app will do the stuff to run it now if it's already
    valide, or at the date/time you enabled it


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


the old way was :

you found a bug, and the current stacktrace is not enough ? first, you should
change the settings LOGGING to make it more verbose (with something like LEVEL: 'DEBUG')

but, the bad thing, is that you must:
1. connect to your production server
2. change the settings in live
3. make sure no synthax error
4. restart the service (with downtime)
5. do not forget to rollback after some time to prevent performance issues.


with django-dynamic-logging, you can update at runtime the logging configuration, including :

- update handlers levels and filter, but nothing else (for security purpose)
- create/delete/update loggers. this include the level, handlers, filters and propagate flag.

may logging configuration can exists in the database, but only one can be active. the leatest trigger (start_date) take
precedence and will activate his config.

ie: you want to set the app «myproject.import» in debug mode to for this night: you set the trigger, and it will
enable the debug only for this night. at day, the default logging config will run




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

configuration in sources
------------------------

1. add `dynamic-logging` to your INSTALLED_APPS

and that's all

configuration for running system
--------------------------------

1. go to your admin, and create a Config
2. create the Trigger that will enable it whenever you want.



