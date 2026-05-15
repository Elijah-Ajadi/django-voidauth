from django.urls import path
from django.views.generic import RedirectView
from .views import (
    ChallengeView, LoginView, RegisterView, RecoveryBlobView, LogoutView,
    WebAuthnRegisterChallengeView, WebAuthnRegisterVerifyView,
    WebAuthnLoginChallengeView, WebAuthnLoginVerifyView,
    UpdateRecoveryBlobView
)

app_name = 'voidauth'

urlpatterns = [
    path('', RedirectView.as_view(url='login/'), name='index'),
    path('challenge/', ChallengeView.as_view(), name='challenge'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('get_recovery_blob/', RecoveryBlobView.as_view(), name='get_recovery_blob'),
    path('update_recovery_blob/', UpdateRecoveryBlobView.as_view(), name='update_recovery_blob'),
    
    # WebAuthn Endpoints
    path('webauthn/register/challenge/', WebAuthnRegisterChallengeView.as_view(), name='webauthn_register_challenge'),
    path('webauthn/register/verify/', WebAuthnRegisterVerifyView.as_view(), name='webauthn_register_verify'),
    path('webauthn/login/challenge/', WebAuthnLoginChallengeView.as_view(), name='webauthn_login_challenge'),
    path('webauthn/login/verify/', WebAuthnLoginVerifyView.as_view(), name='webauthn_login_verify'),
]
