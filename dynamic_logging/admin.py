# -*- coding: utf-8 -*-


from django.contrib import admin
from .models import Config, Trigger
import dynamic_logging.views

@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    pass


@admin.register(Trigger)
class TriggerAdmin(admin.ModelAdmin):
    pass
