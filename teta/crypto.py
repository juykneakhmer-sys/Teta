"""ការអ៊ិនគ្រីប (encryption) សុទ្ធដោយ standard library។

Vault ត្រូវបានការពារដោយ master password៖
  - KDF : scrypt (hashlib.scrypt)
  - Cipher : HMAC-SHA256 keystream (stream cipher) + encrypt-then-MAC
មិនត្រូវការ dependency ខាងក្រៅ (works on Termux with plain python)។
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from typing import Any

MAGIC = "TETA1"
VERSION = 1

# scrypt params (16 MB memory → ស្រាលសម្រាប់ទូរស័ព្ទ)
SCRYPT_N = 2 ** 14
SCRYPT_R = 8
SCRYPT_P = 1
KEY_LEN = 64  # 32 bytes enc + 32 bytes mac


class CryptoError(Exception):
    """លេខសម្ងាត់ខុស ឬទិន្នន័យខូច។"""


def _b64e(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def derive_keys(password: str, salt: bytes, n: int = SCRYPT_N,
                r: int = SCRYPT_R, p: int = SCRYPT_P) -> tuple[bytes, bytes]:
    dk = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=KEY_LEN,
        maxmem=256 * 1024 * 1024,
    )
    return dk[:32], dk[32:]


def _keystream(enc_key: bytes, nonce: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hmac.new(enc_key, nonce + counter.to_bytes(8, "big"),
                         hashlib.sha256).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def _xor(data: bytes, stream: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(data, stream))


def encrypt(password: str, plaintext: bytes) -> str:
    """បម្លែង plaintext → JSON string ដែលអាចរក្សាទុកបាន។"""
    salt = os.urandom(16)
    nonce = os.urandom(16)
    enc_key, mac_key = derive_keys(password, salt)
    ct = _xor(plaintext, _keystream(enc_key, nonce, len(plaintext)))
    tag = hmac.new(mac_key, MAGIC.encode() + nonce + ct, hashlib.sha256).digest()
    blob = {
        "magic": MAGIC,
        "version": VERSION,
        "kdf": {"name": "scrypt", "n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P,
                "salt": _b64e(salt)},
        "nonce": _b64e(nonce),
        "ciphertext": _b64e(ct),
        "tag": _b64e(tag),
    }
    return json.dumps(blob, ensure_ascii=False)


def decrypt(password: str, blob_text: str) -> bytes:
    try:
        blob: dict[str, Any] = json.loads(blob_text)
    except json.JSONDecodeError as exc:
        raise CryptoError("ទម្រង់ vault មិនត្រឹមត្រូវ") from exc

    if blob.get("magic") != MAGIC:
        raise CryptoError("ឯកសារនេះមិនមែនជា vault របស់ Teta ទេ")

    kdf = blob.get("kdf", {})
    try:
        salt = _b64d(kdf["salt"])
        nonce = _b64d(blob["nonce"])
        ct = _b64d(blob["ciphertext"])
        tag = _b64d(blob["tag"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CryptoError("vault មានទិន្នន័យខូច") from exc

    enc_key, mac_key = derive_keys(
        password, salt,
        n=int(kdf.get("n", SCRYPT_N)),
        r=int(kdf.get("r", SCRYPT_R)),
        p=int(kdf.get("p", SCRYPT_P)),
    )
    expected = hmac.new(mac_key, MAGIC.encode() + nonce + ct, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, tag):
        raise CryptoError("លេខសម្ងាត់មេ (master password) មិនត្រឹមត្រូវ")
    return _xor(ct, _keystream(enc_key, nonce, len(ct)))
