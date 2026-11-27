from django.test import TestCase, Client
from django.urls import reverse


class TestOverview(TestCase):
    def setUp(self):
        self.client = Client()

    def test_overview_shows_stats(self):
        response = self.client.get(reverse("overview"))

        self.assertEqual(response.status_code, 200)
        labels = [stat["label"] for stat in response.context["hero_stats"]["stats"]]
        # No questions exist in the test database, so only the event count is shown
        self.assertEqual(labels, ["training events recorded"])
        self.assertContains(response, "training events recorded")
        # No events either, so no widget needs a script
        self.assertEqual(response.context["widget_scripts"], [])

    def test_old_urls_redirect_to_overview(self):
        for url in ("/", "/world-map"):
            response = self.client.get(url)
            self.assertRedirects(response, reverse("overview"), status_code=301)
