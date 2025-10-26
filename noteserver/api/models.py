# journal/models.py
from django.db import models
from django.contrib.auth.models import User
import uuid

class Note(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.CharField(max_length=200)
    text = models.TextField()
    created_at = models.BigIntegerField()
    updated_at = models.BigIntegerField()
    uploaded_at = models.BigIntegerField()

    def __str__(self):
        return f"{self.subject} — {self.author.username}"