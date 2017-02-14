# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import logging

from django.core.exceptions import ImproperlyConfigured
from django.db import connections
from django.dispatch.dispatcher import Signal

logger = logging.getLogger(__name__)

logging_changed = Signal(providing_args=['config'])
"""
triggered when new logging config is added.
"""

config_applied = Signal(providing_args=['config'])
"""
triggered each time a config is applied
"""


class AutoSignalsHandler(object):
    extra_signals = {}

    DEFAULT_SIGNALS = ('db_debug',)

    def apply(self, signals):
        """
        apply a list of signals to handle automaticaly some special cases.
        :param signals: the list of the signals code names. one of
        :return: nothing
        """
        for signal in signals:
            funct = self.extra_signals.get(signal, None) or getattr(self, signal, None)
            if funct:
                funct()
            else:
                raise ImproperlyConfigured("the signal handling %s is not registered" % signal)

    def db_debug(self):
        """
        enable the DebugCursor if django.db.backends is in debug.
        if not, no sql query will be activated.
        :return:
        """
        old_cnx_val = {}

        def db_debug_handler(sender, config, **kwargs):
            """
            set the debug
            :param sender:
            :param config:
            :param kwargs:
            :return:
            """
            lvl = config.config.get('loggers', {}).get('django.db.backends', {}).get('level', 'ERROR')
            if not isinstance(lvl, int):
                lvl = getattr(logging, lvl, 50)
            if lvl <= logging.DEBUG:
                for alias in connections:
                    old_cnx_val.setdefault(alias, connections[alias].force_debug_cursor)
                    connections[alias].force_debug_cursor = True
            else:
                for alias, val in list(old_cnx_val.items()):
                    connections[alias].force_debug_cursor = val
                    del old_cnx_val[alias]
        config_applied.connect(db_debug_handler, weak=False)
