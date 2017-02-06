# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

from django import template

from dynamic_logging.models import Config
from dynamic_logging.scheduler import main_scheduler

register = template.Library()


@register.filter
def getitem(dict, key):
    return dict[key]


@register.inclusion_tag('dynamic_logging/display_config.html')
def display_config(config=None):
    try:
        config.config
    except ValueError:
        return {}
    if config is None:
        config = main_scheduler.current_trigger.config
    return {
        'config': config,
        'handlers': Config.get_all_handlers()
    }
