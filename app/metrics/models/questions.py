from django.db import models
from .common import EditTracking, Event, Node


class Question(EditTracking):
    text = models.CharField(max_length=1024)
    description = models.CharField(max_length=2048, blank=True, null=True)
    slug = models.SlugField(default="", null=False)
    is_multichoice = models.BooleanField()

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

    def __str__(self):
        return self.text


class ResponseSet(EditTracking):
    event = models.ForeignKey(
        Event, on_delete=models.PROTECT, related_name="responses"
    )
    question_set = models.ForeignKey(
        QuestionSet, on_delete=models.PROTECT
    )

    def clean(self, *args, **kwargs):
        # TODO: Verify that the response set includes responses for all questions
        # TODO: Verify that the responses fulfill the individual question requirements
        #         - Answer are part of the questions answer set
        #         - Allow / disallow multiple answers depending on Question.is_multichoice
        super().clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Response(models.Model):
    response_set = models.ForeignKey(
        ResponseSet, on_delete=models.CASCADE, related_name="entries"
    )
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    answer = models.ForeignKey(Answer, on_delete=models.PROTECT)

