"""Encryption, hashing, and audit-chain helpers for NYAYA VAULT."""

import hashlib
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def get_encryption_key() -> bytes:
    """Load AES-256 key from environment variable."""
    hex_key = os.environ.get("ENCRYPTION_KEY", "")
    if len(hex_key) != 64:
        raise ValueError("ENCRYPTION_KEY must be 64 hex characters (32 bytes).")
    return bytes.fromhex(hex_key)


def compute_sha256(data: bytes) -> str:
    """Return hex SHA-256 digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def encrypt_file(plaintext: bytes) -> bytes:
    """Encrypt with AES-256-GCM. Returns nonce (12 bytes) + ciphertext."""
    key = get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def decrypt_file(blob: bytes) -> bytes:
    """Decrypt AES-256-GCM blob (first 12 bytes = nonce)."""
    key = get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = blob[:12]
    ciphertext = blob[12:]
    return aesgcm.decrypt(nonce, ciphertext, None)


def hash_audit_record(username: str, action: str, details: str, timestamp: str, prev_hash: str) -> str:
    """SHA-256 hash linking this audit record to the previous one."""
    data = f"{username}|{action}|{details}|{timestamp}|{prev_hash}"
    return hashlib.sha256(data.encode()).hexdigest()
