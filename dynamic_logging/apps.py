# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import logging

from django.apps.config import AppConfig
from django.db.models.signals import post_delete, post_save
from django.db.utils import OperationalError

logger = logging.getLogger(__name__)


class DynamicLoggingConfig(AppConfig):
    name = 'dynamic_logging'

    def ready(self):
        # import at ready time to prevent model loading before app ready
        from dynamic_logging.scheduler import main_scheduler
        try:
            main_scheduler.reload(2)  # 2 sec to prevent unit-tests to load the production database
        except OperationalError:  # pragma: nocover
            pass  # no trigger table exists atm. we don't care since there is no Trigger to pull.
        # setup signals for Trigger changes. it will reload the current trigger and next one
        from .signals import reload_timers_on_trigger_change
        Trigger = self.get_model('Trigger')
        Config = self.get_model('Config')

        post_save.connect(reload_timers_on_trigger_change, sender=Trigger)
        post_delete.connect(reload_timers_on_trigger_change, sender=Trigger)

        post_save.connect(reload_timers_on_trigger_change, sender=Config)
        post_delete.connect(reload_timers_on_trigger_change, sender=Config)
