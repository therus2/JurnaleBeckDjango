# journal/views.py
import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view
from .models import Note
from .serializers import NoteSerializer, RegisterSerializer


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

        # ПРОВЕРКА: студенты не могут отправлять заметки на сервер
        if user.groups.filter(name='students').exists():
            return Response({
                "error": "Forbidden: Students cannot sync notes to server"
            }, status=status.HTTP_403_FORBIDDEN)

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

            # Получаем имя автора из запроса или используем имя текущего пользователя
            author_name = n.get("author", user.username)

            note, created = Note.objects.update_or_create(
                id=note_uuid,
                defaults={
                    "author": user,
                    "author_name": author_name,
                    "subject": n.get("subject", ""),
                    "text": n.get("text", ""),
                    "created_at": n.get("created_at", now),
                    "updated_at": n.get("updated_at", now),
                    "uploaded_at": n.get("uploaded_at", now),
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
        # Фильтруем только по автору, чтобы не выдавать чужие заметки
        notes = Note.objects.filter(
            author=request.user,
            updated_at__gt=since
        ).order_by('updated_at')
        serializer = NoteSerializer(notes, many=True)
        server_time = int(timezone.now().timestamp() * 1000)
        return Response({
            "success": True,
            "notes": serializer.data,
            "serverTime": server_time
        })


class DeleteNoteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            note_uuid = uuid.UUID(str(pk))
            note = Note.objects.get(id=note_uuid)
        except (ValueError, Note.DoesNotExist):
            return Response({"error": "Note not found or invalid ID"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if note.author != user:
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        if not user.groups.filter(name='teachers').exists():
            return Response({"error": "You do not have permission to delete this note"},
                            status=status.HTTP_403_FORBIDDEN)

        # Жёсткое удаление (hard delete) - физически удаляет из БД
        note.delete()

        return Response({
            "success": True,
            "id": str(note.id),
        })


@api_view(['GET'])
def get_user_group(request):
    user = request.user
    group_names = [g.name for g in user.groups.all()]
    return Response({
        "group": group_names[0] if group_names else None
    })