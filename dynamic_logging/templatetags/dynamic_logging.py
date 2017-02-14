# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

from django import template

from dynamic_logging.models import Config
from dynamic_logging.scheduler import main_scheduler

register = template.Library()


@register.filter
def getitem(dict_, key):
    return dict_.get(key)


@register.inclusion_tag('dynamic_logging/display_config.html')
def display_config(config=None):
    if config is None:
        config = main_scheduler.current_trigger.config
    try:
        config.config
    except ValueError:
        return {}
    return {
        'config': config,
        'handlers': Config.get_all_handlers()
    }
