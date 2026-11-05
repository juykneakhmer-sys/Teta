"""ការបង្កើតឈ្មោះគណនី (username) ថ្មី — generator ក្នុងម៉ាស៊ីនរបស់អ្នក។

សំខាន់៖ ឧបករណ៍នេះបង្កើតតែ "ឈ្មោះ" ដែលអាចប្រើបាន (candidate) ប៉ុណ្ណោះ។
ការត្រួតពិនិត្យថាឈ្មោះនោះទំនេរឬអត់ ត្រូវធ្វើតាម Gmail ផ្ទាល់
(https://accounts.google.com/signup) ដោយមនុស្សម្នាក់បញ្ជាក់ — យើងមិន
ធ្វើ automation បង្កើតគណនី ឬឆ្លងកាត់ verification របស់ Google ទេ។
"""

from __future__ import annotations

import random
import re
import secrets
import string

RESERVED_DOMAINS = ("gmail.com", "googlemail.com")
_SAFE_EMAIL = re.compile(r"^[a-z0-9][a-z0-9.]{2,26}[a-z0-9]@(gmail\.com|googlemail\.com)$")

WORDS = (
    "mango", "mango", "lotus", "lotus", "angkor", "tonle", "sokha", "sokha",
    "dara", "bopha", "chann", "vibol", "rithy", "sophea", "pich", "kanha",
    "srey", "sok", "vuthy", "nita", "kim", "lin", "mey", "nary", "pheak",
    "phnom", "penh", "bassac", "kratie", "kampot", "kep", "koh", "samud",
    "orchid", "frangipani", "rice", "mekong", "temple", "smile", "swift",
)


def _rng(seed: str | None) -> random.Random:
    return random.Random(secrets.randbits(128) if seed is None else seed)


def normalize_localpart(text: str) -> str:
    """យកឈ្មោះ → local part ស្របច្បាប់សម្រាប់ Gmail។"""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9._]", "", text)
    text = re.sub(r"\.{2,}", ".", text).strip("._")
    return text


def is_valid_email(email: str) -> bool:
    email = email.strip().lower()
    if not _SAFE_EMAIL.match(email):
        return False
    local = email.split("@")[0]
    return not local.startswith(".") and not local.endswith(".")


def generate(n: int = 10, seed_text: str | None = None, domain: str = "gmail.com",
             min_len: int = 8, max_len: int = 24) -> list[str]:
    """បង្កើតបញ្ជីឈ្មោះបេក្ខជន (មិនទាន់ត្រួតពិនិត្យជាមួយ Google ទេ)។"""
    if domain not in RESERVED_DOMAINS:
        raise ValueError("ឧបករណ៍នេះគាំទ្រតែ gmail.com / googlemail.com")
    if not 6 <= min_len <= max_len <= 30:
        raise ValueError("ប្រវែងត្រូវនៅចន្លោះ 6–30")

    rng = _rng(seed_text)
    base = normalize_localpart(seed_text) if seed_text else ""
    seen: set[str] = set()
    out: list[str] = []

    def push(local: str) -> None:
        local = normalize_localpart(local)
        if min_len <= len(local) <= max_len and local not in seen and is_valid_email(local + "@" + domain):
            seen.add(local)
            out.append(f"{local}@{domain}")

    if base:
        for suffix in ("", "kh", "pp", ".kh", "1", "2", "07", "69", "168"):
            push(base + suffix)

    styles = [
        # word + word
        lambda: f"{rng.choice(WORDS)}{rng.choice(WORDS)}",
        # word + 2-digit number
        lambda: f"{rng.choice(WORDS)}{rng.randint(10, 99)}",
        # word + word + digits
        lambda: f"{rng.choice(WORDS)}.{rng.choice(WORDS)}{rng.randint(1, 99)}",
        # word + short token
        lambda: f"{rng.choice(WORDS)}{''.join(rng.choices(string.ascii_lowercase, k=3))}",
        # name-ish + digits
        lambda: f"{rng.choice(WORDS)}{rng.choice(WORDS)}.{rng.randint(1, 9)}",
    ]

    guard = 0
    while len(out) < n and guard < n * 200:
        guard += 1
        push(rng.choice(styles)())

    return out[:n]
