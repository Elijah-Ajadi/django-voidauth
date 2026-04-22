from django.urls import path
from django.views.generic import RedirectView
from .views import ChallengeView, LoginView, RegisterView

app_name = 'voidauth'

urlpatterns = [
    path('', RedirectView.as_view(url='login/'), name='index'),
    path('challenge/', ChallengeView.as_view(), name='challenge'),
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
]
