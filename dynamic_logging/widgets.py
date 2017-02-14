# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import json
import logging
from collections import OrderedDict
from copy import deepcopy

from django.conf import settings
from django.forms.widgets import Textarea
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from dynamic_logging.models import Config

logger = logging.getLogger(__name__)


class JsonLoggerWidget(Textarea):
    class Media:
        js = (
            'admin/js/minimal.js',
            'admin/js/logging_widget.js',
        )

    def merge_handlers_value(self, current_val):
        """
        return the current val merged with the existing handlers config
        :param current_val:
        :return:
        """
        res = deepcopy(settings.LOGGING['handlers'])
        for name, handler in res.items():
            handler.update({k: v for k, v in current_val[name].items() if k in ('filters', 'level')})
        res = OrderedDict(sorted(res.items()))
        return res

    def render(self, name, value, attrs=None):
        attrs = attrs or {}
        try:
            data = json.loads(value)
            data['handlers'] = self.merge_handlers_value(data.get('handlers', {}))
            data['loggers'] = OrderedDict(sorted(data['loggers'].items()))
            value = json.dumps(data)
        except ValueError:
            pass
        attrs['style'] = attrs.get('style', '') + ' display: none;'
        res = super(JsonLoggerWidget, self).render(name, value, attrs)
        extra = {
            'handlers': list(Config.get_all_handlers().keys()),
            'filters': list(Config.get_all_filters().keys()),
            'loggers': list()
        }

        return res + format_html(
            '<div id="{anchorid}"></div>'
            '<script type="application/javascript">'
            '(function ($) {{'
            '   $(function() {{'
            '       logging_widget($("#{anchorid}"), $("#{areaid}"), {extra});'
            '   }});'
            '}}(jQuery));'
            '</script>',
            anchorid=attrs.get('id', name) + '_display',
            areaid=attrs.get('id', name),
            extra=mark_safe(json.dumps(extra))
        )
