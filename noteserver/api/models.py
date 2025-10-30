# journal/models.py
from django.db import models
from django.contrib.auth.models import User
import uuid
import secrets


class PermanentToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.token}"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(50)
        super().save(*args, **kwargs)


class Note(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    author_name = models.CharField(max_length=150, blank=True)
    subject = models.CharField(max_length=200)
    text = models.TextField()
    created_at = models.BigIntegerField()
    updated_at = models.BigIntegerField()
    uploaded_at = models.BigIntegerField()

    def __str__(self):
        return f"{self.subject} — {self.author.username}"

    def save(self, *args, **kwargs):
        if not self.author_name and self.author:
            self.author_name = self.author.username
        super().save(*args, **kwargs)