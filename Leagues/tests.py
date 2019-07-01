from django.urls import reverse, resolve
from django.test import TestCase
from Leagues.views import home
from Leagues.models import League,Field,Team, Division

# Create your tests here.


class HomeTests(TestCase):
    def test_home_view_status_code(self):
        url = reverse('home')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_home_url_resolves_home_view(self):
        view = resolve('/')
        self.assertEquals(view.func, home)


class BoardTopicsTests(TestCase):
    def setUp(self):
        League.objects.create(name='Test Team', description='just for testing')

    def test_board_topics_view_success_status_code(self):
        url = reverse('leagues', kwargs={'pk': 1})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_board_topics_view_not_found_status_code(self):
        url = reverse('leagues', kwargs={'pk': 99})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 404)
