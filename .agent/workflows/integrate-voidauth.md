---
description: How to autonomously integrate VoidAuth v0.1.1 into any Django project
---

Follow these steps to achieve a zero-knowledge, passwordless authentication system.

### 1. Installation
Install the base dependencies:
```bash
pip install django-voidauth webauthn cryptography
```

### 2. Configuration (`settings.py`)
Add the settings and standard backends:
```python
INSTALLED_APPS = [
    ...,
    'voidauth',
]

VOIDAUTH_RP_ID = 'localhost' # Enables dynamic host detection
VOIDAUTH_ORIGIN = 'http://localhost:8000'
VOIDAUTH_RP_NAME = 'My Shared Studio'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'voidauth.backend.VoidAuthBackend',
]
```

### 3. Routing (`urls.py`)
Include the standard endpoints:
```python
path('voidauth/', include('voidauth.urls')),
```

### 4. Template Integration
In your Login and Signup templates:
- **Signup**: Add `{% void_registration_interceptor %}` inside your form.
- **Login**: Add `{% void_secure_login_button %}`.
- **Both**: Include `{% void_recovery_modal %}` at the bottom of the content block.

### 5. Verification Check
- Launch server and visit `http://localhost:8000` (DO NOT use 127.0.0.1 for initial enrollment).
- Create a new account and verify the **Biometric Fingerprint prompt** appears during the "Recovery Word" phase.
- Logout and verify **Zero-Typing Login** works by scanning your fingerprint.

// turbo
### 6. Health Check
Run the following management command to verify cache synchronization:
```bash
python manage.py check_voidauth_configuration
```
