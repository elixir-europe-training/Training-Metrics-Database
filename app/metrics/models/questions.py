from django.db import models
from django.core.exceptions import ValidationError
from .common import EditTracking, Event, Node


class Question(EditTracking):
    text = models.CharField(max_length=1024)
    description = models.CharField(max_length=2048, blank=True, null=True)
    slug = models.SlugField(default="", null=False, unique=True, max_length=1024)
    is_multichoice = models.BooleanField(default=False)
    node = models.ForeignKey(Node, on_delete=models.PROTECT, blank=True, null=True)
    is_active = models.BooleanField(default = True)

    def __str__(self):
        return f"{self.text} ({self.slug})"


class QuestionSet(EditTracking):
    name = models.TextField(max_length=1024)
    description = models.TextField(default="", blank=True, max_length=5120)
    slug = models.SlugField(default="", null=False, unique=True, max_length=1024)
    questions = models.ManyToManyField(Question)
    node = models.ForeignKey(Node, on_delete=models.PROTECT, blank=True, null=True)
    is_active = models.BooleanField(default = True)

    def __str__(self):
        return self.name


class QuestionSuperSet(EditTracking):
    name = models.TextField(max_length=1024)
    description = models.TextField(default="", blank=True, max_length=5120)
    slug = models.SlugField(default="", null=False, unique=True, max_length=1024)
    node = models.ForeignKey(Node, on_delete=models.PROTECT, blank=True, null=True)
    question_sets = models.ManyToManyField(QuestionSet)
    use_for_metrics = models.BooleanField(default=False)
    use_for_upload = models.BooleanField(default=False)
    is_active = models.BooleanField(default = True)

    def __str__(self):
        node_name = self.node.name if self.node else "Shared"
        return f"{self.name} ({node_name})"


class Answer(EditTracking):
    text = models.CharField(max_length=1024)
    slug = models.SlugField(default="", null=False, max_length=1024)
    is_active = models.BooleanField(default = True)
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


class ResponseSet(EditTracking):
    event = models.ForeignKey(
        Event, on_delete=models.PROTECT, related_name="responses"
    )
    question_set = models.ForeignKey(
        QuestionSet, on_delete=models.PROTECT
    )


class Response(models.Model):
    response_set = models.ForeignKey(
        ResponseSet, on_delete=models.CASCADE, related_name="entries"
    )
    answer = models.ForeignKey(Answer, on_delete=models.PROTECT)
