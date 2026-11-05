"""ម៉ាស៊ីនបង្កើតកូដ TOTP 6 ខ្ទង់ (offline)។

ប្រើសម្រាប់គណនីរបស់អ្នកផ្ទាល់ ដែលអ្នកបានរក្សាទុក 2FA secret key
(ពេលកំណត់ 2FA ជាមួយ authenticator app)។
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import struct
import time
import urllib.parse


def normalize_secret(secret: str) -> str:
    """យក otpauth:// URI ឬ secret ធម្មតា → base32 ស្អាត។"""
    secret = secret.strip()
    if secret.lower().startswith("otpauth://"):
        parsed = urllib.parse.urlparse(secret)
        query = urllib.parse.parse_qs(parsed.query)
        secret = (query.get("secret") or [""])[0]
    return secret.replace(" ", "").replace("-", "").upper().rstrip("=")


def _decode_base32(secret: str) -> bytes:
    norm = normalize_secret(secret)
    pad = (-len(norm)) % 8
    try:
        return base64.b32decode(norm + "=" * pad, casefold=True)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("2FA secret មិនត្រឹមត្រូវ (ត្រូវជា base32)") from exc


def code_at(secret: str, timestamp: float | None = None,
            digits: int = 6, period: int = 30) -> str:
    key = _decode_base32(secret)
    counter = int((time.time() if timestamp is None else timestamp) // period)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    chunk = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(chunk % (10 ** digits)).zfill(digits)


def remaining_seconds(period: int = 30) -> int:
    return period - int(time.time()) % period
