# 🌌 django-voidauth

[![Version](https://img.shields.io/badge/version-0.1.0-blueviolet.svg?style=flat-square)](https://github.com/ELijah-Ajadi/django-voidauth)
[![Django](https://img.shields.io/badge/Django-3.2+-092e20.svg?style=flat-square)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)

**The Zero-Knowledge Void.** A high-security, asymmetric authentication system for Django that ensures cleartext passwords and reversible hashes *never* touch your server.

---

## 🛡️ The Philosophy

Traditional authentication systems rely on storing secrets (hashed passwords) on the server. If the database is compromised, those secrets are exposed to offline brute-force attacks.

**VoidAuth** flips the script. Inspired by blockchain security and modern cryptography:
- **Server Knowledge:** Zero. The server stores only a **Public Commitment** (Ed25519 Public Key).
- **Client Ownership:** Absolute. The **Private Key** never leaves the user's device.
- **Verification:** Cryptographic. Authentication is achieved via a **Challenge-Response** proof.

---

## 🚀 Key Features

- **💎 Ed25519 Proofs:** Ultra-fast, high-security asymmetric signatures for every login.
- **🧩 BIP-39 Recovery:** Human-readable 12-word mnemonics for account restoration.
- **🔒 Local Vault:** Private keys are stored in the browser's `IndexedDB`, never in cookies or local storage.
- **📦 Recovery Blobs:** AES-GCM encrypted private key backups stored on-server for multi-device sync.
- **⏳ Vetting Periods:** Built-in security locks for sensitive account recovery actions.

---

## 🛠️ Installation

```bash
pip install django-voidauth
```

### 1. Update `INSTALLED_APPS`
Add `voidauth` to your Django settings:

```python
INSTALLED_APPS = [
    ...
    'voidauth',
]
```

### 2. Configure Authentication Backends
Set `VoidAuthBackend` as your primary backend:

```python
AUTHENTICATION_BACKENDS = [
    'voidauth.backend.VoidAuthBackend',
    'django.contrib.auth.backends.ModelBackend', # Keep for standard users/admin
]
```

### 3. Add Middleware
Include the `VoidAuthMiddleware` to handle session integrity:

```python
MIDDLEWARE = [
    ...
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'voidauth.middleware.VoidAuthMiddleware',
    ...
]
```

### 4. Include URLs
Mount the authentication endpoints in your `urls.py`:

```python
urlpatterns = [
    ...
    path('voidauth/', include('voidauth.urls')),
]
```

---

## 💻 Client-Side Integration

VoidAuth provides a powerful JavaScript API. First, include the required libraries in your base template:

```html
<!-- Cryptography Libraries -->
<script src="{% static 'voidauth/js/libsodium.js' %}"></script>
<script src="{% static 'voidauth/js/bip39.js' %}"></script>
<!-- VoidAuth Logic -->
<script src="{% static 'voidauth/js/voidauth.js' %}"></script>
```

### 📝 Quick Start Example

Here is a minimal implementation for a login form:

```html
<form id="login-form">
    <input type="text" id="username" placeholder="Username" required>
    <button type="submit">Enter the Void</button>
</form>

<script>
    document.getElementById('login-form').onsubmit = async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        
        try {
            const response = await VoidAuth.login(username);
            if (response.status === 'success') {
                window.location.href = '/dashboard/';
            }
        } catch (error) {
            alert("Security Error: " + error.message);
        }
    };
</script>
```

### 🔑 JavaScript API Reference

| Method | Description |
| :--- | :--- |
| `VoidAuth.register(username, email, password)` | Generates keys, creates account, and returns recovery mnemonic. |
| `VoidAuth.login(username)` | Performs the challenge-response handshake. |
| `VoidAuth.recoverWithMnemonic(username, mnemonic, newPassword)` | Restores account access on a new device. |

---

## 🏗️ Security Architecture

1.  **Handshake:** Client requests a `challenge` (random nonce) from the server.
2.  **Signature:** Client signs the `challenge` using their local `Private Key`.
3.  **Proof:** Client sends the `signature` and `challenge` back to the server.
4.  **Verification:** Server uses the stored `Public Key` to verify the signature. If valid, the user is logged in.

---

## 🌐 Browser Compatibility

VoidAuth leverages the **Web Crypto API** and **IndexedDB**. It is compatible with:
- Chrome 37+
- Firefox 34+
- Edge 12+
- Safari 10.1+

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

<p align="center">
  Built with ❤️ for the privacy-conscious web.
</p>
