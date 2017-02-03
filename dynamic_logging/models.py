# -*- coding: utf-8 -*-
import datetime
import json
import logging
import logging.config
from copy import deepcopy

from django.conf import settings
from django.db import models
from django.db.models.query_utils import Q
from django.utils import timezone
from django.utils.six import python_2_unicode_compatible

module_logger = logging.getLogger(__name__)


def now_plus_2hours():
    return timezone.now() + datetime.timedelta(hours=2)


class TriggerQueryset(models.QuerySet):
    def valid_at(self, date):
        """
        recover all triggers valid at the given time
        :param start:
        :param end:
        :return:
        """
        return self.filter(
            (Q(start_date__lte=date) | Q(start_date__isnull=True))
            &
            (Q(end_date__gt=date) | Q(end_date__isnull=True))
        )


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

    is_active = models.BooleanField(default=True)

    start_date = models.DateTimeField(default=timezone.now, null=True)
    end_date = models.DateTimeField(default=now_plus_2hours, null=True)

    config = models.ForeignKey('Config', related_name='triggers')

    @classmethod
    def default(cls):
        if not hasattr(cls, "_default_settings"):
            cls._default_settings = cls(
                name='default settings', start_date=None, end_date=None, config=Config.default()
            )
        return cls._default_settings

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

    def apply(self):
        self.config.apply(self)

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

    KEEPT_CONFIG = ('loggers', )

    name = models.CharField(max_length=255)

    config_json = models.TextField()

    @classmethod
    def default(cls):
        if not hasattr(cls, "_default_settings"):
            cls._default_settings = cls(name="from settings")
            cls._default_settings.config = settings.LOGGING
        return cls._default_settings

    @property
    def config(self):
        if not self.config_json:
            return {}
        return {
            key: val
            for key, val in json.loads(self.config_json).items()
            if key in self.KEEPT_CONFIG
        }

    @config.setter
    def config(self, val):
        self.config_json = json.dumps({
            key: val
            for key, val in val.items()
            if key in self.KEEPT_CONFIG
        })

    def apply(self, trigger=None):
        """
        apply the current config to the global logging system.
        it will override all handlers and loggers currently active.
        :return:
        """
        config = deepcopy(settings.LOGGING)
        config['loggers'] = self.config.get('loggers', {})
        module_logger.info("[%s] applying logging config %s: %r" % (trigger, self, config))
        self._reset_logging()
        logging.config.dictConfig(config)

    def _reset_logging(self):
        """
        reset all the handlers for all loggers.
        :return:
        """
        for logger in get_loggers().values():
            logger.handlers = []
            logger.propagate = True


def get_loggers():
    return {k: v for k, v in logging.Logger.manager.loggerDict.items() if isinstance(v, logging.Logger)}
