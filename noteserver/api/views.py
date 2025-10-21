import json
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
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SyncNotesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        notes = request.data.get("notes", [])
        now = int(timezone.now().timestamp() * 1000)
        saved_notes = []

        for n in notes:
            note_id = n.get("id")
            try:
                if note_id:
                    note_uuid = uuid.UUID(str(note_id))
                else:
                    note_uuid = uuid.uuid4()
            except ValueError:
                continue

            # Принимаем поля напрямую — БЕЗ попыток парсить JSON внутри значений!
            note, created = Note.objects.update_or_create(
                id=note_uuid,
                defaults={
                    "author": user,
                    "subject": n.get("subject", ""),
                    "text": n.get("text", ""),
                    "created_at": n.get("created_at", now),
                    "updated_at": n.get("updated_at", now),
                    "uploaded_at": n.get("uploaded_at", now),
                    "deleted": n.get("deleted", False),
                }
            )
            saved_notes.append(NoteSerializer(note).data)

        return Response({
            "success": True,
            "notes": saved_notes,
            "serverTime": now
        })

class UpdatesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        since = int(request.query_params.get("since", 0))
        notes = Note.objects.filter(updated_at__gt=since)
        serializer = NoteSerializer(notes, many=True)
        return Response({
            "success": True,
            "notes": serializer.data,
            "serverTime": int(timezone.now().timestamp() * 1000)
        })

class DeleteNoteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            note_uuid = uuid.UUID(str(pk))
            note = Note.objects.get(pk=note_uuid)
        except (ValueError, Note.DoesNotExist):
            return Response({"error": "Note not found or invalid ID"}, status=status.HTTP_404_NOT_FOUND)
        if note.author != request.user:
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        note.deleted = True
        note.updated_at = int(timezone.now().timestamp() * 1000)
        note.save()
        return Response({"success": True, "id": str(note.id), "updated_at": note.updated_at})