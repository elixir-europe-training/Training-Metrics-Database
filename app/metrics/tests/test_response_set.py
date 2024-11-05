from django.test import TestCase
from metrics.models import QuestionSet, Question, Answer, Response, ResponseSet
from django.contrib.auth.models import User


class TestResponseSet(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="user")
        self.questions = [
            Question.objects.create(
                text=f"Question {i}?",
                slug=f"question-{i}",
                is_multichoice=i%2,
                user=self.user
            )
            for i in range(10)
        ]
        for question in self.questions:
            for i in range(5):
                Answer.objects.create(
                    question=question,
                    text=f"A{i}",
                    slug=f"{question.slug}.a{i}",
                    user=self.user
                )
        self.question_set = QuestionSet.objects.create(
            name="QuestionSet",
            user=self.user,
        )
        self.question_set.questions.set(self.questions)

    def test_parse_response_entries(self):
        questions = list(self.question_set.questions.all())
        self.assertTrue(len(questions) > 0)

        response_data = [
            {
                q.slug: q.answers.first().slug
                for q in questions
            }
            for _i in range(10)
        ]
        entries = ResponseSet.objects.parse_response_entries(
            self.question_set,
            response_data
        )

        for entry in entries:
            for response in entry:
                self.assertTrue(response.question in questions)
                self.assertTrue(response.answer in response.question.answers.all())

    def test_parse_response(self):
        questions = [
            q
            for q in self.questions
            if q.is_multichoice
        ]
        self.assertTrue(len(questions) > 0)

        for question in questions:
            answers = list(question.answers.all())
            value = ",".join([a.slug for a in answers])
            responses = list(Response.objects.parse_response(question, value))
            parsed_answers = [
                r.answer
                for r in responses
            ]
            self.assertEqual(answers, parsed_answers)
            for r in responses:
                self.assertEqual(r.question, question)
        


