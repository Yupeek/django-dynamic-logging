from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test import TestCase
# Create your tests here.
from django.test.utils import override_settings

from dynamic_logging.handlers import MockHandler
from dynamic_logging.models import Config, Trigger
from dynamic_logging.scheduler import main_scheduler
from dynamic_logging.tests import now_plus


class TestPages(TestCase):
    def setUp(self):
        pass

    def test_200(self):
        res = self.client.get('/testapp/ok/')
        self.assertEqual(res.status_code, 200)

    def test_401(self):
        res = self.client.get('/testapp/error401/')
        self.assertEqual(res.status_code, 401)

    def test_raise(self):
        self.assertRaises(Exception, self.client.get, '/testapp/error500/')

    def test_log_no_cfg(self):
        with MockHandler.capture() as messages:
            res = self.client.get('/testapp/log/DEBUG/testproject.testapp/')
            self.assertEqual(res.status_code, 200)
            self.assertEqual(messages['debug'], [])

    def test_log_with_cfg(self):
        cfg = Config(name='mocklog')
        cfg.config = {"loggers": {
            "testproject.testapp": {
                "handlers": ["mock"],
                "level": "WARN",
            }
        }}
        cfg.apply()
        with MockHandler.capture() as messages:
            res = self.client.get('/testapp/log/DEBUG/testproject.testapp/')
            self.assertEqual(res.status_code, 200)
            self.assertEqual(messages['debug'], [])

    def test_log_bad_level(self):
        self.assertRaises(Exception, self.client.get, '/testapp/log/OOPS/testproject.testapp/')


@override_settings(
    DYNAMIC_LOGGING={"upgrade_propagator": {'class': "dynamic_logging.propagator.ThreadSignalPropagator", 'config': {}}
                     }
)
class TestAdminContent(TestCase):

    def setUp(self):
        super(TestAdminContent, self).setUp()
        u = get_user_model().objects.create(username='admin', is_staff=True, is_superuser=True)
        """:type: django.contrib.auth.models.User"""
        u.set_password('password')
        u.save()
        self.client.login(username='admin', password='password')
        main_scheduler.reload()
        self.c = c = Config.objects.create(name='my_config', config_json='{"loggers":{"blablabla":{"level":"ERROR",'
                                                                         '"handlers":["console"],"propagate":true}}}')
        self.t = Trigger.objects.create(name='in1hour', config=c, start_date=now_plus(2), end_date=now_plus(4))

    def tearDown(self):
        main_scheduler.reset()

    def test_logging_in_admin(self):
        response = self.client.get('/admin/')
        self.assertContains(response, 'Trigger')

    def test_config_list(self):
        response = self.client.get(reverse('admin:dynamic_logging_config_changelist'))
        self.assertContains(response, 'default settings')

    def test_trigger_list(self):
        response = self.client.get(reverse('admin:dynamic_logging_trigger_changelist'))
        self.assertContains(response, 'in1hour')

    def test_config_change(self):
        response = self.client.get(reverse('admin:dynamic_logging_config_change', args=(self.t.pk,)))
        self.assertContains(response, 'my_config')

    def test_trigger_change(self):
        response = self.client.get(reverse('admin:dynamic_logging_trigger_change', args=(self.t.pk,)))
        self.assertContains(response, 'in1hour')

    def test_config_add(self):
        response = self.client.get(reverse('admin:dynamic_logging_config_add'))
        self.assertEqual(response.status_code, 200)

    def test_trigger_add(self):
        response = self.client.get(reverse('admin:dynamic_logging_trigger_add'))
        self.assertEqual(response.status_code, 200)

    def test_trigger_summary(self):
        self.t.start_date = now_plus(-2)
        self.t.save()
        response = self.client.get(reverse('admin:app_list', kwargs={'app_label': 'dynamic_logging'}))
        self.assertContains(response, 'blablabla')

    def test_display_bad_conf(self):
        self.t.start_date = now_plus(-2)
        self.t.save()
        self.t.config.config_json = 'oops bad json'
        self.t.config.save()

        response = self.client.get(reverse('admin:app_list', kwargs={'app_label': 'dynamic_logging'}))
        self.assertNotContains(response, 'blablabla')

    def test_trigger_broken(self):
        self.t.config_id = 99
        self.t.save()
        self.assertIn('<no config>', str(Trigger.objects.get(pk=self.t.pk)))

    def test_create_bad_config(self):
        res = self.client.post(reverse('admin:dynamic_logging_config_add'), data={
            'name': 'new config',
            'config_json': '{bda bconfig oops'
        })
        self.assertContains(res, 'not a valid json')

    def test_wsgi_import(self):
        import testproject.wsgi  # NOQA
