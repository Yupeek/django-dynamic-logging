# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import logging
import threading

from django.db.models.signals import post_delete, post_save
from django.utils import timezone
from django.utils.module_loading import import_string

from dynamic_logging.models import Config, Trigger
from dynamic_logging.scheduler import main_scheduler
from dynamic_logging.settings import get_setting

logger = logging.getLogger(__name__)


class Propagator(object):
    """
    this object is in charge to call main_scheduler.reload each time a config or a trigger
    is updated
    """

    @staticmethod
    def get_current():
        current = get_setting('upgrade_propagator')
        cls = import_string(current['class'])
        return cls(current['config'])

    def __init__(self, conf):
        self.conf = conf

    def setup(self):
        """
        called a application start
        :return:
        """
        post_save.connect(self.on_config_changed, sender=Trigger)
        post_delete.connect(self.on_config_changed, sender=Trigger)

        post_save.connect(self.on_config_changed, sender=Config)
        post_delete.connect(self.on_config_changed, sender=Config)

    def teardown(self):
        post_save.disconnect(self.on_config_changed)
        post_delete.disconnect(self.on_config_changed)

    def on_config_changed(self, *args, **kwargs):
        """
        called each time a local config is changed
        """
        self.propagate()

    def propagate(self):
        """
        propagate the signal to reload the config.
        :return:
        """
        raise NotImplementedError()

    def reload_scheduler(self):
        """
        called whene we recieved a propagated order to reload
        :return:
        """
        main_scheduler.reload()


class DummyPropagator(Propagator):
    def setup(self):
        pass

    def propagate(self):
        pass


class ThreadSignalPropagator(Propagator):
    """
    this propagator is for single process only. it will reload the scheduler localy to
    the process that has updated the config/trigger.

    in multi process env, all other process won't be triggered
    """

    def propagate(self, *args, **kwargs):
        self.reload_scheduler()


class RepeatTimer(threading.Thread):
    def __init__(self, interval, function, *args, **kwargs):
        self.interval = interval
        self.function = function
        super(RepeatTimer, self).__init__(*args, **kwargs)
        self.stopped = threading.Event()
        self.daemon = True

    def cancel(self):
        self.stopped.set()

    def run(self):
        while not self.stopped.wait(self.interval):
            self.function()


class TimerPropagator(Propagator):
    """
    this propagator is a fallback for small website that can't use message queue.
    it will check for config update each minutes (customisable) and will reload if a trigger/config
    was updated since the last time
    """

    def __init__(self, conf):
        super(TimerPropagator, self).__init__(conf)
        self.timer = None
        self.last_wake = timezone.now()

    def setup(self):
        # we don't call super since we will update this process each n sec
        self.timer = RepeatTimer(
            self.conf.get("interval", 60),
            self.check_new_config,
            name='TimerPropagator_timer')
        self.timer.start()

    def teardown(self):
        self.timer.cancel()

    def check_new_config(self):
        now = timezone.now()
        if (Trigger.objects.filter(last_update__gte=self.last_wake).exists() or
                Config.objects.filter(last_update__gte=self.last_wake).exists()):
            self.last_wake = now
            self.reload_scheduler()

    def propagate(self):
        pass
