# django-voidauth

A zero-knowledge authentication system for Django.

## Philosophy

"The Zero-Knowledge Void"
Ensure that Cleartext Passwords and Reversible Hashes never exist on the server. The server stores only a Public Commitment. Authentication is achieved through a Challenge-Response proof.

## Features
- Ed25519 Asymmetric Proofs
- BIP-39 Mnemonic Recovery
- AES-GCM Encrypted Private Key blobs
- Timed Security Locks

## Installation

```bash
pip install django-voidauth
```

Add to `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
    ...
    'voidauth',
]
```

Add to `AUTHENTICATION_BACKENDS`:
```python
AUTHENTICATION_BACKENDS = [
    'voidauth.backend.VoidAuthBackend',
    'django.contrib.auth.backends.ModelBackend', # Keep for legacy users if using Hybrid Mode
]
```

Add to `MIDDLEWARE`:
```python
MIDDLEWARE = [
    ...
    'voidauth.middleware.VoidAuthMiddleware',
]
```
