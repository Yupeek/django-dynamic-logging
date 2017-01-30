# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import logging

from django.apps.config import AppConfig

from dynamic_logging.models import Scheduler

logger = logging.getLogger(__name__)

main_scheduler = Scheduler()


class DynamicLoggingConfig(AppConfig):
    def ready(self):
        main_scheduler.reload()
