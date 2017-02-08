# -*- coding: utf-8 -*-
import datetime
import json
import logging
import logging.config
from copy import deepcopy

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.query_utils import Q
from django.utils import timezone
from django.utils.six import python_2_unicode_compatible
from django.utils.translation import ugettext as _

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

    start_date = models.DateTimeField(default=timezone.now, blank=True, null=True)
    end_date = models.DateTimeField(default=now_plus_2hours, blank=True, null=True)

    config = models.ForeignKey('Config', related_name='triggers')

    @classmethod
    def default(cls):
        if not hasattr(cls, "_default_settings"):
            cls._default_settings = cls(
                name='default settings', start_date=None, end_date=None
            )
            cls._default_settings.config = Config.default()
        return cls._default_settings

    def __str__(self):
        try:
            cfg_name = self.config.name
        except Config.DoesNotExist:
            cfg_name = "<no config>"
        return 'trigger %s from %s to %s for config %s' % (
            self.name, self.start_date, self.end_date,
            cfg_name)

    def apply(self):
        self.config.apply(self)

    class Meta:
        index_together = [
            ('start_date', 'end_date'),
        ]
        get_latest_by = 'start_date'


def json_value(val):
    try:
        json.loads(val)
    except Exception as e:
        raise ValidationError(
            _('%(value)s is not a valid json: %(error)s'),
            params={'value': val, 'error': str(e)},
        )


@python_2_unicode_compatible
class Config(models.Model):
    """
    the configuration for a whole logging config.
    one at a time can be active through the Trigger class. if None is active,
    it's the settings.LOGGING that is setup in the server.
    """

    KEEPT_CONFIG = ('loggers', )

    name = models.CharField(max_length=255)

    config_json = models.TextField(validators=[json_value])

    @classmethod
    def default(cls):
        if not hasattr(cls, "_default_settings"):
            cls._default_settings = cls(name="from settings")
            cls._default_settings.config = settings.LOGGING
        return cls._default_settings

    @classmethod
    def get_all_handlers(cls):
        """
        return a dict with all conigured handlers
        :return:
        """
        return settings.LOGGING.get('handlers', {})

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
        # we merge the loggers and handlers into the default config
        config['loggers'] = self.create_loggers(self.config.get('loggers', {}))
        config['handlers'] = self.merge_handlers(config.get('handlers', {}), self.config.get('handlers', {}))
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
            logger.filters = []
            logger.propagate = True

    @staticmethod
    def create_loggers(partial_config):
        """
        generate a correct logger config for the parital config
        :param partial_config:
        :return: the dict that can be passed into a logger configrator
        """
        default_val = {'propagate': True, 'handlers': [], 'filters': [], 'level': 'INFO'}

        res = {}
        for logger_name, logger_cfg in partial_config.items():
            current = res[logger_name] = {}
            current.update(default_val)
            current.update({k: v for k, v in logger_cfg.items() if k in default_val.keys()})
        return res

    @staticmethod
    def merge_handlers(settings_handlers, new_config):
        """
        merge the handler config. it don't add new handler, and just
        merge the level and the filters. nothing else
        :param settings_handlers:
        :param new_config:
        :return:
        """
        res = deepcopy(settings_handlers)
        for handler_name, handler_cfg_res in res.items():
            expected_handler_cfg = new_config.get(handler_name, {})
            handler_cfg_res.update({k: v for k, v in expected_handler_cfg.items() if k in ('filters', 'level')})
        return res

    def __str__(self):
        return self.name


def get_loggers():
    return {k: v for k, v in logging.Logger.manager.loggerDict.items() if isinstance(v, logging.Logger)}
