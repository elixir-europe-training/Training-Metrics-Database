from django.test import TestCase, Client
from django.utils.text import slugify
from ..utils import create_user, create_question_data
import re
import json


class TestMetrics(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = create_user(
            "admin",
            "pwd",
            []
        )

        (_, supersets) = create_question_data(self.admin)
        self.question_sets = supersets

    def test_questionset_properties(self):
        """
        Test type and size in order to avoid reimplementing parts of the system in
        the tests.
        """
        for question_set in self.question_sets:
            response = self.client.get(f"/properties?question_sets={question_set.slug}")

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertValueProfile(
                data.keys(),
                {"values"},
            )
            self.assertGreater(len(data["values"]), 0)
            for value in data["values"]:
                self.assertValueProfile(
                    value.keys(),
                    {"id", "label", "options"},
                )

                for option in value["options"]:
                    self.assertValueProfile(
                        option.keys(),
                        {"id", "label"},
                    )

    def test_questionset_metrics(self):
        """
        Test type and size in order to avoid reimplementing parts of the system in
        the tests.
        """
        for question_set in self.question_sets:
            response = self.client.get(f"/metrics?question_sets={question_set.slug}")

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertValueProfile(
                data.keys(),
                {"values", "_meta"},
            )
            self.assertGreater(len(data["values"]), 0)
            for value in data["values"]:
                self.assertValueProfile(
                    value.keys(),
                    {"id", "label", "options"},
                )

                for option in value["options"]:
                    self.assertValueProfile(
                        option.keys(),
                        {"id", "label", "count"},
                    )
    
    def test_questionset_report(self):
        """
        Test type and size in order to avoid reimplementing parts of the system in
        the tests.
        """
        for question_set in self.question_sets:
            response = self.client.get(f"/report/set/{question_set.slug}")

            self.assertEqual(response.status_code, 200)
            content = response.content.decode("utf-8")

            datatags = [
                tag
                for tag in re.findall(
                    r'<script\s+id="(.+?)"\s+type="application/json">(.+?)</script>',
                    content
                )
            ]
            
            self.assertGreater(len(datatags), 0)
            for (tag_id, tag_content) in datatags:
                tag_data = json.loads(tag_content)
                self.assertValueProfile(
                    tag_data.keys(),
                    {"id", "label", "options"}
                )
                self.assertEqual(tag_id, tag_data["id"])

    def test_event_properties(self):
        """
        Test type and size in order to avoid reimplementing parts of the system in
        the tests.
        """
        response = self.client.get("/properties/event")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertValueProfile(
            data.keys(),
            {"values"},
        )
        self.assertGreater(len(data["values"]), 0)
        for value in data["values"]:
            self.assertValueProfile(
                value.keys(),
                {"id", "label", "filterable", "type"},
                {"options"}
            )
            
            for option in value.get("options", []):
                self.assertValueProfile(
                    option.keys(),
                    {"id", "label"},
                )

    def test_event_metrics(self):
        """
        Test type and size in order to avoid reimplementing parts of the system in
        the tests.
        """
        response = self.client.get("/metrics/event")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertValueProfile(
            data.keys(),
            {"values"},
        )
        self.assertGreater(len(data["values"]), 0)
        for value in data["values"]:
            self.assertValueProfile(
                value.keys(),
                {"id", "label", "options"}
            )
            
            for option in value.get("options", []):
                self.assertValueProfile(
                    option.keys(),
                    {"id", "label", "count"},
                )
    
    def test_event_report(self):
        """
        Test type and size in order to avoid reimplementing parts of the system in
        the tests.
        """
        response = self.client.get("/report/event")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")

        datatags = [
            tag
            for tag in re.findall(
                r'<script\s+id="(.+?)"\s+type="application/json">(.+?)</script>',
                content
            )
        ]
        
        self.assertGreater(len(datatags), 0)
        for (tag_id, tag_content) in datatags:
            tag_data = json.loads(tag_content)
            self.assertValueProfile(
                tag_data.keys(),
                {"id", "label", "options"}
            )
            self.assertEqual(tag_id, tag_data["id"])

    def assertValueProfile(self, values, requiredValues = None, optionalValues = None):
        requiredSet = set() if requiredValues is None else set(requiredValues)
        optionalSet = set() if optionalValues is None else set(optionalValues)
        valueSet = set(values)
        fullSet = requiredSet.union(optionalSet)
        self.assertTrue(valueSet.issubset(fullSet), f"The value set {valueSet} should be completely covered by the full set {fullSet}")
        self.assertTrue(requiredSet.issubset(valueSet), f"The required set {requiredSet} should be a subset of the value set {valueSet}")

