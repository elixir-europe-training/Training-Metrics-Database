from django.test import TestCase, Client
from django.utils.text import slugify
from ..utils import create_user, create_question_data
from metrics.models import QuestionSuperSet, Question, Node, Event, Response
from django.core.files.uploadedfile import SimpleUploadedFile
import re
import csv
import json
import logging


class TestUpload(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = create_user(
            "user",
            "pwd",
            []
        )

        self.user_without_node = create_user(
            "user_without_node",
            "pwd",
            []
        )

        self.admin = create_user(
            "admin",
            "pwd",
            []
        )

        self.node = Node.objects.create(name="Node", country="Nodetopia")
        self.user.profile.node = self.node
        self.user.profile.save()

        (question_sets, supersets) = create_question_data(self.admin)
        self.supersets = supersets
    
    def test_upload_events(self):
        # Silence alias loading log
        logging.getLogger("metrics.import_utils").setLevel(logging.WARNING)
        self.client.force_login(self.user)
        event_title = "Test event title"
        events_file = SimpleUploadedFile(
            "events.csv",
            bytes(
                (
                    'Title,ELIXIR Node,Start Date,End Date,Event type,Funding,Organising Institution/s,"Location (city, country)",EXCELERATE WP,Target audience,Additional ELIXIR Platforms involved,ELIXIR Communities involved,No. of participants,No. of trainers/ facilitators,Url to event page/ agenda\n'
                    f'{event_title},Node,2024-06-12,2024-06-10,Knowledge Exchange Workshop,ELIXIR Hub,"https://ror.org/02nv7yv05,https://ror.org/0576by029,https://ror.org/02catss52","Neverland, Sweden",,"Industry, Healthcare",Data,"Proteomics, Proteomics, NA, Metabolomics",,,https://neverland.local'
                ),
                "utf-8"
            ),
            content_type="text/csv"
        )
        response = self.client.post("/upload-data", {"events-file": events_file})
        self.assertEqual(response.status_code, 200)

        events = list(Event.objects.all())
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].title, event_title)


    def test_upload_metrics(self):
        self.client.force_login(self.user)
        node = Node.objects.first()
        event = Event.objects.create(
            user=self.admin,
            title="Test event",
            node_main=node,
            date_start="2026-01-01",
            date_end="2026-02-01",
            duration=10,
            type="Training - face to face",
            location_city="City",
            location_country="Testland",
            funding=["ELIXIR Converge"],
            target_audience=["Academia/ Research Institution"],
            additional_platforms=["Compute"],
            communities=["Human Data"],
            number_participants=1,
            number_trainers=1,
            url="http://test.local",
            status="Complete",
        )
        expected_result = {}
        for superset in self.supersets:
            questions = {
                question.slug: question
                for question_set in superset.question_sets.all()
                for question in question_set.questions.all()
            }

            headers = ["event_id"]
            metrics = [str(event.id)]
            for question in questions.values():
                answer = question.answers.first()
                headers.append(question.slug)
                metrics.append(answer.slug)
                expected_result[f"{question.slug}.{answer.slug}"] = expected_result.get(f"{question.slug}.{answer.slug}", 0) + 1
            
            metrics_file = events_file = SimpleUploadedFile(
                f"{superset.slug}.csv",
                bytes(
                    "\n".join([
                        ",".join(headers),
                        ",".join(metrics)
                    ]),
                    "utf-8"
                ),
                content_type="text/csv"
            )
            response = self.client.post("/upload-data", {f"{superset.slug}-file": metrics_file})
            self.assertEqual(response.status_code, 200)
        
        self.assertGreater(Response.objects.count(), 0)
        actual_result = {}
        for response in Response.objects.all():
            answer = response.answer
            question = answer.question
            actual_result[f"{question.slug}.{answer.slug}"] = actual_result.get(f"{question.slug}.{answer.slug}", 0) + 1

        self.assertEqual(
            expected_result,
            actual_result
        )

    def test_download_event_template(self):
        self.client.force_login(self.user)
        response = self.client.get("/download-template/event/base")
        self.assertEqual(response.status_code, 200)
        self.assertEquals(
            response.get("Content-Disposition"),
            'attachment; filename="event-template.csv"'
        )

        content = response.content.decode("utf-8")
        reader = csv.DictReader(content.split("\n"))

        event_header_count = 15
        self.assertFalse(reader.fieldnames == None)
        self.assertEqual(len(reader.fieldnames), event_header_count)

    def test_download_template_requires_login(self):
        url_variants = [
            "event/base",
            *[
                "metrics/{superset.slug}"
                for superset in self.supersets
            ]
        ]
        for url in url_variants:
            response = self.client.get(f"/download-template/{url}")
            self.assertEqual(response.status_code, 302)

    def test_download_metrics_template(self):
        self.client.force_login(self.user)

        for superset in self.supersets:
            response = self.client.get(f"/download-template/metrics/{superset.slug}")
            self.assertEqual(response.status_code, 200)
            self.assertEquals(
                response.get("Content-Disposition"),
                f'attachment; filename="metrics-{superset.slug}-template.csv"'
            )

            content = response.content.decode("utf-8")
            reader = csv.DictReader(content.split("\n"))

            header_count = sum([
                question_set.questions.count()
                for question_set in superset.question_sets.all()
            ]) + 1
            self.assertFalse(reader.fieldnames == None)
            self.assertEqual(len(reader.fieldnames), header_count, f"Header count for {superset.slug} should be {header_count}.")
    
    def test_upload_page_includes_correct_uploads(self):
        self.client.force_login(self.user)
        response = self.client.get("/upload-data")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")

        upload_ids = {
            upload_id
            for upload_id in re.findall(
                r'<input\s+type="file"\s+name="(.+?)-file"\s+class="form-control"\s+required\s+id=".+-file">',
                content
            )
        }

        superset_ids = {
            superset.slug
            for superset in self.supersets
        }
        expected_upload_ids = superset_ids.union({"events"})

        self.assertEqual(
            upload_ids,
            expected_upload_ids,
            f"The upload ids {upload_ids} are the same as the expected upload ids {expected_upload_ids}"
        )

    def test_upload_page_restricts_non_node_users(self):
        # Silence PermissionDenied exception logging
        logging.getLogger("django.request").setLevel(logging.ERROR)
        self.client.force_login(self.user_without_node)
        response = self.client.get(f"/upload-data")
        self.assertEqual(response.status_code, 403)
    
    def test_upload_page_redirects_unidentified_users(self):
        response = self.client.get(f"/upload-data")
        self.assertEqual(response.status_code, 302)
