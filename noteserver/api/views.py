import uuid

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone
from .models import Note
from .serializers import NoteSerializer, RegisterSerializer
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                "token": str(refresh.access_token),
                "username": user.username
            })
        return Response(serializer.errors, status=400)

class SyncNotesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        notes = request.data.get("notes", [])
        applied = []
        now = int(timezone.now().timestamp() * 1000)

        for n in notes:
            note_id = n.get("id")
            obj, _ = Note.objects.get_or_create(
                id=note_id or uuid.uuid4(),
                defaults={
                    "client_id": n.get("client_id"),
                    "author": user,
                    "subject": n.get("subject", ""),
                    "text": n.get("text", ""),
                    "created_at": n.get("created_at", now),
                    "updated_at": n.get("updated_at", now),
                    "deleted": n.get("deleted", False),
                },
            )
            # если заметка уже существует и автор совпадает — обновить
            if obj.author == user:
                obj.subject = n.get("subject", obj.subject)
                obj.text = n.get("text", obj.text)
                obj.updated_at = n.get("updated_at", now)
                obj.deleted = n.get("deleted", obj.deleted)
                obj.save()
            applied.append(NoteSerializer(obj).data)
        return Response({"success": True, "applied": applied, "serverTime": now})

class UpdatesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        since = int(request.query_params.get("since", 0))
        notes = Note.objects.filter(updated_at__gt=since)
        serializer = NoteSerializer(notes, many=True)
        return Response({"success": True, "notes": serializer.data, "serverTime": int(timezone.now().timestamp() * 1000)})

class DeleteNoteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            note = Note.objects.get(pk=pk)
        except Note.DoesNotExist:
            return Response({"error": "not found"}, status=404)
        if note.author != request.user:
            return Response({"error": "forbidden"}, status=403)
        note.deleted = True
        note.updated_at = int(timezone.now().timestamp() * 1000)
        note.save()
        return Response({"success": True, "id": str(note.id), "updated_at": note.updated_at})
