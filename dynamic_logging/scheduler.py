# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import functools
import logging
import threading

from django.utils import timezone

from dynamic_logging.models import Trigger

logger = logging.getLogger(__name__)


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
        self._enabled = True
        self.current_trigger = Trigger.default()
        """
        :type: Trigger
        """
        self.start_thread = True
        """
        a bool to prevent the threads to start, for testing purpose
        """
        self.reload_timer = None
        """
        the local timer for the defered reload
        """
        self.trigger_applied = threading.Event()
        """
        a simple Event used to test each time a trigger is applied
        """

    def disable(self):
        """
        disable this scheduler. reload has no effect
        :return:
        """
        if self._enabled:
            self._enabled = False
            self.reset()

    def enable(self):
        """
        reenable the scheduler.
        set the next timer to the next Trigger
        :return:
        """
        if not self._enabled:
            self._enabled = True
            self.reload()

    def is_enabled(self):
        return self._enabled

    @staticmethod
    def get_next_wake(current=None, after=None):
        """
        function that return the next trigger to apply and the date at which it may occure

        :param Trigger current: the current trigger active (which won't be reenabled
        :param datetime after:  the date to use to check current time
        :return: the next trigger to enable, with the date it whith it occure. date can be none if the trigger shall be
                 enabled right now
        :rtype: (Trigger, datetime.datetime)
        """
        after = after or timezone.now()
        # next wake is the earliest of :
        # - the end of the current one
        # - the start of a new one

        try:
            next_trigger = Trigger.objects.filter(is_active=True, start_date__gt=after).earliest('start_date')
        except Trigger.DoesNotExist:
            # no next trigger
            next_trigger = None  # type: Trigger

        # boolean opperation is
        # w = current trigger is null
        # x = current trigger's end date is null =>_trigger don't end
        # y = no next trigger
        # z = current trigger end befor the next one start

        # results are
        # a = activate next trigger at next trigger start date
        # b = find best trigger at current one end date
        # c = no trigger

        # boolean simplification lead to:
        # c = y and not b
        # a = not y and not b
        # b = not w and not x and (y or (not y and z))

        # start with b case => find best trigger at the end of the current one
        if (
            current is not None  # not w
            and current.end_date is not None  # not x
            and (next_trigger is None or current.end_date < next_trigger.start_date)
        ):
            # b =>
            try:
                last_active = Trigger.objects.filter(is_active=True).valid_at(current.end_date).earliest('start_date')
            except Trigger.DoesNotExist:
                # no trigger active at the end of the current one, the default will be enabled
                last_active = Trigger.default()
            return last_active, current.end_date
        elif next_trigger is None:  # case c = not b and y
            return current or Trigger.default(), None
        else:  # case a (last case)
            return next_trigger, next_trigger.start_date

    def set_next_wake(self, trigger, at):
        logger.debug("next trigger to enable : %s at %s", trigger, at, extra={'next_date': at})
        with self._lock:
            self.reset_timer()
            interval = (at - timezone.now()).total_seconds()
            self.next_timer = threading.Timer(interval,
                                              functools.partial(self.wake, trigger=trigger, date=at))
            self.next_timer.name = 'ApplyTimer for %s' % trigger.pk
            self.next_timer.daemon = True  # prevent program hanging until netx trigger
            self.next_timer.trigger = trigger
            self.next_timer.at = at
            if self.start_thread:
                # in some tests, we skip the overload of starting thread for nothing.
                self.next_timer.start()

    def reset(self):
        """
        reset the logging to the default settings. disable the timer to change it
        :return:
        """
        with self._lock:
            self.reset_timer()
            self.current_trigger = Trigger.default()

    def reset_timer(self):
        """
        reset the timer
        :return:
        """
        with self._lock:
            if self.next_timer is not None:
                self.next_timer.cancel()
                self.next_timer = None
            if self.reload_timer is not None:
                self.reload_timer.cancel()
                self.reload_timer = None

    def activate_current(self):
        """
        activate the current trigger
        :return:
        """
        try:
            t = Trigger.objects.filter(is_active=True).valid_at(timezone.now()).latest('start_date')
        except Trigger.DoesNotExist:
            return None
        try:
            self.apply(t)
            return t
        except ValueError as e:
            logger.exception("error with current logger activation trigger=%s, config=%s => %s",
                             t.id, t.config_id, str(e))
            return None

    def reload(self, interval=None):
        """
        cancel the timer and the next trigger, and
        compute the next one. can be done after an interval to delay the setup for some time.
        :return:
        """
        if self._enabled:
            with self._lock:
                if self.reload_timer is not None:
                    self.reload_timer.cancel()
                if interval is not None:
                    self.reload_timer = t = threading.Timer(interval, self.reload)
                    t.name = "ReloadTimer"
                    t.daemon = True
                    t.start()
                    self.reload_timer = t
                    return

                self.reset_timer()
                current = self.activate_current()
                trigger, at = self.get_next_wake(current=current)
                if at:
                    self.set_next_wake(trigger, at)
                else:
                    # no date to wake. we apply now this trigger and so be it
                    self.apply(trigger)
                    self.current_trigger = trigger

    def wake(self, trigger, date):
        """
        function called each time a timer arrived at expiration

        :return:
        """
        logger.debug("wake to enable trigger %s at %s", trigger, date, extra={'expected_date': date})
        next_trigger, at = self.get_next_wake(current=trigger, after=date)
        with self._lock:
            self.apply(trigger)
            self.current_trigger = trigger
            # get the next trigger valid at the current expected date
            # we don't use timezone.now() to prevent the case where threading.Timer wakeup some ms befor the expected
            # date
            if at:
                self.set_next_wake(next_trigger, at)

    def apply(self, trigger):
        logger.debug('applying %s', trigger, extra={'trigger': trigger, 'config': trigger.config.config_json})
        trigger.apply()
        self.current_trigger = trigger
        self.trigger_applied.set()


main_scheduler = Scheduler()
