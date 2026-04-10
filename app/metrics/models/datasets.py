import uuid
from django.db import models
from .common import (
    Node,
    EditTracking,
)


class Dataset(EditTracking):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    node = models.ForeignKey(Node, on_delete=models.PROTECT, blank=False, null=False)
    name = models.CharField(max_length=128)
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
