"""ជំនួយការស្តារគណនី Gmail (Recovery Assistant) — តាមផ្លូវការរបស់ Google។

គោលការណ៍សុវត្ថិភាព
  ✔ ជួយអ្នកស្តារ **គណនីរបស់អ្នកផ្ទាល់** តាម https://accounts.google.com/signin/recovery
  ✔ រៀបចំព័ត៌មានដែល Google សួរ (recovery email/phone hints, កាលបរិច្ឆេទបង្កើត,
    label, ចំណាំ) និងបង្កើតតារាងពិនិត្យសម្រាប់អ្នកបំពេញដោយខ្លួនឯង
  ✔ រំលឹកពីជំហានសុវត្ថិភាពក្រោយស្តារបាន (ប្តូរលេខសម្ងាត់, 2FA, ពិនិត្យឧបករណ៍)

  ✘ មិនភ្ជាប់ IMAP/POP ទៅគណនីអ្នកដទៃ និងមិនចាប់យកសារដែលផ្ញើមកអ៊ីមែលដែល
    អ្នកមិនមានសិទ្ធិចូល — នោះមិនអាចធ្វើបានតាមបច្ចេកទេស (សារនៅលើ server
    របស់ Google ត្រូវការ login) ហើយខុសច្បាប់/លក្ខខណ្ឌ Google
  ✘ មិនបង្កើតគណនីជំនួសឈ្មោះដែលមានរួច (Google មិនអនុញ្ញាត)
"""

from __future__ import annotations

import time
from pathlib import Path

from . import __version__
from .generator import is_valid_email
from .store import Account, Vault

RECOVERY_URL = "https://accounts.google.com/signin/recovery"
SIGNUP_URL = "https://accounts.google.com/signup"
SECURITY_URL = "https://myaccount.google.com/security"

# សំណួរដែល Google តែងសួរ — រៀបចំជាបញ្ជីពិនិត្យ
CHECKLIST = (
    ("អ៊ីមែល/លេខទូរស័ព្ទស្តារ (recovery) ដែលអ្នកធ្លាប់ភ្ជាប់", "recovery"),
    ("ថ្ងៃ/ខែ/ឆ្នាំ ដែលអ្នកបង្កើតគណនី (ប្រហែលក៏បាន)", "created"),
    ("ឈ្មោះពេញដែលអ្នកបានបំពេញពេលបង្កើតគណនី", "name"),
    ("លេខសម្ងាត់ចុងក្រោយដែលអ្នកចាំបាន", "password"),
    ("ឧបករណ៍/កម្មវិធីដែលអ្នកធ្លាប់ប្រើចូល (ទូរស័ព្ទ, កុំព្យូទ័រ)", "devices"),
    ("ឈ្មោះអ្នកទំនាក់ទំនងញឹកញាប់ (label ឬឈ្មោះក្នុង Gmail)", "contacts"),
    ("សេវាដែលភ្ជាប់ (YouTube, Drive, Play) និងអ្វីដែលអ្នកបានទិញ", "services"),
)


class RecoveryError(Exception):
    pass


def mask_hint(text: str) -> str:
    """បង្ហាញ hint បែបសុវត្ថិភាព (បង្ហាញតែដើម/ចុង)។"""
    text = (text or "").strip()
    if not text:
        return ""
    if len(text) <= 4:
        return text[0] + "*" * (len(text) - 1)
    if "@" in text:                      # អ៊ីមែល
        local, domain = text.split("@", 1)
        head = local[:2]
        return f"{head}{'*' * max(1, len(local) - 3)}{local[-1]}@{domain}"
    return f"{text[:2]}{'*' * max(1, len(text) - 4)}{text[-2:]}"


def build_plan(account: Account) -> "list[tuple[str, str]]":
    """បង្កើតបញ្ជីពិនិត្យ — តួណាមានព័ត៌មានរួច (ពី vault) តួណាត្រូវរៀបចំបន្ថែម។"""
    note = account.note or ""
    rows = []
    for label, key in CHECKLIST:
        status = "ត្រូវរៀបចំ"
        if key == "created" and account.created_at:
            status = time.strftime("%Y-%m-%d", time.localtime(account.created_at))
        elif key == "recovery" and note:
            status = mask_hint(note)
        elif key == "contacts" and account.tags:
            status = ", ".join(account.tags)
        rows.append((label, status))
    return rows


def recovery_guide(account: Account) -> str:
    """អត្ថបទណែនាំជាជំហានៗ (អាចចម្លងទៅកត់ត្រា)។"""
    rows = build_plan(account)
    lines = [
        f"Teta v{__version__} — ផែនការស្តារគណនី",
        f"គណនី: {account.email}",
        f"label: {account.label or '-'}",
        f"បង្កើតពេល: {time.strftime('%Y-%m-%d %H:%M', time.localtime(account.created_at))}",
        "",
        "ជំហាន ១ — បើកទំព័រស្តារផ្លូវការ",
        f"  {RECOVERY_URL}",
        "  វាយអ៊ីមែលខាងលើ → ជ្រើស 'ខ្ញុំមិនចាំលេខសម្ងាត់' → បំពេញតាមអ្វីដែលអ្នកចាំ",
        "",
        "ជំហាន ២ — ព័ត៌មានដែលគួររៀបចំ (Google សួរ)",
    ]
    for label, status in rows:
        lines.append(f"  [ ] {label}: {status}")
    lines += [
        "",
        "ជំហាន ៣ — បើស្តារមិនបាន",
        "  • សាកល្បងពីឧបករណ៍/កន្លែងដែលធ្លាប់ចូល (Wi-Fi ផ្ទះ, ទូរស័ព្ទចាស់)",
        "  • ប្រើ 'ស្តារដោយលេខទូរស័ព្ទ' បើអ្នកនៅមានលេខនោះ",
        "  • បើគណនីត្រូវបានផ្អាក → ប្រើ Google Account Recovery Form ឬជំនួយការ Google",
        f"  • បង្កើតគណនីថ្មី (ឈ្មោះថ្មី): {SIGNUP_URL}",
        "",
        "ជំហាន ៤ — ក្រោយស្តារបាន (សំខាន់)",
        f"  • ប្តូរលេខសម្ងាត់ថ្មី + បើក 2FA: {SECURITY_URL}",
        "  • ពិនិត្យឧបករណ៍ដែលបានចូល ហើយដកចេញឧបករណ៍មិនស្គាល់",
        "  • ពិនិត្យ Forwarding/POP/IMAP ក្នុង Gmail Settings → Forwarding and POP/IMAP",
        "  • រក្សាទុក 2FA secret ក្នុង Teta ដើម្បីបង្កើតកូដបានពេលក្រោយ",
        "",
        "ចំណាំសុវត្ថិភាព",
        "  • គ្មានឧបករណ៍ណាអាច 'ចាប់យកសារ' ចូលអ៊ីមែលដែលអ្នកមិនមានសិទ្ធិចូលបានទេ",
        "  • សារផ្ញើមកអ៊ីមែលដែលបាត់ នឹងមិនអាចអានបានដោយគ្មានការស្តារគណនីស្របច្បាប់",
        "  • កុំផ្តល់លេខសម្ងាត់/កូដ 2FA ដល់អ្នកបម្រើ 'ស្តារគណនី' ណាមួយ — ទាំងអស់នោះជាការបោកប្រាស់",
    ]
    return "\n".join(lines)


def status(account: Account) -> dict:
    """សង្ខេបស្ថានភាពរៀបចំសម្រាប់ការស្តារ។"""
    filled = sum(1 for _, value in build_plan(account) if value != "ត្រូវរៀបចំ")
    return {
        "email": account.email,
        "has_note": bool(account.note),
        "has_tags": bool(account.tags),
        "has_totp": bool(account.totp_secret),
        "ready_items": filled,
        "total_items": len(CHECKLIST),
    }


def save_guide(account: Account, directory: "Path | str") -> Path:
    """សរសេរផែនការចូលឯកសារ (ដើម្បីយកទៅបំពេញក្រៅ app)។"""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    safe = account.email.replace("@", "_at_").replace("/", "_")
    target = directory / f"recovery-{safe}.txt"
    target.write_text(recovery_guide(account), encoding="utf-8")
    try:
        import os
        os.chmod(target, 0o600)
    except OSError:
        pass
    return target


def find_account(vault: Vault, email: str) -> "Account | None":
    if not is_valid_email(email):
        raise RecoveryError("អ៊ីមែលមិនត្រឹមត្រូវ (ត្រូវជា name@gmail.com)")
    return vault.find(email)
