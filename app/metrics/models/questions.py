from django.db import models
from .common import EditTracking, Event


class Question(EditTracking):
    text = models.CharField(max_length=1024)
    friendly_id = models.CharField(max_length=128)

    def __str__(self):
        return f"{self.text} ({self.friendly_id})"


class QuestionSet(EditTracking):
    name = models.TextField(max_length=1024)
    questions = models.ManyToManyField(Question)

    def __str__(self):
        return self.name


class Answer(EditTracking):
    text = models.CharField(max_length=1024)
    friendly_id = models.CharField(max_length=128)
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="answers"
    )

    def __str__(self):
        return self.text


class ResponseSet(EditTracking):
    event = models.ForeignKey(
        Event, on_delete=models.PROTECT, related_name="responses"
    )


class Response(models.Model):
    response_set = models.ForeignKey(
        ResponseSet, on_delete=models.CASCADE, related_name="entries"
    )
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    answer = models.ForeignKey(Answer, on_delete=models.PROTECT)
