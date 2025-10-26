from django.urls import path
from .views import RegisterView, SyncNotesView, UpdatesView, DeleteNoteView, get_user_group
from rest_framework_simplejwt.views import TokenObtainPairView

urlpatterns = [
    path('register', RegisterView.as_view()),
    path('login', TokenObtainPairView.as_view()),
    path('notes/sync', SyncNotesView.as_view()),
    path('notes/updates', UpdatesView.as_view()),
    path('notes/<uuid:pk>/', DeleteNoteView.as_view(), name='delete_note'),
    path('user/group/', get_user_group, name='get_user_group'),
]