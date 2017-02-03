# -*- coding: utf-8 -*-
import datetime
import doctest
import logging.config

from django.conf import settings
from django.test.testcases import TestCase
from django.utils import timezone

from dynamic_logging.handlers import MockHandler
from dynamic_logging.models import Config, Trigger, get_loggers
from dynamic_logging.scheduler import Scheduler, main_scheduler


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite())
    return tests


def get_tz_date(dmy):
    """
    return a datetime with given day
    >>> get_tz_date('01-04-2017')
    datetime.datetime(2017, 4, 1, 0, 0, tzinfo=<UTC>)
    """
    ret = datetime.datetime.strptime(dmy, '%d-%m-%Y')
    tz = timezone.get_current_timezone()
    return tz.localize(ret)


class SchedulerTest(TestCase):
    def setUp(self):
        main_scheduler.disable()
        assert not main_scheduler.is_enabled()
        c = Config.objects.create(name='nothing logged')
        dates = [
            # #                            #  | jan  | fevrier
            ('01-03-2016', '01-03-2016'),  # 0|
            ('11-01-2017', '12-01-2017'),  # 1|==
            ('12-01-2017', '14-01-2017'),  # 2|  ==
            ('01-02-2017', '14-02-2017'),  # 3|          ======================
            ('03-02-2017', '08-02-2017'),  # 4|             ==========
            ('05-02-2017', '13-02-2017'),  # 5|               ===========
            ('16-02-2017', '25-02-2017'),  # 6|                                   ============
        ]
        for i, (start, end) in enumerate(dates):
            Trigger.objects.create(name='%d' % i,
                                   start_date=get_tz_date(start),
                                   end_date=get_tz_date(end),
                                   config=c)
        self.scheduler = Scheduler()

    def tearDown(self):
        main_scheduler.enable()

    def assertTriggerForDate(self, date, expected_tname, expected_next_wakeup, current=None):
        if current is not None:
            current = Trigger.objects.get(name=str(current))

        t, next_w = self.scheduler.get_next_wake(current=current, after=get_tz_date(date))
        self.assertEqual(t.name, str(expected_tname))
        if expected_next_wakeup is None:
            self.assertIsNone(next_w)
        else:
            self.assertEqual(next_w, get_tz_date(expected_next_wakeup))

    def test_all_bases_values(self):
        self.assertTriggerForDate('01-01-2017', '1', '11-01-2017')
        self.assertTriggerForDate('11-01-2017', '2', '12-01-2017', '1')
        self.assertTriggerForDate('13-01-2017', 'default settings', '14-01-2017', '2')
        self.assertTriggerForDate('15-01-2017', '3', '01-02-2017')
        self.assertTriggerForDate('02-02-2017', '4', '03-02-2017', '3')
        self.assertTriggerForDate('04-02-2017', '5', '05-02-2017', '4')
        self.assertTriggerForDate('06-02-2017', '3', '13-02-2017', '5')
        self.assertTriggerForDate('09-02-2017', '3', '13-02-2017', '5')
        self.assertTriggerForDate('13-02-2017', 'default settings', '14-02-2017', '3')
        self.assertTriggerForDate('15-02-2017', '6', '16-02-2017')
        self.assertTriggerForDate('17-02-2017', 'default settings', '25-02-2017', '6')
        self.assertTriggerForDate('17-02-2017', 'default settings', None)
        self.assertTriggerForDate('27-02-2017', 'default settings', None)


class TestSchedulerTimers(TestCase):
    def setUp(self):
        self.config = Config.objects.create(name='nothing', config={})
        main_scheduler.reset()
        main_scheduler.start_threads = False

    def tearDown(self):
        main_scheduler.reload()
        main_scheduler.start_threads = True

    def test_activate_trigger_at_creation(self):
        now_plus_2h = timezone.now() + datetime.timedelta(hours=2)
        now_less_2h = timezone.now() - datetime.timedelta(hours=2)
        # no trigger in fixtures
        self.assertIsNone(main_scheduler.next_timer)
        t = Trigger.objects.create(name='fake', config=self.config, start_date=now_less_2h, end_date=now_plus_2h)
        self.assertEqual(main_scheduler.current_trigger, t)
        self.assertEqual(main_scheduler.next_timer.at, now_plus_2h)

    def test_activate_right_trigger_at_creation(self):
        now_plus_2h = timezone.now() + datetime.timedelta(hours=2)
        now_plus_1h = timezone.now() + datetime.timedelta(hours=1)
        now_less_2h = timezone.now() - datetime.timedelta(hours=2)
        now_less_1h = timezone.now() - datetime.timedelta(hours=1)
        # no trigger in fixtures
        self.assertIsNone(main_scheduler.next_timer)
        t1 = Trigger.objects.create(name='fake', config=self.config, start_date=now_less_2h, end_date=now_plus_2h)
        t2 = Trigger.objects.create(name='fake', config=self.config, start_date=now_less_1h, end_date=now_plus_1h)
        self.assertEqual(main_scheduler.current_trigger, t2)
        self.assertEqual(main_scheduler.next_timer.at, now_plus_1h)
        self.assertEqual(main_scheduler.next_timer.trigger, t1)

    def test_wakeup_trigger_at_creation(self):
        now_plus_2h = timezone.now() + datetime.timedelta(hours=2)
        now_plus_1h = timezone.now() + datetime.timedelta(hours=1)
        # no trigger in fixtures
        self.assertIsNone(main_scheduler.next_timer)
        self.assertEqual(main_scheduler.current_trigger.name, 'default settings')
        t1 = Trigger.objects.create(name='fake', config=self.config, start_date=now_plus_2h, end_date=None)
        self.assertEqual(main_scheduler.current_trigger.name, 'default settings')
        self.assertEqual(main_scheduler.next_timer.at, now_plus_2h)
        self.assertEqual(main_scheduler.next_timer.trigger, t1)

        t2 = Trigger.objects.create(name='fake', config=self.config, start_date=now_plus_1h, end_date=None)
        self.assertEqual(main_scheduler.current_trigger.name, 'default settings')
        self.assertEqual(main_scheduler.next_timer.at, now_plus_1h)
        self.assertEqual(main_scheduler.next_timer.trigger, t2)

    def test_trigger_with_none_date(self):
        now_plus_2h = timezone.now() + datetime.timedelta(hours=2)
        now_less_2h = timezone.now() - datetime.timedelta(hours=2)
        # no trigger in fixtures
        self.assertIsNone(main_scheduler.next_timer)
        self.assertEqual(main_scheduler.current_trigger.name, 'default settings')
        t1 = Trigger.objects.create(name='fake', config=self.config, start_date=None, end_date=None)
        self.assertEqual(main_scheduler.current_trigger, t1)
        self.assertEqual(main_scheduler.next_timer, None)

        t2 = Trigger.objects.create(name='fake', config=self.config, start_date=now_less_2h, end_date=now_plus_2h)
        self.assertEqual(main_scheduler.current_trigger, t2)
        self.assertEqual(main_scheduler.next_timer.at, now_plus_2h)
        self.assertEqual(main_scheduler.next_timer.trigger, t1)

    def test_trigger_with_none_date_already_active(self):
        now_plus_2h = timezone.now() + datetime.timedelta(hours=2)
        now_less_2h = timezone.now() - datetime.timedelta(hours=2)
        # no trigger in fixtures
        self.assertIsNone(main_scheduler.next_timer)
        self.assertEqual(main_scheduler.current_trigger.name, 'default settings')

        t2 = Trigger.objects.create(name='fake', config=self.config, start_date=now_less_2h, end_date=now_plus_2h)
        self.assertEqual(main_scheduler.current_trigger, t2)
        self.assertEqual(main_scheduler.next_timer.at, now_plus_2h)
        self.assertEqual(main_scheduler.next_timer.trigger.name, 'default settings')

        # does not change anything
        t1 = Trigger.objects.create(name='fake', config=self.config, start_date=None, end_date=None)
        self.assertEqual(main_scheduler.current_trigger, t2)
        self.assertEqual(main_scheduler.next_timer.at, now_plus_2h)
        self.assertEqual(main_scheduler.next_timer.trigger, t1)

    def test_auto_reload_on_trigger_changes(self):
        now_plus_2h = timezone.now() + datetime.timedelta(hours=2)
        now_less_2h = timezone.now() - datetime.timedelta(hours=2)
        # no trigger in fixtures
        self.assertIsNone(main_scheduler.next_timer)
        t = Trigger.objects.create(name='fake', config=self.config, start_date=now_plus_2h)
        self.assertIsNotNone(main_scheduler.next_timer)
        self.assertEqual(main_scheduler.next_timer.at, now_plus_2h)
        self.assertEqual(main_scheduler.next_timer.trigger, t)
        # trigger already ended
        t.start_date = now_less_2h
        t.end_date = now_less_2h
        t.save()
        self.assertIsNone(main_scheduler.next_timer)
        # trigger active
        t.end_date = now_plus_2h
        t.save()
        self.assertIsNotNone(main_scheduler.next_timer)
        # trigger deleted
        t.delete()
        self.assertIsNone(main_scheduler.next_timer)

    def test_wake(self):
        now_plus_2h = timezone.now() + datetime.timedelta(hours=2)
        now_plus_4h = timezone.now() + datetime.timedelta(hours=4)
        # no trigger in fixtures
        self.assertIsNone(main_scheduler.next_timer)
        t = Trigger.objects.create(name='fake', config=self.config, start_date=now_plus_2h, end_date=now_plus_4h)

        self.assertEqual(main_scheduler.current_trigger, Trigger.default())
        main_scheduler.wake(t, now_plus_2h)
        self.assertEqual(main_scheduler.current_trigger, t)


class ConfigApplyTest(TestCase):
    def tearDown(self):
        # reset the default config
        Config.default().apply()

    def test_default_config_by_default(self):
        loggers = get_loggers()
        for name, configured in settings.LOGGING['loggers'].items():
            self.assertEqual(len(configured['handlers']), len(loggers[name].handlers))

    def test_empty_config(self):
        cfg = Config(name='empty', config_json='{"loggers": {}}')
        cfg.apply()
        for logger in get_loggers().values():
            self.assertEqual(logger.handlers, [])

    def test_simple_config(self):
        cfg = Config(name='empty', config_json='{"loggers": {"dynamic_logging": {"handlers": ["console"]}}}')
        cfg.apply()
        for logger in get_loggers().values():
            if logger.name in cfg.config['loggers']:

                self.assertEqual(len(logger.handlers), 1)
            else:
                self.assertEqual(logger.handlers, [])

    def test_level_config(self):

        loggers = get_loggers()

        self.assertEqual(loggers['testproject.testapp'].level, logging.DEBUG)  # default to info

        cfg = Config(name='empty')
        cfg.config = {"loggers": {
            "dynamic_logging": {
                "handlers": ["console", "null"],
                "level": "ERROR",
            },
            "testproject.testapp": {
                "handlers": ["devnull"],
                "level": "WARNING",
            }
        }}
        cfg.apply()
        self.assertEqual(loggers['testproject.testapp'].level, logging.WARNING)  # default to info
        for logger in get_loggers().values():
            logger_config = cfg.config['loggers'].get(logger.name)
            if logger_config:
                self.assertEqual(len(logger.handlers), len(logger_config['handlers']))
                self.assertEqual(logger.level, getattr(logging, logger_config["level"]))

            else:
                self.assertEqual(logger.handlers, [])

    def test_messages_passed(self):
        with MockHandler.capture() as messages:
            self.assertEqual(messages['debug'], [])
            logger = logging.getLogger('testproject.testapp')
            logger.debug("couocu")
            # handler not attached to this logger
            self.assertEqual(messages['debug'], [])
        # setup new config
        cfg = Config(name='empty')
        cfg.config = {"loggers": {
            "dynamic_logging": {
                "handlers": ["console", "null"],
                "level": "ERROR",
            },
            "testproject.testapp": {
                "handlers": ["mock"],
                "level": "WARN",
            }
        }}
        cfg.apply()
        # log debug ineficient
        logger.debug("couocu")
        with MockHandler.capture() as messages:
            self.assertEqual(messages['debug'], [])
            self.assertEqual(messages['warning'], [])
            logger.warn("hey")
            self.assertEqual(messages['debug'], [])
            self.assertEqual(messages['warning'], ['hey'])

    def test_config_reversed(self):
        logger = logging.getLogger('testproject.testapp')
        # handler not attached to this logger
        # setup new config
        cfg = Config(name='empty')
        cfg.config = {"loggers": {
            "dynamic_logging": {
                "handlers": ["console", "null"],
                "level": "ERROR",
            },
            "testproject.testapp": {
                "handlers": ["mock"],
                "level": "WARN",
            }
        }}
        cfg.apply()
        # log debug ineficient
        with MockHandler.capture() as messages:
            logger.warn("hey")
            self.assertEqual(messages['warning'], ['hey'])
            logger.warn("hey")
            self.assertEqual(messages['warning'], ['hey', 'hey'])

        with MockHandler.capture() as messages:
            # default config does not add to mockhandler
            Config.default().apply()
            logger.warn("hey")
            self.assertEqual(messages['warning'], [])
