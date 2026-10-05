from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


AAD = b"casa-local-hub-mobile-v1"


class MobileCryptoError(RuntimeError):
    pass


class MobileCrypto:
    def __init__(self, private_key_path: Path, public_key_path: Path) -> None:
        self.private_key_path = private_key_path
        self.public_key_path = public_key_path
        self.private_key_path.parent.mkdir(parents=True, exist_ok=True)
        self._private_key = self._load_or_create_key()
        self._public_key = self._private_key.public_key()

    def _load_or_create_key(self):
        if self.private_key_path.exists():
            return serialization.load_pem_private_key(
                self.private_key_path.read_bytes(),
                password=None,
            )

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=3072,
        )
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self.private_key_path.write_bytes(private_pem)
        self.public_key_path.write_bytes(public_pem)
        try:
            os.chmod(self.private_key_path, 0o600)
            os.chmod(self.public_key_path, 0o644)
        except OSError:
            pass
        return private_key

    def public_info(self) -> dict[str, str]:
        public_pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        fingerprint = hashlib.sha256(public_pem).hexdigest()
        return {
            "algorithm": "RSA-OAEP-SHA256+AES-256-GCM",
            "public_key_pem": public_pem.decode("ascii"),
            "fingerprint": ":".join(
                fingerprint[index : index + 2]
                for index in range(0, 24, 2)
            ).upper(),
        }

    def decrypt_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            encrypted_key = base64.b64decode(str(payload["encrypted_key"]))
            iv = base64.b64decode(str(payload["iv"]))
            ciphertext = base64.b64decode(str(payload["ciphertext"]))
        except (KeyError, ValueError, TypeError) as exc:
            raise MobileCryptoError("Invalid encrypted payload.") from exc

        try:
            aes_key = self._private_key.decrypt(
                encrypted_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
            plaintext = AESGCM(aes_key).decrypt(iv, ciphertext, AAD)
            data = json.loads(plaintext.decode("utf-8"))
        except Exception as exc:
            raise MobileCryptoError("Could not decrypt payload.") from exc

        if not isinstance(data, dict):
            raise MobileCryptoError("Decrypted payload must be an object.")
        return data
