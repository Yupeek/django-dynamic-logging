from django.test import TestCase

# Create your tests here.


class TestPages(TestCase):

    def test_200(self):
        res = self.client.get('/testapp/ok/')
        self.assertEqual(res.status_code, 200)

    def test_401(self):
        res = self.client.get('/testapp/error401/')
        self.assertEqual(res.status_code, 401)
