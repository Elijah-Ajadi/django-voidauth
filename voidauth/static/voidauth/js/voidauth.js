window.VoidAuth = (function () {
    const DEBUG = true;
    function log(...args) { if (DEBUG) console.log("[VoidAuth]", ...args); }

    // Simple IndexedDB wrapper
    const dbPromise = new Promise((resolve, reject) => {
        const request = indexedDB.open('VoidAuthDB', 1);
        request.onupgradeneeded = event => {
            const db = event.target.result;
            db.createObjectStore('keys');
        };
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });

    async function savePrivateKey(username, privateKeyHex, password) {
        log("Saving Private Key for", username);
        const db = await dbPromise;
        const privateKeyBuf = hex2buf(privateKeyHex);
        const encryptedBlob = await encryptPrivateKey(privateKeyBuf, password);

        return new Promise((resolve, reject) => {
            const tx = db.transaction('keys', 'readwrite');
            tx.objectStore('keys').put(encryptedBlob, username);
            tx.oncomplete = () => {
                log("Private Key Saved Successfully.");
                resolve();
            };
            tx.onerror = () => reject(tx.error);
        });
    }

    async function getPrivateKey(username, password) {
        log("Retrieving Private Key for", username);
        const db = await dbPromise;
        return new Promise((resolve, reject) => {
            const tx = db.transaction('keys', 'readonly');
            const req = tx.objectStore('keys').get(username);
            req.onsuccess = async () => {
                if (!req.result) {
                    log("No key found in IndexedDB for", username);
                    return resolve(null);
                }
                try {
                    if (typeof req.result === 'string') {
                        log("Found legacy unencrypted key.");
                        return resolve(req.result);
                    }
                    const decryptedBuf = await decryptPrivateKey(req.result, password);
                    log("Decryption Successful.");
                    resolve(buf2hex(decryptedBuf));
                } catch (e) {
                    console.error("[VoidAuth] Decryption failed:", e);
                    reject(new Error("Master password incorrect. (Details: " + e.message + ")"));
                }
            };
            req.onerror = () => reject(req.error);
        });
    }

    // Helper: Buffer to Hex
    function buf2hex(buffer) {
        return Array.prototype.map.call(new Uint8Array(buffer), x => ('00' + x.toString(16)).slice(-2)).join('');
    }

    function hex2buf(hexString) {
        if (!hexString || typeof hexString !== 'string') return new Uint8Array(0);
        const matches = hexString.match(/.{1,2}/g);
        if (!matches) return new Uint8Array(0);
        return new Uint8Array(matches.map(byte => parseInt(byte, 16)));
    }

    // Helper: Derive AES key from password with support for versioning
    async function deriveKey(password, salt, iterations = 100000) {
        const enc = new TextEncoder();
        const keyMaterial = await window.crypto.subtle.importKey(
            'raw', enc.encode(password), { name: 'PBKDF2' }, false, ['deriveBits', 'deriveKey']
        );
        return window.crypto.subtle.deriveKey(
            {
                name: 'PBKDF2',
                salt: salt,
                iterations: iterations,
                hash: 'SHA-256'
            },
            keyMaterial,
            { name: 'AES-GCM', length: 256 },
            true,
            ['encrypt', 'decrypt']
        );
    }

    async function encryptPrivateKey(privateKeyBuf, password) {
        const iterations = 100000;
        const salt = window.crypto.getRandomValues(new Uint8Array(16));
        const iv = window.crypto.getRandomValues(new Uint8Array(12));
        const key = await deriveKey(password, salt, iterations);
        const encrypted = await window.crypto.subtle.encrypt(
            { name: 'AES-GCM', iv: iv },
            key,
            privateKeyBuf
        );
        return {
            salt: buf2hex(salt),
            iv: buf2hex(iv),
            ciphertext: buf2hex(encrypted),
            iterations: iterations
        };
    }

    async function decryptPrivateKey(blob, password) {
        const salt = hex2buf(blob.salt);
        const iv = hex2buf(blob.iv);
        const ciphertext = hex2buf(blob.ciphertext);
        const iterations = blob.iterations || 100000; // Fallback for older blobs

        const key = await deriveKey(password, salt, iterations);
        const decrypted = await window.crypto.subtle.decrypt(
            { name: 'AES-GCM', iv: iv },
            key,
            ciphertext
        );
        return new Uint8Array(decrypted);
    }

    // Helper: base64url to Uint8Array
    function base64urlToUint8Array(base64url) {
        const padding = '='.repeat((4 - base64url.length % 4) % 4);
        const base64 = (base64url + padding).replace(/\-/g, '+').replace(/_/g, '/');
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    function uint8ArrayToBase64url(uint8array) {
        const base64 = btoa(String.fromCharCode.apply(null, uint8array));
        return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
    }

    async function apiRequest(url, data) {
        log("API Request:", url);
        const fd = new FormData();
        for (let k in data) fd.append(k, data[k]);

        const res = await fetch(url, {
            method: 'POST',
            body: fd,
            headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });

        if (res.status === 404 && url.includes('challenge')) {
            throw new Error("No passkeys registered");
        }

        if (!res.ok) {
            const txt = await res.text();
            throw new Error(`Server error ${res.status}: ${txt.substring(0, 50)}`);
        }

        const contentType = res.headers.get("content-type");
        if (contentType && contentType.indexOf("application/json") !== -1) {
            return res.json();
        }
        return res.text();
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    async function registerPasskey(username, email, deviceName = "My Device") {
        log("Registering Passkey for", username);
        const options = await apiRequest('/voidauth/webauthn/register/challenge/', { username, email });
        if (options.error) throw new Error(options.error);

        options.challenge = base64urlToUint8Array(options.challenge);
        options.user.id = base64urlToUint8Array(options.user.id);
        if (options.excludeCredentials) {
            options.excludeCredentials.forEach(cred => {
                cred.id = base64urlToUint8Array(cred.id);
            });
        }

        const credential = await navigator.credentials.create({ publicKey: options });
        const responseData = {
            id: credential.id,
            rawId: uint8ArrayToBase64url(new Uint8Array(credential.rawId)),
            type: credential.type,
            response: {
                attestationObject: uint8ArrayToBase64url(new Uint8Array(credential.response.attestationObject)),
                clientDataJSON: uint8ArrayToBase64url(new Uint8Array(credential.response.clientDataJSON)),
                transports: credential.response.getTransports ? credential.response.getTransports() : []
            }
        };

        const verification = await apiRequest('/voidauth/webauthn/register/verify/', {
            username, email, device_name: deviceName, response: JSON.stringify(responseData)
        });

        return verification;
    }

    async function loginWithPasskey(username) {
        log("Login with Passkey for", username);
        const options = await apiRequest('/voidauth/webauthn/login/challenge/', { username });
        if (options.error) throw new Error(options.error);

        options.challenge = base64urlToUint8Array(options.challenge);
        options.allowCredentials.forEach(cred => {
            cred.id = base64urlToUint8Array(cred.id);
        });

        const assertion = await navigator.credentials.get({ publicKey: options });
        const responseData = {
            id: assertion.id,
            rawId: uint8ArrayToBase64url(new Uint8Array(assertion.rawId)),
            type: assertion.type,
            response: {
                authenticatorData: uint8ArrayToBase64url(new Uint8Array(assertion.response.authenticatorData)),
                clientDataJSON: uint8ArrayToBase64url(new Uint8Array(assertion.response.clientDataJSON)),
                signature: uint8ArrayToBase64url(new Uint8Array(assertion.response.signature)),
                userHandle: assertion.response.userHandle ? uint8ArrayToBase64url(new Uint8Array(assertion.response.userHandle)) : null
            }
        };

        return await apiRequest('/voidauth/webauthn/login/verify/', {
            username, response: JSON.stringify(responseData)
        });
    }

    async function login(username, masterPassword) {
        log("Logging in via Vault for", username);
        if (typeof window.sodium === 'undefined') {
            await new Promise(r => setTimeout(r, 500)); // Wait for libsodium
            if (typeof window.sodium === 'undefined') throw new Error("Security library not loaded.");
        }
        await window.sodium.ready;
        const sodium = window.sodium;

        const privateKeyHex = await getPrivateKey(username, masterPassword);
        if (!privateKeyHex) throw new Error("Account not found on this device.");

        const challengeData = await apiRequest('/voidauth/challenge/', { username });
        const challengeStr = challengeData.challenge;

        const privateKeyBuf = hex2buf(privateKeyHex);
        const challengeBuf = new TextEncoder().encode(challengeStr);
        const signatureBuf = sodium.crypto_sign_detached(challengeBuf, privateKeyBuf);
        const signatureHex = buf2hex(signatureBuf);

        return await apiRequest('/voidauth/login/', {
            username, challenge: challengeStr, signature: signatureHex
        });
    }

    async function register(username, email, masterPassword, skipApiCall = false) {
        log("Registering Vault for", username);
        await window.sodium.ready;
        const sodium = window.sodium;

        const mnemonic = await window.bip39.generateMnemonic();
        const entropy = await window.bip39.mnemonicToEntropy(mnemonic);
        const seed = sodium.crypto_hash_sha256(entropy);
        const keypair = sodium.crypto_sign_seed_keypair(seed);
        const publicKeyHex = buf2hex(keypair.publicKey);
        const privateKeyHex = buf2hex(keypair.privateKey);

        const blob = await encryptPrivateKey(keypair.privateKey, masterPassword);
        await savePrivateKey(username, privateKeyHex, masterPassword);

        if (skipApiCall) {
            return { mnemonic, publicKey: publicKeyHex, recoveryBlob: JSON.stringify(blob) };
        }

        return await apiRequest('/voidauth/register/', {
            username, email, public_key: publicKeyHex, recovery_blob: JSON.stringify(blob)
        });
    }

    return { register, login, registerPasskey, loginWithPasskey };
})();
