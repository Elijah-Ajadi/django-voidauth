window.VoidAuth = (function() {
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

    async function savePrivateKey(username, privateKeyHex) {
        const db = await dbPromise;
        return new Promise((resolve, reject) => {
            const tx = db.transaction('keys', 'readwrite');
            tx.objectStore('keys').put(privateKeyHex, username);
            tx.oncomplete = () => resolve();
            tx.onerror = () => reject(tx.error);
        });
    }

    async function getPrivateKey(username) {
        const db = await dbPromise;
        return new Promise((resolve, reject) => {
            const tx = db.transaction('keys', 'readonly');
            const req = tx.objectStore('keys').get(username);
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
    }

    // Helper: Buffer to Hex
    function buf2hex(buffer) {
        return Array.prototype.map.call(new Uint8Array(buffer), x => ('00' + x.toString(16)).slice(-2)).join('');
    }
    function hex2buf(hexString) {
        return new Uint8Array(hexString.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));
    }

    // Helper: Derive AES key from password
    async function deriveKey(password, salt) {
        const enc = new TextEncoder();
        const keyMaterial = await window.crypto.subtle.importKey(
            'raw', enc.encode(password), {name: 'PBKDF2'}, false, ['deriveBits', 'deriveKey']
        );
        return window.crypto.subtle.deriveKey(
            {
                name: 'PBKDF2',
                salt: salt,
                iterations: 100000,
                hash: 'SHA-256'
            },
            keyMaterial,
            {name: 'AES-GCM', length: 256},
            true,
            ['encrypt', 'decrypt']
        );
    }

    // Helper: Encrypt private key
    async function encryptPrivateKey(privateKeyBuf, password) {
        const salt = window.crypto.getRandomValues(new Uint8Array(16));
        const iv = window.crypto.getRandomValues(new Uint8Array(12));
        const key = await deriveKey(password, salt);
        const encrypted = await window.crypto.subtle.encrypt(
            {name: 'AES-GCM', iv: iv},
            key,
            privateKeyBuf
        );
        return {
            salt: buf2hex(salt),
            iv: buf2hex(iv),
            ciphertext: buf2hex(encrypted)
        };
    }

    // Helper: Decrypt private key
    async function decryptPrivateKey(blob, password) {
        const salt = hex2buf(blob.salt);
        const iv = hex2buf(blob.iv);
        const ciphertext = hex2buf(blob.ciphertext);
        const key = await deriveKey(password, salt);
        const decrypted = await window.crypto.subtle.decrypt(
            {name: 'AES-GCM', iv: iv},
            key,
            ciphertext
        );
        return new Uint8Array(decrypted);
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

    // API calls
    async function apiRequest(url, data) {
        const fd = new FormData();
        for (let k in data) fd.append(k, data[k]);
        const res = await fetch(url, {
            method: 'POST',
            body: fd,
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        return res.json();
    }

    async function register(username, email, masterPassword, skipApiCall = false) {
        if (typeof window.sodium === 'undefined') {
            throw new Error("Security library (libsodium) not loaded locally. Please refresh the page.");
        }
        await window.sodium.ready;
        const sodium = window.sodium;
        // Generate Mnemonic & Seed
        const mnemonic = await window.bip39.generateMnemonic();
        const entropy = await window.bip39.mnemonicToEntropy(mnemonic);
        
        // Hash entropy to 32 bytes for Ed25519 seed
        const seed = sodium.crypto_hash_sha256(entropy);
        
        // Use 32-byte seed for Ed25519
        const keypair = sodium.crypto_sign_seed_keypair(seed);
        const publicKeyHex = buf2hex(keypair.publicKey);
        const privateKeyHex = buf2hex(keypair.privateKey);

        // Encrypt private key
        const blob = await encryptPrivateKey(keypair.privateKey, masterPassword);

        // Save local
        await savePrivateKey(username, privateKeyHex);

        if (skipApiCall) {
            return {
                mnemonic,
                publicKey: publicKeyHex,
                recoveryBlob: JSON.stringify(blob)
            };
        }

        // Send to default server endpoint
        const response = await apiRequest('/voidauth/register/', {
            username,
            email,
            public_key: publicKeyHex,
            recovery_blob: JSON.stringify(blob)
        });

        if (response.status === 'success') {
            return { success: true, mnemonic, message: "Registration successful." };
        } else {
            throw new Error(response.error);
        }
    }

    async function login(username, endpointUrl = '/voidauth/login/') {
        if (typeof window.sodium === 'undefined') {
            throw new Error("Security library (libsodium) not loaded locally. Please refresh the page.");
        }
        await window.sodium.ready;
        const sodium = window.sodium;
        const privateKeyHex = await getPrivateKey(username);
        if (!privateKeyHex) throw new Error("Device not recognized. Please recover your account.");

        // Get challenge
        const challengeData = await apiRequest('/voidauth/challenge/', { username });
        if (challengeData.error) throw new Error(challengeData.error);
        const challengeStr = challengeData.challenge;

        // Sign challenge
        const privateKeyBuf = hex2buf(privateKeyHex);
        const challengeBuf = new TextEncoder().encode(challengeStr);
        const signatureBuf = sodium.crypto_sign_detached(challengeBuf, privateKeyBuf);
        const signatureHex = buf2hex(signatureBuf);

        // Submit signature
        const loginData = await apiRequest(endpointUrl, {
            username,
            challenge: challengeStr,
            signature: signatureHex
        });

        if (loginData.status === 'success') {
            return loginData;
        } else {
            throw new Error(loginData.message || loginData.error || "Login failed");
        }
    }

    async function recoverWithMnemonic(username, mnemonic, newMasterPassword) {
        if (typeof window.sodium === 'undefined') {
            throw new Error("Security library (libsodium) not loaded locally. Please refresh the page.");
        }
        await window.sodium.ready;
        const sodium = window.sodium;
        const entropy = await window.bip39.mnemonicToEntropy(mnemonic);
        
        // Hash entropy to 32 bytes for Ed25519 seed
        const seed = sodium.crypto_hash_sha256(entropy);
        
        const keypair = sodium.crypto_sign_seed_keypair(seed);
        const privateKeyHex = buf2hex(keypair.privateKey);
        
        await savePrivateKey(username, privateKeyHex);
        
        // In a full implementation, you would also trigger the key rotation/vetting period here
        // by making an API call to a specific recovery endpoint.
        // For now, we just restore the local key, allowing login to succeed.
        return login(username);
    }

    return {
        register,
        login,
        recoverWithMnemonic
    };
})();
