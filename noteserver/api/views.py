# journal/views.py
import uuid
import secrets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from .models import Note, PermanentToken
from .serializers import NoteSerializer, RegisterSerializer
from .authentication import PermanentTokenAuthentication


# ====== Кастомная аутентификация =======
class CustomLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)

        if user is not None:
            # Создаем или получаем постоянный токен
            token_obj, created = PermanentToken.objects.get_or_create(user=user)

            return Response({
                'success': True,
                'token': token_obj.token,
                'username': user.username
            })
        else:
            return Response({
                'success': False,
                'error': 'Invalid credentials'
            }, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token')

        try:
            permanent_token = PermanentToken.objects.get(token=token)
            return Response({
                'success': True,
                'username': permanent_token.user.username
            })
        except PermanentToken.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)


class ResetTokenView(APIView):
    authentication_classes = [PermanentTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        # Удаляем старый токен и создаем новый
        PermanentToken.objects.filter(user=user).delete()
        new_token = PermanentToken.objects.create(user=user)

        return Response({
            'success': True,
            'token': new_token.token
        })


# ====== Регистрация (остается без изменений) =======
class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Создаем постоянный токен для нового пользователя
            token_obj = PermanentToken.objects.create(user=user)

            return Response({
                "token": token_obj.token,
                "username": user.username
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ====== API с постоянной аутентификацией =======
class SyncNotesView(APIView):
    authentication_classes = [PermanentTokenAuthentication]
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
    authentication_classes = [PermanentTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        since = int(request.query_params.get("since", 0))

        # Показываем ВСЕ заметки всех пользователей
        notes = Note.objects.filter(
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
    authentication_classes = [PermanentTokenAuthentication]
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
@authentication_classes([PermanentTokenAuthentication])
@permission_classes([IsAuthenticated])
def get_user_group(request):
    user = request.user
    group_names = [g.name for g in user.groups.all()]
    return Response({
        "group": group_names[0] if group_names else None
    })