import csv
import io
from html import unescape

from django.test import TestCase, Client
from django.urls import reverse

from metrics.models import Event, Node, OrganisingInstitution
from ..utils import create_user


class TestEventListDownload(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = create_user("admin", "pwd")
        self.node = Node.objects.create(name="ELIXIR-SE", country="Sweden")
        self.institution = OrganisingInstitution.objects.create(
            name="Uppsala University", country="Sweden"
        )

    def create_event(self, title, **kwargs):
        data = {
            "user": self.user,
            "title": title,
            "node_main": self.node,
            "date_start": "2026-01-01",
            "date_end": "2026-01-02",
            "duration": 2,
            "type": "Training - face to face",
            "location_city": "Uppsala",
            "location_country": "Sweden",
            "funding": ["ELIXIR Node"],
            "target_audience": ["Academia/ Research Institution"],
            "additional_platforms": ["Compute"],
            "communities": ["NA"],
            "number_participants": 10,
            "number_trainers": 2,
            "url": "http://test.local",
            "status": "Complete",
            **kwargs,
        }
        event = Event.objects.create(**data)
        event.node.add(self.node)
        event.organising_institution.add(self.institution)
        return event

    def get_csv_rows(self, params=None):
        self.client.force_login(self.user)
        response = self.client.get(reverse("event-list-download"), params or {})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        self.assertIn("attachment", response["Content-Disposition"])
        return list(csv.DictReader(io.StringIO(response.content.decode("utf-8"))))

    def test_download_contains_event_details(self):
        event = self.create_event(
            "Intro to Python",
            funding=["ELIXIR Node", "EOSC Life"],
        )
        rows = self.get_csv_rows()

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["event_id"], str(event.id))
        self.assertNotIn("id", row)
        self.assertNotIn("code", row)
        self.assertEqual(row["title"], "Intro to Python")
        self.assertEqual(row["node_main"], "ELIXIR-SE (Sweden)")
        self.assertEqual(row["node"], "ELIXIR-SE (Sweden)")
        self.assertEqual(row["organising_institution"], "Uppsala University (Sweden)")
        self.assertEqual(row["funding"], "ELIXIR Node, EOSC Life")
        self.assertEqual(row["date_start"], "2026-01-01")
        self.assertNotIn("user", row)

    def test_download_applies_filters(self):
        self.create_event("Face to face", type="Training - face to face")
        self.create_event("Hackathon", type="Hackathon")

        rows = self.get_csv_rows({"type": "Hackathon"})

        self.assertEqual([row["title"] for row in rows], ["Hackathon"])

    def test_download_ignores_pagination(self):
        for i in range(15):
            self.create_event(f"Event {i}")

        rows = self.get_csv_rows({"page_size": 10, "page": 1})

        self.assertEqual(len(rows), 15)

    def test_download_requires_login(self):
        self.create_event("Intro to Python")

        response = self.client.get(reverse("event-list-download"))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("login")))

    def test_event_list_hides_download_for_anonymous_users(self):
        self.create_event("Intro to Python")

        response = self.client.get(reverse("event-list"))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("download", response.context)
        self.assertNotIn(reverse("event-list-download"), response.content.decode("utf-8"))

    def test_event_list_links_to_filtered_download(self):
        self.create_event("Hackathon", type="Hackathon")
        self.client.force_login(self.user)

        response = self.client.get(reverse("event-list"), {"type": "Hackathon"})

        self.assertEqual(response.status_code, 200)
        download_url = response.context["download"]["href"]
        self.assertTrue(download_url.startswith(reverse("event-list-download")))
        self.assertIn("type=Hackathon", download_url)
        self.assertIn(download_url, unescape(response.content.decode("utf-8")))
