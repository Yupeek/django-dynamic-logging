# -*- coding: utf-8 -*-
import datetime
import functools
import json
import logging
import threading

from django.conf import settings
from django.db import models
from django.db.models.query_utils import Q
from django.utils import timezone
from django.utils.six import python_2_unicode_compatible

logger = logging.getLogger(__name__)


def now_plus_2hours():
    return timezone.now() + datetime.timedelta(hours=2)


class Scheduler(object):
    """
    a special class that keep trace of the next event to trigger and
    will trigger it in time.
    """

    def __init__(self):
        self.next_timer = None
        """
        :type: threading.Timer
        """
        self._lock = threading.RLock()

    def get_next_wake(self, current=None, after=None):
        """
        function that return the next trigger to apply and the date at which it may occure

        :param current: the current trigger active (which won't be reenabled
        :param after:  the date to use to check current time
        :return: the next trigger to enable, with the date it whith it occure. date can be none if the trigger shall be
                 enabled right now
        """
        after = after or timezone.now()
        try:
            next_trigger = Trigger.objects.filter(start_date__gt=after).earliest()
        except Trigger.DoesNotExist:
            # no next trigger
            if current is None:
                # and no current... reverse for default
                return Trigger.default(), None
            else:
                # and a current: we wait for current to stop and so be it
                return Trigger.default(), current.end_date
        if current is None or current.end_date is None \
                or current.end_date > next_trigger.start_date:
            # the current one does not exists or end after the next_trigger start.
            # => the next event is the start of the next trigger
            return next_trigger, next_trigger.start_date
        else:
            # the current one will end befor the next one start
            # we get the trigger that will be valid at the end of the current one(may be null)
            try:
                last_trigger = Trigger.objects.valid_at(current.end_date).latest()
            except Trigger.DoesNotExist:
                # no trigger valide at this moment.
                last_trigger = Trigger.default()
            return last_trigger, current.end_date

    def set_next_wake(self, trigger, at):
        logger.debug("next trigger to enable : %s at %s", trigger, at, extra={'next_date': at})
        with self._lock:
            if self.next_timer is not None:
                self.next_timer.cancel()
                self.next_timer = None
            interval = (at - timezone.now()).total_seconds()
            self.next_timer = threading.Timer(interval, functools.partial(self.wake, trigger=trigger, date=at))
            self.next_timer.start()

    def reload(self):
        """
        cancel the timer and the next trigger, and
        compute the next one
        :return:
        """
        trigger, at = self.get_next_wake()
        with self._lock:
            if self.next_timer is not None:
                self.next_timer.cancel()
                self.next_timer = None
            self.set_next_wake(trigger, at)

    def wake(self, trigger, date):
        """
        function called each time a timer arrived at expiration

        :return:
        """
        logger.debug("wake to enable trigger %s at %s", trigger, date, extra={'expected_date': date})
        next_trigger, at = self.get_next_wake(current=trigger, after=date)
        with self._lock:
            trigger.apply()
            # get the next trigger valid at the current expected date
            # we don't use timezone.now() to prevent the case where threading.Timer wakeup some ms befor the expected
            # date
            self.set_next_wake(next_trigger, at)


class TriggerQueryset(models.QuerySet):
    def valid_at(self, date):
        """
        recover all triggers valid at the given time
        :param start:
        :param end:
        :return:
        """
        return self.filter((Q(start_date__lte=date) | Q(start_date=None)) & Q(end_date__gt=date) | Q(end_date=None))


@python_2_unicode_compatible
class Trigger(models.Model):
    """
    represent the period of time a config should be effective.
    multiple trigger can be active at the same time, but only one config is active. the
    latest trigger in date will take precedence. at the end of a trigger, it will rollback the current config and
    reactivate the last config.
    """
    objects = TriggerQueryset.as_manager()

    name = models.CharField(max_length=255, blank=False, null=False)

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(default=now_plus_2hours)

    config = models.ForeignKey('Config', related_name='triggers')

    @classmethod
    def default(cls):
        return cls(name='default settings', start_date=None, end_date=None, config=Config.default())

    def __str__(self):
        return 'trigger %s from %s to %s for config %s' % (self.name, self.start_date, self.end_date, self.config.name)

    def is_active(self, date=None):
        """
        return True if the current trigger is active at the given date. if no date is given, current date is used
        :param date: the date to check or None for now()
        :return:
        :rtype: bool
        """
        date = date or timezone.now()
        start_date, end_date = self.start_date, self.end_date
        return (start_date <= date or end_date is None) and (end_date >= date or end_date is None)

    class Meta:
        index_together = [
            ('start_date', 'end_date'),
        ]
        get_latest_by = 'start_date'


class Config(models.Model):
    """
    the configuration for a whole logging config.
    one at a time can be active through the Trigger class. if None is active,
    it's the settings.LOGGING that is setup in the server.
    """

    name = models.CharField(max_length=255)

    config_json = models.TextField()

    @classmethod
    def default(cls):
        cfg = cls(name="from settings")
        cfg.config = settings.LOGGING
        return cfg

    @property
    def config(self):
        return {
            key: val
            for key, val in json.loads(self.config_json)
            if key in ('loggers', 'handlers')
            }

    @config.setter
    def config(self, val):
        self.config_json = json.dumps({
                                          key: val
                                          for key, val in val
                                          if key in ('loggers', 'handlers')
                                          })

    def apply(self):
        """
        apply the current config to the global logging system.
        it will override all handlers and loggers currently active.
        :return:
        """
