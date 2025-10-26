# journal/serializers.py
from rest_framework import serializers
from .models import Note
from django.contrib.auth.models import User

class NoteSerializer(serializers.ModelSerializer):
    author_username = serializers.ReadOnlyField(source='author.username') # <<< Добавлено для удобства

    class Meta:
        model = Note
        fields = '__all__'  # <<< Включает все поля модели (id, author, subject, text, created_at, updated_at, uploaded_at)
        # author_username добавлен отдельно, но не является полем модели, поэтому указывать его в fields не обязательно,
        # но можно, чтобы контролировать порядок:
        # fields = ['id', 'author', 'author_username', 'subject', 'text', 'created_at', 'updated_at', 'uploaded_at']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user