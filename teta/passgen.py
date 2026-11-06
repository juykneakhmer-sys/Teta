"""ម៉ាស៊ីនបង្កើតលេខសម្ងាត់ខ្លាំង — ដំណើរការ offline ទាំងស្រុង។

ប្រើ `secrets` (CSPRNG របស់ប្រព័ន្ធ) មិនមែន `random` ទេ ដូច្នេះលទ្ធផល
មិនអាចទាយបានពី seed ឬពីលទ្ធផលមុនៗ។ គ្មានអ្វីចេញទៅ internet។
"""

from __future__ import annotations

import secrets
import string

from .generator import WORDS

# ការពារ 0/O, 1/l/I ដែលច្រើនតែច្រឡំពេលវាយដោយដៃ
LOWER = "abcdefghijkmnopqrstuvwxyz"
UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"
DIGITS = "23456789"
SYMBOLS = "!@#$%^&*-_=+?"

# ពាក្យងាយចងចាំ សម្រាប់ passphrase
_PHRASE_WORDS = tuple(sorted(set(WORDS)))


def generate_password(
    length: int = 20,
    *,
    symbols: bool = True,
    digits: bool = True,
    upper: bool = True,
    ambiguous: bool = False,
) -> str:
    """បង្កើតលេខសម្ងាត់ចៃដន្យខ្លាំង។"""
    if length < 8:
        raise ValueError("ប្រវែងត្រូវមានយ៉ាងតិច 8")
    if length > 256:
        raise ValueError("ប្រវែងគួរតិចជាង 256")

    pools: list[str] = [LOWER]
    if upper:
        pools.append(UPPER)
    if digits:
        pools.append(DIGITS)
    if symbols:
        pools.append(SYMBOLS)
    if ambiguous:
        pools = [string.ascii_letters, string.digits] + ([string.punctuation] if symbols else [])

    alphabet = "".join(pools)
    # ធានាថាមានយ៉ាងតិច ១ តួពីគ្រប់ pool
    chars = [secrets.choice(pool) for pool in pools]
    chars += [secrets.choice(alphabet) for _ in range(length - len(chars))]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def generate_passphrase(words: int = 4, separator: str = "-", capitalize: bool = False) -> str:
    """បង្កើត passphrase ពីពាក្យចៃដន្យ (ងាយចងចាំ ងាយវាយ)។"""
    if words < 3:
        raise ValueError("ត្រូវមានយ៉ាងតិច 3 ពាក្យ")
    if words > 16:
        raise ValueError("ច្រើនពេក — កំណត់ត្រឹម 16 ពាក្យ")
    picked = [secrets.choice(_PHRASE_WORDS) for _ in range(words)]
    if capitalize:
        picked = [w.capitalize() for w in picked]
    # បន្ថែមលេខ ២ ខ្ទង់ ដើម្បីបង្កើន entropy
    return separator.join(picked) + separator + str(secrets.randbelow(90) + 10)


def entropy_bits(password: str) -> float:
    """ការប៉ាន់ស្មាន entropy (bits) — សម្រាប់បង្ហាញកម្រិតកម្លាំង។"""
    import math

    if not password:
        return 0.0
    pool = 0
    if any(ch.islower() for ch in password):
        pool += 26
    if any(ch.isupper() for ch in password):
        pool += 26
    if any(ch.isdigit() for ch in password):
        pool += 10
    if any(not ch.isalnum() for ch in password):
        pool += 32
    return round(len(password) * math.log2(pool), 1) if pool else 0.0


def strength_label(bits: float) -> str:
    if bits < 40:
        return "ខ្សោយ"
    if bits < 60:
        return "មធ្យម"
    if bits < 80:
        return "ល្អ"
    return "ខ្លាំង"
