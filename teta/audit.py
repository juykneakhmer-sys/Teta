"""សវនកម្ម (audit) គណនីផ្ទាល់ខ្លួន — ដំណើរការ offline ទាំងស្រុង។

ពិនិត្យរកបញ្ហាដែលអ្នកអាចកែបានភ្លាមៗ៖
  • លេខសម្ងាត់ខ្សោយ
  • លេខសម្ងាត់ប្រើដដែលលើច្រើនគណនី (reuse)
  • គណនីសំខាន់គ្មាន 2FA
  • គណនីមិនបានពិនិត្យ/កែជាយូរហួសកំណត់
  • គណនីហ្គេមគ្មានលេខសម្ងាត់ ឬគ្មាន ID

គ្មានការតភ្ជាប់បណ្តាញ គ្មានការផ្ញើទិន្នន័យចេញទេ។
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .passgen import entropy_bits
from .store import Account

WARN = "warning"
INFO = "info"
ERROR = "error"

WEAK_BITS = 50.0
STALE_DAYS = 180
TWO_FACTOR_KINDS = ("gmail", "email", "moonton", "social")


@dataclass
class Finding:
    level: str
    key: str
    message: str


def audit_accounts(accounts: list[Account], now: float | None = None,
                   stale_days: int = STALE_DAYS) -> list[Finding]:
    now = time.time() if now is None else now
    findings: list[Finding] = []

    by_password: dict[str, list[str]] = {}
    for acc in accounts:
        key = acc.key or "(គ្មានឈ្មោះ)"
        if acc.password:
            by_password.setdefault(acc.password, []).append(key)

        if acc.password and entropy_bits(acc.password) < WEAK_BITS:
            findings.append(Finding(
                WARN, key,
                f"លេខសម្ងាត់ខ្សោយ ({entropy_bits(acc.password):.0f} bits) — "
                f"ប្តូរទៅ `teta genpass`",
            ))

        if acc.kind in TWO_FACTOR_KINDS and not acc.totp_secret:
            findings.append(Finding(
                WARN, key, "គ្មាន 2FA — បើក 2FA រួច `teta set-totp` ដើម្បីរក្សា secret",
            ))

        age_days = (now - acc.updated_at) / 86400
        if age_days > stale_days:
            findings.append(Finding(
                INFO, key, f"មិនបានកែជាង {int(age_days)} ថ្ងៃ — ពិនិត្យឡើងវិញ?",
            ))

        if acc.kind == "game" and not acc.username:
            findings.append(Finding(
                ERROR, key, "គណនីហ្គេមគ្មាន ID/username",
            ))

    for key_list in by_password.values():
        if len(key_list) > 1:
            joined = ", ".join(key_list)
            for key in key_list:
                findings.append(Finding(
                    WARN, key, f"ប្រើលេខសម្ងាត់ដដែលលើ {len(key_list)} គណនី ({joined})",
                ))

    order = {ERROR: 0, WARN: 1, INFO: 2}
    findings.sort(key=lambda f: (order.get(f.level, 3), f.key))
    return findings


def score(accounts: list[Account], findings: list[Finding]) -> int:
    """ពិន្ទុ 0–100 (ខ្ពស់ = សុវត្ថិភាពល្អ) សម្រាប់បង្ហាញសង្ខេប។"""
    if not accounts:
        return 100
    penalty = sum({ERROR: 12, WARN: 7, INFO: 2}.get(f.level, 1) for f in findings)
    return max(0, 100 - penalty)
