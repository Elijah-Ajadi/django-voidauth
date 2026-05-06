from django.urls import path
from django.views.generic import RedirectView
from .views import (
    ChallengeView, LoginView, RegisterView, RecoveryBlobView,
    QRChallengeView, QRHandoverView, QRRelayView, SessionStatusView, DashboardView, LogoutView, RelayView
)

app_name = 'voidauth'

urlpatterns = [
    path('', RedirectView.as_view(url='login/'), name='index'),
    path('challenge/', ChallengeView.as_view(), name='challenge'),
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('get_recovery_blob/', RecoveryBlobView.as_view(), name='get_recovery_blob'),
    path('qr_challenge/', QRChallengeView.as_view(), name='qr_challenge'),
    path('qr_handover/', QRHandoverView.as_view(), name='qr_handover'),
    path('qr_relay/', QRRelayView.as_view(), name='qr_relay'),
    path('session_status/', SessionStatusView.as_view(), name='session_status'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('relay/', RelayView.as_view(), name='relay'),
]
