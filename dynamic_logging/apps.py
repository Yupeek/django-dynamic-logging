# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import logging

from django.apps.config import AppConfig
from django.core.signals import setting_changed
from django.db.utils import OperationalError

from dynamic_logging.settings import get_setting
from dynamic_logging.signals import AutoSignalsHandler

logger = logging.getLogger(__name__)


class DynamicLoggingConfig(AppConfig):
    name = 'dynamic_logging'
    auto_signal_handler = AutoSignalsHandler()

    def __init__(self, *args, **kwargs):
        self.propagator = None
        super(DynamicLoggingConfig, self).__init__(*args, **kwargs)

    def on_settings_changed(self, sender, setting, *args, **kwargs):
        if setting == 'DYNAMIC_LOGGING':
            self.setup_propagator()

    def setup_propagator(self):
        from dynamic_logging.propagator import Propagator
        if self.propagator is not None:
            self.propagator.teardown()
        self.propagator = Propagator.get_current()
        self.propagator.setup()

    def ready(self):
        # import at ready time to prevent model loading before app ready
        from dynamic_logging.scheduler import main_scheduler
        try:
            main_scheduler.reload(2)  # 2 sec to prevent unit-tests to load the production database
        except OperationalError:  # pragma: nocover
            pass  # no trigger table exists atm. we don't care since there is no Trigger to pull.
        # setup signals for Trigger changes. it will reload the current trigger and next one

        self.auto_signal_handler.apply(get_setting('signals_auto'))
        self.setup_propagator()

        setting_changed.connect(self.on_settings_changed)
