# -*- coding: utf-8 -*-
import datetime
import doctest
import json
import logging.config
import threading
from unittest.case import SkipTest

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test.testcases import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from dynamic_logging.handlers import MockHandler
from dynamic_logging.models import Config, Trigger
from dynamic_logging.propagator import AmqpPropagator, TimerPropagator
from dynamic_logging.scheduler import Scheduler, main_scheduler
from dynamic_logging.signals import AutoSignalsHandler
from dynamic_logging.templatetags.dynamic_logging import display_config, getitem


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


def now_plus(hours):
    return timezone.now() + datetime.timedelta(hours=hours)


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


@override_settings(
    DYNAMIC_LOGGING={"upgrade_propagator": {'class': "dynamic_logging.propagator.ThreadSignalPropagator", 'config': {}}
                     }
)
class TestSchedulerTimers(TestCase):
    def setUp(self):
        self.config = Config.objects.create(name='nothing', config={})
        main_scheduler.reset()
        main_scheduler.start_threads = False

    def tearDown(self):
        main_scheduler.reload()
        main_scheduler.start_threads = True

    def test_activate_trigger_at_creation(self):
        now_plus_2h = now_plus(2)
        now_less_2h = now_plus(-2)
        # no trigger in fixtures
        self.assertIsNone(main_scheduler.next_timer)
        t = Trigger.objects.create(name='fake', config=self.config, start_date=now_less_2h, end_date=now_plus_2h)
        self.assertEqual(main_scheduler.current_trigger, t)
        self.assertEqual(main_scheduler.next_timer.at, now_plus_2h)

    def test_activate_right_trigger_at_creation(self):
        now_plus_2h = now_plus(2)
        now_plus_1h = now_plus(1)
        now_less_2h = now_plus(-2)
        now_less_1h = now_plus(-1)
        # no trigger in fixtures
        self.assertIsNone(main_scheduler.next_timer)
        t1 = Trigger.objects.create(name='fake', config=self.config, start_date=now_less_2h, end_date=now_plus_2h)
        t2 = Trigger.objects.create(name='fake', config=self.config, start_date=now_less_1h, end_date=now_plus_1h)
        self.assertEqual(main_scheduler.current_trigger, t2)
        self.assertEqual(main_scheduler.next_timer.at, now_plus_1h)
        self.assertEqual(main_scheduler.next_timer.trigger, t1)

    def test_wakeup_trigger_at_creation(self):
        now_plus_2h = now_plus(2)
        now_plus_1h = now_plus(1)
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
        now_plus_2h = now_plus(2)
        now_less_2h = now_plus(-2)
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
        now_plus_2h = now_plus(2)
        now_less_2h = now_plus(-2)
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
        now_plus_2h = now_plus(2)
        now_less_2h = now_plus(-2)
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

    def test_is_active_usage(self):
        t = Trigger.objects.create(name='fake', config=self.config, start_date=now_plus(2))
        t2 = Trigger.objects.create(name='fake', config=self.config, start_date=now_plus(3))

        self.assertEqual(main_scheduler.next_timer.trigger, t)
        # trigger already ended
        t.is_active = False
        t.save()
        self.assertEqual(main_scheduler.next_timer.trigger, t2)
        t2.start_date = now_plus(1)
        t2.save()
        self.assertEqual(main_scheduler.next_timer.trigger, t2)
        t.is_active = True
        t.save()
        self.assertEqual(main_scheduler.next_timer.trigger, t2)

    def test_wake(self):
        now_plus_2h = now_plus(2)
        now_plus_4h = now_plus(4)
        # no trigger in fixtures
        self.assertIsNone(main_scheduler.next_timer)
        t = Trigger.objects.create(name='fake', config=self.config, start_date=now_plus_2h, end_date=now_plus_4h)

        self.assertEqual(main_scheduler.current_trigger, Trigger.default())
        main_scheduler.wake(t, now_plus_2h)
        self.assertEqual(main_scheduler.current_trigger, t)


@override_settings(
    DYNAMIC_LOGGING={"upgrade_propagator": {'class': "dynamic_logging.propagator.DummyPropagator", 'config': {}}}
)
class AmqpPropagatorTest(TestCase):
    amqp_url = 'amqp://guest:guest@localhost:5672/%2F'

    @classmethod
    def setUpClass(cls):
        main_scheduler.reset_timer()
        super(AmqpPropagatorTest, cls).setUpClass()

    def setUp(self):
        super(AmqpPropagatorTest, self).setUp()
        try:
            import pika
            import pika.exceptions

        except ImportError:
            raise SkipTest("pika is not importable")

        amqp_url = self.amqp_url
        try:
            self.connection = pika.BlockingConnection(pika.URLParameters(amqp_url))
        except pika.exceptions.ConnectionClosed:
            raise SkipTest("no rabbitmq running for %s" % amqp_url)

    def test_message_sent(self):
        # this test try to run a temporary connection and check if the AmqpPropagator
        # send a message wherever a Config/Trigger is created/updated

        # all this threading stuff is ugly... i know
        propagator = AmqpPropagator({'url': self.amqp_url, 'echange_name': 'my_test_exchange'})

        def fake_reload(*args, **kwargs):
            pass

        propagator.reload_scheduler = fake_reload
        propagator.setup()
        np = []
        channel = self.connection.channel()

        called = threading.Event()

        def callback(ch, method, properties, body):
            called.set()
            np.append(1)

        ended = threading.Event()
        start = threading.Event()

        def target():
            start.set()

            while channel._consumer_infos:
                channel.connection.process_data_events(time_limit=1)
            ended.set()

        queue = channel.queue_declare(exclusive=True)
        channel.queue_bind(exchange='my_test_exchange', queue=queue.method.queue, routing_key='')
        channel.basic_consume(callback, queue=queue.method.queue)
        self.assertEqual(np, [])
        thr = threading.Thread(target=target)
        thr.daemon = True
        thr.start()

        if not start.wait(4):
            raise Exception("failed to start cunsumer")
        c = Config.objects.create(name="name", config_json='{}')
        self.assertTrue(called.wait(4))
        called.clear()
        self.assertEqual(np, [1])
        c.config_json = '{}'
        c.save()
        self.assertTrue(called.wait(1))
        called.clear()
        self.assertEqual(np, [1, 1])
        Trigger.objects.create(name='lolilol', end_date=None, start_date=None, config=c)
        self.assertTrue(called.wait(1))
        called.clear()
        self.assertEqual(np, [1, 1, 1])
        channel.stop_consuming()
        self.connection.close()
        self.assertTrue(ended.wait(4))
        propagator.teardown()

    def test_message_received(self):
        # this test try to run a temporary connection and check if the AmqpPropagator
        # listen for message to trigger a scheduler_reload

        config = Config.objects.create(name="name", config_json='{}')
        Trigger.objects.create(name='lolilol', end_date=None, start_date=None, config=config)

        propagator = AmqpPropagator({'url': self.amqp_url, 'echange_name': 'my_test_exchange'})
        reload_called = threading.Event()

        def fake_reload(*args, **kwargs):
            reload_called.set()

        propagator.reload_scheduler = fake_reload
        propagator.setup()
        channel = self.connection.channel()

        self.assertIsNone(main_scheduler.current_trigger.pk)
        main_scheduler.trigger_applied.clear()
        channel.basic_publish(exchange='my_test_exchange', routing_key="", body="")

        self.assertTrue(reload_called.wait(1))
        propagator.teardown()


@override_settings(
    DYNAMIC_LOGGING={"upgrade_propagator": {'class': "dynamic_logging.propagator.DummyPropagator", 'config': {}}}
)
class TimerPropagatorTest(TestCase):

    def test_timer_check_call(self):
        propagator = TimerPropagator({'interval': 0.15})
        check_called = threading.Event()

        def fake_check(*args, **kwargs):
            check_called.set()

        propagator.check_new_config = fake_check

        propagator.setup()
        self.assertTrue(check_called.wait(1))
        propagator.teardown()
        check_called.clear()
        self.assertFalse(check_called.wait(0.5))

    def test_timer_propagator(self):
        # setup proagator
        propagator = TimerPropagator({'interval': 0.25})
        reload_called = threading.Event()

        def fake_reload(*args, **kwargs):
            reload_called.set()

        propagator.reload_scheduler = fake_reload
        propagator.check_new_config()
        self.assertFalse(reload_called.isSet())
        reload_called.clear()
        # setup models to trigger propagator
        config = Config.objects.create(name="name", config_json='{}')
        t = Trigger.objects.create(name='lolilol', end_date=None, start_date=None, config=config)
        # start test :
        propagator.check_new_config()
        self.assertTrue(reload_called.isSet())
        # detect supressions
        reload_called.clear()
        t.delete()
        propagator.check_new_config()
        self.assertTrue(reload_called.isSet())
        # teardown and check nothing changed


class ConfigApplyTest(TestCase):

    def setUp(self):
        Config.default().apply()
        main_scheduler.reset_timer()

    def tearDown(self):
        # reset the default config
        Config.default().apply()
        main_scheduler.reset_timer()

    def test_config_property_setter(self):
        c = Config(name='lol', config_json='{}')
        c.config = {
            'handlers': {
                'added': {}
            },
            'loggers': {
                'console': {
                    'level': 'CRITICAL',
                    'class': 'missed'
                }
            }
        }
        self.assertEqual(
            json.loads(c.config_json),
            {'handlers': {'added': {}}, 'loggers': {'console': {'level': 'CRITICAL'}}}
        )

    def test_config_property_getter(self):
        c = Config(name='lol', config_json='{}')
        self.maxDiff = None
        c.config_json = json.dumps({
            'handlers': {
                'added': {}
            },
            'loggers': {
                'console': {
                    'level': 'CRITICAL',
                    'class': 'missed'
                }
            }
        })
        self.assertEqual(
            c.config,
            {'handlers': {'added': {}}, 'loggers': {'console': {'level': 'CRITICAL'}}}
        )

    def test_config_property_getter_empty(self):
        c = Config(name='lol', config_json='')
        self.assertEqual(c.config, {})

    def test_default_config_by_default(self):
        loggers = Config.get_existing_loggers()
        for name, configured in settings.LOGGING['loggers'].items():
            self.assertEqual(len(configured['handlers']), len(loggers[name].handlers))

    def test_empty_config(self):
        cfg = Config(name='empty', config_json='{"loggers": {}}')
        cfg.apply()
        for logger in Config.get_existing_loggers().values():
            self.assertEqual(logger.handlers, [])

    def test_simple_config(self):
        cfg = Config(name='empty', config_json='{"loggers": {"dynamic_logging": {"handlers": ["console"]}}}')
        cfg.apply()
        for logger in Config.get_existing_loggers().values():
            if logger.name in cfg.config['loggers']:

                self.assertEqual(len(logger.handlers), 1)
            else:
                self.assertEqual(logger.handlers, [])

    def test_level_config(self):

        loggers = Config.get_existing_loggers()

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
        for logger in Config.get_existing_loggers().values():
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

    def test_filter_apply(self):
        # handler not attached to this logger
        # setup new config
        cfg_filtered = Config(name='empty')
        cfg_filtered.config = {"loggers": {
            "testproject.testapp": {
                "handlers": ["mock"],
                "level": "WARN",
                "filters": ['polite']
            }
        }}
        cfg_passall = Config(name='empty')
        cfg_passall.config = {"loggers": {
            "testproject.testapp": {
                "handlers": ["mock"],
                "level": "WARN",
                "filters": []
            }
        }}
        logger_old = logging.getLogger('testproject.testapp')

        cfg_filtered.apply()
        logger = logging.getLogger('testproject.testapp')
        self.assertEqual(logger, logger_old)

        # log debug ineficient
        with MockHandler.capture() as messages:
            self.assertEqual(len(logger.filters), 1)
            logger.warn("hey")
            self.assertEqual(messages['warning'], [])
            logger.warn("hello, you")
            self.assertEqual(messages['warning'], ['hello, you'])

        with MockHandler.capture() as messages:
            # default config does not add
            cfg_passall.apply()
            logger.warn("hey")
            self.assertEqual(messages['warning'], ['hey'])
            logger.warn("hello, you")
            self.assertEqual(messages['warning'], ['hey', 'hello, you'])

    def test_handler_merging(self):
        original_cfg = {
            'mail_admins': {
                'level': 'ERROR',
                'filters': ['require_debug_false'],
                'class': 'django.utils.log.AdminEmailHandler',
            },
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'colored',
                'propagate': False
            }
        }
        new_cfg = {
            'dont exists': {  # ignored
                'level': 'ERROR'
            },
            'console': {
                'level': 'INFO',  # ok
                'class': 'logging.HACKME',  # ignored
                'formatter': 'prout',  # ignored
                'ignored': True,  # ignored
                'filters': ['nofilter']  # ok
            }
        }
        res = Config.merge_handlers(original_cfg, new_cfg)
        self.assertEqual(res, {
            'mail_admins': {
                'level': 'ERROR',
                'filters': ['require_debug_false'],
                'class': 'django.utils.log.AdminEmailHandler',
            },
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'colored',
                'propagate': False,
                'filters': ['nofilter']
            }
        })

    def test_loggers_creation(self):
        asked_cfg = {
            'django': {
                'level': 'ERROR',
                'propagate': False,
            },
            'django.request': {
                'handlers': ['null'],
                'filters': ['filter']
            },
            'testproject.testapp': {
                'handlers': ['null', 'devnull'],
            },
            'lol': {
                'ignored': 'lol',
            }
        }
        self.maxDiff = None
        self.assertEqual(Config.create_loggers(asked_cfg), {
            'django': {
                'handlers': [],
                'level': 'ERROR',
                'propagate': False,
                'filters': []
            },
            'django.request': {
                'handlers': ['null'],
                'level': 'INFO',
                'propagate': True,
                'filters': ['filter']
            },
            'testproject.testapp': {
                'handlers': ['null', 'devnull'],
                'level': 'INFO',
                'propagate': True,
                'filters': []
            },
            'lol': {
                'handlers': [],
                'level': 'INFO',
                'propagate': True,
                'filters': []
            },
        })


class TestTag(TestCase):
    def test_display_config_current_auto(self):
        config = display_config()
        self.assertEqual(config['config'], main_scheduler.current_trigger.config)
        self.assertGreater(len(config['handlers']), 0)

    def test_display_config_given(self):
        c = Config(name="lol", config_json='{}')
        config = display_config(c)
        self.assertEqual(config['config'], c)
        self.assertGreater(len(config['handlers']), 0)

    def test_display_fallback_bad_config(self):
        c = Config(name="lol", config_json='}')
        self.assertRaises(ValueError, getattr, c, 'config')
        config = display_config(c)
        self.assertEqual(config, {})

    def test_getitem(self):
        self.assertEqual(getitem({'a': True}, 'a'), True)


class SignalHandlingTest(TestCase):

    def test_auto_signal_handler(self):
        a = AutoSignalsHandler()
        self.assertRaises(ImproperlyConfigured, a.apply, ('dontexists',))

    def test_auto_signal_customise(self):
        cnt = []

        def wrapper():
            cnt.append(1)
        a = AutoSignalsHandler()
        a.extra_signals['exists'] = wrapper
        a.apply(('exists',))
        self.assertEqual(cnt, [1])

    def test_auto_signal_overwrite(self):
        cnt = []

        def wrapper():
            cnt.append(1)
        a = AutoSignalsHandler()
        a.extra_signals['db_debug'] = wrapper
        a.apply(('db_debug',))
        self.assertEqual(cnt, [1])

    def test_db_debug_debug_bad_logger(self):
        # bad
        config = Config(name='nothing')
        config.config = {"loggers": {
            "django.db": {
                "handlers": ["mock"],
                "level": "DEBUG",
            }
        }}
        config.apply()

        with MockHandler.capture() as msg:
            Config.objects.count()
        self.assertEqual(msg['debug'], [])

    def test_db_debug_not_debug(self):
        # bad
        config = Config(name='nothing')
        config.config = {"loggers": {
            "django.db": {
                "handlers": ["mock"],
                "level": 15,
            }
        }}
        config.apply()

        with MockHandler.capture() as msg:
            Config.objects.count()
        self.assertEqual(msg['debug'], [])

    def test_db_debug_debug_ok(self):
        config = Config(name='nothing')

        config.config = {"loggers": {
            "django.db.backends": {
                "handlers": ["mock"],
                "level": "DEBUG",
            }
        }}
        config.apply()

        with MockHandler.capture() as msg:
            Config.objects.count()
        self.assertEqual(len(msg['debug']), 1)
        self.assertTrue('SELECT COUNT(*)' in msg['debug'][0])
