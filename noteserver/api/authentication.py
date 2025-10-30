# journal/authentication.py
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import PermanentToken


class PermanentTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return None

        try:
            # Формат: "Bearer <token>" или просто "<token>"
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            else:
                token = auth_header

            permanent_token = PermanentToken.objects.get(token=token)
            return (permanent_token.user, None)

        except PermanentToken.DoesNotExist:
            raise AuthenticationFailed('Invalid token')
        except Exception as e:
            raise AuthenticationFailed(f'Authentication error: {str(e)}')