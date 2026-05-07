from django.urls import path
from django.views.generic import RedirectView
from .views import (
    ChallengeView, LoginView, RegisterView, RecoveryBlobView, LogoutView
)

app_name = 'voidauth'

urlpatterns = [
    path('', RedirectView.as_view(url='login/'), name='index'),
    path('challenge/', ChallengeView.as_view(), name='challenge'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('get_recovery_blob/', RecoveryBlobView.as_view(), name='get_recovery_blob'),
]
