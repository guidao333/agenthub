"""AES 加解密工具"""

import os
import json
from hashlib import sha256
from base64 import b64encode, b64decode

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

# 从配置密钥派生 AES 密钥
_MASTER_KEY = os.getenv("ENCRYPTION_KEY", "agenthub-encryption-key-20260519")


def _derive_key(salt: bytes = None) -> tuple:
    if salt is None:
        salt = os.urandom(16)
    key = sha256(_MASTER_KEY.encode() + salt).digest()
    return key, salt


def encrypt(plaintext: str) -> str:
    """AES-256-CBC 加密，返回 base64 字符串"""
    key, salt = _derive_key()
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plaintext.encode()) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    # 输出: base64(salt + iv + ciphertext)
    payload = salt + iv + ciphertext
    return b64encode(payload).decode()


def decrypt(encoded: str) -> str:
    """解密 base64 字符串"""
    try:
        payload = b64decode(encoded)
        salt, iv, ciphertext = payload[:16], payload[16:32], payload[32:]
        key, _ = _derive_key(salt)
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded_data) + unpadder.finalize()
        return plaintext.decode()
    except Exception:
        return encoded  # 如果解密失败，返回原文（兼容非加密数据）
