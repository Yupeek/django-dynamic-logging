# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import logging
import operator
import threading

from django.core.exceptions import ImproperlyConfigured
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
        post_save.disconnect(self.on_config_changed, sender=Trigger)
        post_delete.disconnect(self.on_config_changed, sender=Trigger)

        post_save.disconnect(self.on_config_changed, sender=Config)
        post_delete.disconnect(self.on_config_changed, sender=Config)

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

    def reload_scheduler(self, *args, **kwargs):
        """
        called whene we recieved a propagated order to reload
        :return:
        """
        try:
            main_scheduler.reload()
        except Exception:
            logger.exception("failed to reload the scheduler")


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
        self.last_pks = {'triggers': set(), 'configs': set()}

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
        last_wake, self.last_wake = self.last_wake, now
        triggers = list(Trigger.objects.only('pk', 'last_update'))
        configs = list(Config.objects.only('pk', 'last_update'))
        triggers_pks = set(map(operator.attrgetter('pk'), triggers))
        configs_pks = set(map(operator.attrgetter('pk'), configs))
        if any(map(lambda o: o.last_update >= last_wake, triggers + configs)) \
                or (self.last_pks['triggers'] - triggers_pks) \
                or (self.last_pks['configs'] - configs_pks):

            self.reload_scheduler()
        self.last_pks = {'triggers': triggers_pks, 'configs': configs_pks}

    def propagate(self):
        pass


class AmqpPropagator(Propagator):
    """
    the most reliable propagator that use a message broker to propagatate the reloading of the current config
    for all instances

    it require, in the settings, the url to use to connect.
    the name of the exchange to create can be given too. by default it will logging_propagator

    >>> DYNAMIC_LOGGING = {
    ...     "upgrade_propagator": {
    ...         'class': "dynamic_logging.propagator.AmqpPropagator",
    ...         'config': {
    ...             'url': 'amqp://guest:guest@localhost:5672/%2F',
    ...             'exchange_name': 'loger_propagator',
    ...         }
    ...     }
    ... }
    """

    def __init__(self, conf):
        super(AmqpPropagator, self).__init__(conf)
        self.connection = self.channel = self.exchange_name = None
        self.amqp_thread = None

    def setup(self):
        try:
            import pika
        except ImportError:  # pragma: nocover
            raise ImproperlyConfigured("AmqpPropagator require the pika library to be installed.")
        url = self.conf.get("url")
        if not url:  # pragma: nocover
            raise ImproperlyConfigured("AmqpPropagator require the url of the message broker in the setting "
                                       "DYNAMIC_LOGGING['upgrade_propagator']['config']. please refer to the pika doc "
                                       "to build it : "
                                       "http://pika.readthedocs.io/en/0.10.0/examples/using_urlparameters.html")
        self.connection = pika.BlockingConnection(pika.URLParameters(url))
        self.channel = channel = self.connection.channel()
        self.exchange_name = exchange_name = self.conf.get('echange_name', 'logging_propagator')
        channel.exchange_declare(exchange=exchange_name,
                                 type='fanout')
        queue = channel.queue_declare(exclusive=True)
        queue_name = queue.method.queue
        channel.queue_bind(exchange=exchange_name, queue=queue_name)

        channel.basic_consume(self.reload_scheduler, queue=queue_name, no_ack=True)
        self.amqp_thread = threading.Thread(name='AmqpPropagator Listener', target=channel.start_consuming)
        self.amqp_thread.daemon = True
        self.amqp_thread.start()
        super(AmqpPropagator, self).setup()

    def propagate(self):
        self.channel.basic_publish(
            exchange=self.exchange_name,
            routing_key='',
            body='reload config trigered'
        )

    def teardown(self):
        self.connection.ioloop.stop()
        self.amqp_thread = None
        self.connection = self.channel = self.exchange_name = None
