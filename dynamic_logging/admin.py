# -*- coding: utf-8 -*-
from django.contrib import admin
from django.core.urlresolvers import reverse
from django.db import models
from django.template.defaultfilters import safe
from django.utils.translation import ugettext_lazy as _

from dynamic_logging.scheduler import main_scheduler
from dynamic_logging.widgets import JsonLoggerWidget

from .models import Config, Trigger


@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'config_is_running', 'link_to_triggers', 'add_trigger']
    formfield_overrides = {
        models.TextField: {'label': 'settings', 'widget': JsonLoggerWidget},
    }

    def config_is_running(self, obj):
        return main_scheduler.current_trigger.config == obj

    config_is_running.boolean = True
    config_is_running.short_description = _('config is running')

    def link_to_triggers(self, obj):
        return safe('<a href="%s?config=%d">%d trigger(s)</a>' % (
            reverse('admin:dynamic_logging_trigger_changelist'),
            obj.pk,
            obj.triggers.count()
        ))

    def get_changeform_initial_data(self, request):
        return {'config_json': Config.default().config_json}

    def add_trigger(self, obj):
        return safe('<a href="%s?config=%d">add trigger</a>' % (reverse('admin:dynamic_logging_trigger_add'), obj.pk))

    class Media:
        css = {'all': ('admin/css/dynamic_logging.css',
                       'admin/css/forms.css')}

        js = ('admin/js/collapse.min.js', )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['current_trigger'] = main_scheduler.current_trigger
        extra_context['next_trigger'] = main_scheduler.next_timer and main_scheduler.next_timer.trigger
        # add extra data for handlers in each loggers
        loggers = list(main_scheduler.current_trigger.config.config.get('loggers', {}).values())
        if main_scheduler.next_timer:
            extra_context['next_trigger'] = main_scheduler.next_timer.trigger
            loggers += list(main_scheduler.next_timer.trigger.config.config.get('loggers', {}).values())

        return super(ConfigAdmin, self).changelist_view(request, extra_context)


@admin.register(Trigger)
class TriggerAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'is_active', 'config_is_running', 'link_to_config']
    date_hierarchy = 'start_date'
    list_filter = ['is_active', 'start_date', 'end_date', 'config']
    list_editable = ['is_active']

    def link_to_config(self, obj):
        return safe('<a href="%s">%s</a>' % (
            reverse('admin:dynamic_logging_config_change', args=(obj.config_id, )),
            obj.config.name
        ))

    def config_is_running(self, obj):
        return main_scheduler.current_trigger == obj

    config_is_running.boolean = True
    config_is_running.short_description = _('config is running')
