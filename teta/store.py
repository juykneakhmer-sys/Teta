"""ឃ្លាំងទិន្នន័យ (vault) សម្រាប់គណនី — ទាំងអស់អ៊ិនគ្រីបដោយ master password។"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from . import crypto

DEFAULT_DIR = Path(os.environ.get("TETA_HOME", Path.home() / ".teta"))
VAULT_NAME = "vault.json"
SALT_NAME = "vault.salt"          # សម្រាប់ផ្ទៀងផ្ទាត់លេខសម្ងាត់ពេលបើក
ITER_NAME = "vault.check"


class StoreError(Exception):
    pass


@dataclass
class Account:
    email: str
    label: str = ""
    tags: list[str] = field(default_factory=list)
    totp_secret: str = ""          # 2FA secret (base32) — offline TOTP
    note: str = ""                 # ចំណាំឯកជន (ដូចជា recovery email hint)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Account":
        known = {k: v for k, v in data.items() if k in cls.__annotations__}
        return cls(**known)


class Vault:
    """គ្រប់គ្រងឯកសារ vault + បញ្ជីគណនី។"""

    def __init__(self, base_dir: Path | str | None = None) -> None:
        self.base = Path(base_dir) if base_dir else DEFAULT_DIR
        self.path = self.base / VAULT_NAME
        self._password: str | None = None
        self.accounts: list[Account] = []

    # ---------- lifecycle ----------
    def exists(self) -> bool:
        return self.path.exists()

    def init(self, password: str) -> None:
        if self.exists():
            raise StoreError("vault មានរួចហើយ")
        if len(password) < 6:
            raise StoreError("លេខសម្ងាត់ត្រូវមានយ៉ាងតិច 6 តួ")
        self.base.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._password = password
        self.accounts = []
        self.save()
        self._chmod_private()

    def unlock(self, password: str) -> None:
        if not self.exists():
            raise StoreError("មិនទាន់មាន vault ទេ — សូមដំណើរការ `teta init` សិន")
        try:
            raw = self.path.read_text(encoding="utf-8")
            plain = crypto.decrypt(password, raw)
        except crypto.CryptoError as exc:
            raise StoreError(str(exc)) from exc
        data = json.loads(plain.decode("utf-8"))
        self.accounts = [Account.from_dict(a) for a in data.get("accounts", [])]
        self._password = password

    def lock(self) -> None:
        self._password = None
        self.accounts = []

    def save(self) -> None:
        if self._password is None:
            raise StoreError("vault មិនទាន់បើកទេ")
        payload = {
            "schema": 1,
            "updated_at": time.time(),
            "accounts": [a.to_dict() for a in self.accounts],
        }
        blob = crypto.encrypt(self._password, json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        self.base.mkdir(parents=True, exist_ok=True, mode=0o700)
        # atomic write
        fd, tmp = tempfile.mkstemp(dir=str(self.base), prefix=".vault-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(blob)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        self._chmod_private()

    def _chmod_private(self) -> None:
        try:
            os.chmod(self.base, 0o700)
            for p in self.base.iterdir():
                if p.is_file():
                    os.chmod(p, 0o600)
        except OSError:
            pass

    def change_password(self, new_password: str) -> None:
        if len(new_password) < 6:
            raise StoreError("លេខសម្ងាត់ថ្មីត្រូវមានយ៉ាងតិច 6 តួ")
        self._password = new_password
        self.save()

    def backup_to(self, dest: Path | str) -> Path:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.path, dest)
        try:
            os.chmod(dest, 0o600)
        except OSError:
            pass
        return dest

    # ---------- accounts ----------
    def find(self, email: str) -> Account | None:
        email = email.strip().lower()
        for acc in self.accounts:
            if acc.email.lower() == email:
                return acc
        return None

    def add(self, account: Account) -> Account:
        if self.find(account.email):
            raise StoreError(f"{account.email} មាននៅក្នុង vault រួចហើយ")
        self.accounts.append(account)
        self.save()
        return account

    def remove(self, email: str) -> bool:
        acc = self.find(email)
        if not acc:
            return False
        self.accounts.remove(acc)
        self.save()
        return True

    def update(self, account: Account) -> None:
        for i, acc in enumerate(self.accounts):
            if acc.email.lower() == account.email.lower():
                account.updated_at = time.time()
                self.accounts[i] = account
                self.save()
                return
        raise StoreError(f"រកមិនឃើញ {account.email} ក្នុង vault")
