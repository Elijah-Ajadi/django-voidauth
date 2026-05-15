# 🌌 django-voidauth

[![Version](https://img.shields.io/badge/version-0.1.1-blueviolet.svg?style=flat-square)](https://github.com/ELijah-Ajadi/django-voidauth)
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
- **🛡️ View Shield:** Indentation-agnostic defensive layer for registration views, ensuring cryptographic keys are verified even in complex nested code.
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

## 🧩 Modular UI Components

VoidAuth now ships with built-in Django template tags for a "plug-and-play" integration.

### 1. Load the Tags
First, load the tags in your template:
```html
{% load voidauth_tags %}
```

### 2. Recovery Modal (Mnemonic Display)
Add this at the bottom of your signup/registration template. It injects a high-tech "Vault Identity" overlay that ensures users save their 12-word seed phrase before finishing registration.
```html
{% void_recovery_modal %}
```

**JS Trigger:**
After calling `VoidAuth.register`, simply trigger the modal:
```javascript
const result = await VoidAuth.register(username, email, password);
if (result.success) {
    window.showVoidRecovery(result.mnemonic, '/login/'); // mnemonic and redirect URL
}
```

### 3. Secure Login Button
Add this inside your login form to enable passwordless authentication.
```html
{% void_secure_login_button redirect_url='/your_redirect_url' %}
```

### 4. Recovery Portal (Mnemonic & Password)
Add this to your login page. It injects a hidden modal that allows users to restore their vault on a new device using either their 12-word seed or their master password.
```html
{% void_recovery_form %}
```

**Triggering Recovery:**
Simply add the class `void-recover-trigger` to any link or button:
```html
<a href="#" class="void-recover-trigger">Lost device? Recover Account</a>
```

---

## 🛡️ Recovery Architecture

VoidAuth provides a unique dual-path recovery system that balances high security with user convenience:

1.  **Path A: BIP-39 Mnemonic (Seed Phrase)**
    -   **Usage**: Primary recovery method if the device is lost.
    -   **Logic**: The 12-word phrase re-derives the Ed25519 Private Key entirely on the client side.
    -   **Security**: No server interaction required for derivation.

2.  **Path B: Server-Side Recovery Blob (Master Password)**
    -   **Usage**: Fallback if the user loses their 12-word seed but remembers their password.
    -   **Logic**: The server provides an AES-GCM encrypted version of the private key. The client decrypts it locally using the master password.
    -   **Security**: The server *never* sees the cleartext key or the password.

---

## 🤖 Void Architect (AI Setup Assistant)

The **Void Architect** is now more powerful than ever. It performs a **Deep Scan** of your project (including your custom views and templates) to perform a surgical integration.
## The Void Architect is still under development and is prone to make mistakes

### Usage
```bash
# Automatically integrate VoidAuth into your existing templates
python manage.py void_architect --auto
```

The Architect will now:
- 🔍 **Deep Scan**: Recursively analyze your project structure to find your specific auth templates.
- 🎨 **Smart Patching**: Use the built-in `{% voidauth_tags %}` for a clean, modular integration.
- 🧬 **Field Detection**: Automatically detect your form field names (e.g., `password1` vs `password`) to ensure the JavaScript works out-of-the-box.
- 🩹 **Surgical Integration**: Intelligent indentation-agnostic patching that respects your code style and avoids breaking complex view logic.
- 🛡️ **View Shield Injection**: Automatically injects defensive key verification into your registration views to eliminate `IntegrityError` crashes.
- 🩹 **Non-Destructive**: Appends logic to the end of your files instead of overwriting them.

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
