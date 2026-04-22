from django.urls import path, include

urlpatterns = [
    path('voidauth/', include('voidauth.urls')),
]
