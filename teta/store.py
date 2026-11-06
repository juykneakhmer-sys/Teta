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
SCHEMA = 2                        # v2 = គណនីហ្គេម/គេហទំព័រ + password + server

# ប្រភេទគណនីដែលគាំទ្រ
KINDS = ("gmail", "moonton", "game", "social", "email", "other")


class StoreError(Exception):
    pass


@dataclass
class Account:
    email: str = ""                # អ៊ីមែល ឬទំនេរបើគណនីប្រើ login name
    label: str = ""
    tags: list[str] = field(default_factory=list)
    totp_secret: str = ""          # 2FA secret (base32) — offline TOTP
    note: str = ""                 # ចំណាំឯកជន
    kind: str = "gmail"            # gmail | moonton | game | social | email | other
    username: str = ""             # login name / game ID (ឧ. MLBB ID)
    password: str = ""             # លេខសម្ងាត់គណនី (អ៊ិនគ្រីបក្នុង vault)
    server: str = ""               # server / zone (ឧ. MLBB Zone ID)
    url: str = ""                  # ទំព័រចូល ឬ app scheme
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Account":
        known = {k: v for k, v in data.items() if k in cls.__annotations__}
        obj = cls(**known)
        if obj.kind not in KINDS:
            obj.kind = "other"
        return obj

    @property
    def key(self) -> str:
        """ឈ្មោះយោងសម្រាប់បង្ហាញ/វាយក្នុង CLI។"""
        return self.email or self.username or self.label


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
            "schema": SCHEMA,
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
            if acc.email and acc.email.lower() == email:
                return acc
        return None

    def resolve(self, key: str) -> Account | None:
        """រកគណនីដោយ អ៊ីមែល → login name → label (ត្រូវតែមានតែមួយ)។"""
        key = (key or "").strip()
        if not key:
            return None
        low = key.lower()
        hit = self.find(low)
        if hit:
            return hit
        for acc in self.accounts:
            if acc.username and acc.username.lower() == low:
                return acc
        by_label = [a for a in self.accounts if a.label and a.label.lower() == low]
        if len(by_label) == 1:
            return by_label[0]
        return None

    def _duplicate(self, account: Account) -> Account | None:
        for acc in self.accounts:
            if account.email and acc.email and acc.email.lower() == account.email.lower():
                return acc
            if (account.username and acc.username
                    and acc.kind == account.kind
                    and acc.username.lower() == account.username.lower()):
                return acc
        return None

    def add(self, account: Account) -> Account:
        dup = self._duplicate(account)
        if dup:
            raise StoreError(f"{account.key} មាននៅក្នុង vault រួចហើយ")
        self.accounts.append(account)
        self.save()
        return account

    def remove(self, key: str) -> bool:
        acc = self.resolve(key)
        if not acc:
            return False
        self.accounts.remove(acc)
        self.save()
        return True

    def drop(self, account: Account) -> bool:
        """លុបតាម identity ត្រង់ៗ (មិនប្រើ key ដែលអាចច្រឡំ)។"""
        if account in self.accounts:
            self.accounts.remove(account)
            self.save()
            return True
        return False

    def update(self, account: Account) -> None:
        for i, acc in enumerate(self.accounts):
            same_email = acc.email and account.email and acc.email.lower() == account.email.lower()
            same_user = (acc.username and account.username
                         and acc.kind == account.kind
                         and acc.username.lower() == account.username.lower())
            if same_email or same_user:
                account.updated_at = time.time()
                self.accounts[i] = account
                self.save()
                return
        raise StoreError(f"រកមិនឃើញ {account.key} ក្នុង vault")

    def replace(self, old: Account, account: Account) -> None:
        """ជំនួសគណនីដែលមានស្រាប់ (សម្រាប់ `teta edit`)។"""
        acc = old if old in self.accounts else self.resolve(old.email or old.username)
        if acc is None or acc not in self.accounts:
            raise StoreError(f"រកមិនឃើញ {old.key} ក្នុង vault")
        account.created_at = acc.created_at
        account.updated_at = time.time()
        self.accounts[self.accounts.index(acc)] = account
        self.save()
