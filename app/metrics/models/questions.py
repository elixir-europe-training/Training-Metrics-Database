from django.db import models
from django.core.exceptions import ValidationError
from .common import EditTracking, Event, Node


class Question(EditTracking):
    text = models.CharField(max_length=1024)
    description = models.CharField(max_length=2048, blank=True, null=True)
    slug = models.SlugField(default="", null=False, unique=True)
    is_multichoice = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.text} ({self.slug})"


class QuestionSet(EditTracking):
    name = models.TextField(max_length=1024)
    questions = models.ManyToManyField(Question)

    def __str__(self):
        return self.name


class QuestionSuperSet(EditTracking):
    name = models.TextField(max_length=1024)
    node = models.ForeignKey(Node, on_delete=models.PROTECT, blank=True, null=True)
    question_sets = models.ManyToManyField(QuestionSet)

    def __str__(self):
        node_name = self.node.name if self.node else "Shared"
        return f"{self.name} ({node_name})"


class Answer(EditTracking):
    text = models.CharField(max_length=1024)
    slug = models.SlugField(default="", null=False)
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="answers"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "question"],
                name="slug is unique per question",
            )
        ]

    def __str__(self):
        return self.text


class ResponseSetManager(models.Manager):
    def parse_response_entries(self, question_set, data):
        questions = list(question_set.questions.all())
        question_map = {
            **{
                q.slug: q
                for q in questions
            },
            **{
                q.text: q
                for q in questions
            },
        }

        entries = [
            [
                response
                for key, value in entry_data.items()
                for response in Response.objects.parse_response(question_map[key], value)
            ]
            for entry_data in data
        ]

        required_responses = set(questions)
        for i, entry in enumerate(entries):
            current_responses = set([response.answer.question for response in entry])
            if required_responses != current_responses:
                raise ValidationError(f"Not all questions have been answered on row {i}")

        return entries


class ResponseSet(EditTracking):
    event = models.ForeignKey(
        Event, on_delete=models.PROTECT, related_name="responses"
    )
    question_set = models.ForeignKey(
        QuestionSet, on_delete=models.PROTECT
    )

    objects = ResponseSetManager()

    def clean(self):
        # TODO: Verify that the response set includes responses for all questions
        # TODO: Verify that the responses fulfill the individual question requirements
        #         - Answer are part of the questions answer set
        #         - Allow / disallow multiple answers depending on Question.is_multichoice
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ResponseManager(models.Manager):
    def parse_response(self, question, value):
        values = value.split(",") if question.is_multichoice else [value]
        filtered_values = [
            v
            for v in values
            if v
        ]
        for v in filtered_values:
            try:
                answer = question.answers.get(slug=v)
                yield Response(answer=answer)
            except Answer.DoesNotExist:
                raise ValidationError(f"The answer '{value}' does not exist for question '{question.slug}'")


class Response(models.Model):
    response_set = models.ForeignKey(
        ResponseSet, on_delete=models.CASCADE, related_name="entries"
    )
    answer = models.ForeignKey(Answer, on_delete=models.PROTECT)

    objects = ResponseManager()

