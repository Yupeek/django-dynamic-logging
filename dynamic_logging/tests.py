# -*- coding: utf-8 -*-
import datetime
import doctest

from django.test.testcases import TestCase
from django.utils import timezone

from dynamic_logging.models import Config, Scheduler, Trigger


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

