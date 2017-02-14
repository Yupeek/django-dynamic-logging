# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


DEFAULT_VALUES = {
    "signals_auto":  ('db_debug',),  # setup all automatic signal handlers
    "upgrade_propagator": {'class': "dynamic_logging.propagator.ThreadSignalPropagator", 'config': {}}
}


def get_setting(name):
    """
    return the settings of dynamic_logging by his name. will take the value from django settings if it exists
    :param name: the name of the setting
    :return: the value
    :raise: KeyError if the settings does not exist
    """

    dj_settings = getattr(settings, "DYNAMIC_LOGGING", {})
    return dj_settings.get(name, None) or DEFAULT_VALUES[name]
