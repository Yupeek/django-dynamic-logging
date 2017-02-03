# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import logging

from django.dispatch.dispatcher import Signal

from dynamic_logging.scheduler import main_scheduler

logger = logging.getLogger(__name__)

logging_changed = Signal(providing_args=['config'])
"""
triggered when new logging config is added.
"""


def reload_timers_on_trigger_change(sender, **kwargs):
    main_scheduler.reload()
