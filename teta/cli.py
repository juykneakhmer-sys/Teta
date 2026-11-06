"""Command line interface របស់ Teta។"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import __version__
from .generator import RESERVED_DOMAINS, generate, is_valid_email, normalize_localpart
from .store import KINDS, Account, StoreError, Vault
from .crypto import CryptoError
from . import audit, passgen, totp

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"


def _color_enabled() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def c(text: str, code: str) -> str:
    return f"{code}{text}{RESET}" if _color_enabled() else text


def _width(text: str) -> int:
    """ប្រវែងលើ terminal (អក្សរខ្មែរ/ចិន = ២ ជួរ)។"""
    import unicodedata
    total = 0
    for ch in text:
        total += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return total


def _pad(text: str, width: int) -> str:
    text = str(text)
    return text + " " * max(1, width - _width(text))


def die(message: str, code: int = 1) -> "NoReturn":  # type: ignore[name-defined]
    print(c("✖ ", RED) + message, file=sys.stderr)
    raise SystemExit(code)


def read_password(prompt: str, confirm: bool = False) -> str:
    env = os.environ.get("TETA_PASSWORD")
    if env:
        return env
    pw = getpass.getpass(prompt)
    if confirm:
        again = getpass.getpass("វាយលេខសម្ងាត់ម្តងទៀត: ")
        if pw != again:
            die("លេខសម្ងាត់មិនដូចគ្នាទេ")
    return pw


def open_vault(args: argparse.Namespace) -> Vault:
    vault = Vault(getattr(args, "home", None))
    if not vault.exists():
        die("មិនទាន់មាន vault ទេ — ដំណើរការ `teta init` សិន")
    password = read_password("លេខសម្ងាត់មេ: ")
    try:
        vault.unlock(password)
    except StoreError as exc:
        die(str(exc))
    return vault


def require_account(vault: Vault, key: str) -> Account:
    """រកគណនី ឬបញ្ចប់ដោយសារ (message) ដែលច្បាស់លាស់។"""
    acc = vault.resolve(key)
    if not acc:
        die(f"រកមិនឃើញ {key} — មើលបញ្ជីដោយ `teta list`")
    assert acc is not None
    return acc


def read_secret_value(value: str, prompt: str) -> str:
    """អានលេខសម្ងាត់ដោយសុវត្ថិភាព៖ `-` = អានពី stdin/terminal ដោយលាក់។"""
    if value == "-":
        if sys.stdin.isatty():
            return getpass.getpass(prompt)
        return sys.stdin.readline().rstrip("\n")
    return value


def copy_to_clipboard(text: str) -> bool:
    """ចម្លងចូល clipboard តាម termux-clipboard-set ឬឧបករណ៍ផ្សេង។"""
    candidates = (
        ("termux-clipboard-set", []),
        ("wl-copy", []),
        ("xclip", ["-selection", "clipboard"]),
        ("xsel", ["--clipboard", "--input"]),
        ("pbcopy", []),
    )
    for prog, extra in candidates:
        path = shutil.which(prog)
        if not path:
            continue
        try:
            proc = subprocess.run([path, *extra], input=text, text=True,
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL, timeout=5,
                                  check=False)
        except (OSError, subprocess.SubprocessError):
            continue
        if proc.returncode == 0:
            return True
    return False


def mask(value: str) -> str:
    if not value:
        return "-"
    if len(value) <= 4:
        return "•" * len(value)
    return value[:2] + "•" * (len(value) - 4) + value[-2:]


# ---------------- commands ----------------

def cmd_init(args: argparse.Namespace) -> int:
    vault = Vault(args.home)
    if vault.exists():
        die(f"vault មានរួចហើយ៖ {vault.path}")
    print(c("បង្កើត vault ថ្មី", BOLD) + f" → {vault.path}")
    print(c("សូមចងចាំលេខសម្ងាត់មេ៖ បើបាត់ ទិន្នន័យមិនអាចយកមកវិញបានទេ។", DIM))
    pw = read_password("លេខសម្ងាត់មេថ្មី: ", confirm=True)
    try:
        vault.init(pw)
    except StoreError as exc:
        die(str(exc))
    print(c("✔ រួចរាល់", GREEN) + f" — បន្ថែមគណនីដោយ៖ teta add you@gmail.com")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    ident = (args.ident or "").strip()
    if not ident:
        die("សូមផ្តល់អ៊ីមែល ឬ login name — ឧ. teta add sokha@gmail.com")
    looks_email = is_valid_email(ident)
    if "@" in ident and not looks_email:
        die("អ៊ីមែលមិនត្រឹមត្រូវ (ត្រូវជា name@gmail.com ឬ --kind ផ្សេង)")

    kind = args.kind
    if kind == "auto":
        if looks_email:
            kind = "gmail" if ident.lower().endswith(("@gmail.com", "@googlemail.com")) else "email"
        else:
            kind = "other"

    if kind == "gmail" and not looks_email:
        die("គណនី Gmail ត្រូវការអ៊ីមែលត្រឹមត្រូវ (name@gmail.com)")
    if kind not in KINDS:
        die(f"ប្រភេទមិនស្គាល់ — ជ្រើសពី៖ {', '.join(KINDS)}")

    password = read_secret_value(args.password, "លេខសម្ងាត់គណនី: ")
    if password and kind == "gmail" and len(password) < 8:
        die("លេខសម្ងាត់ខ្លីពេក (យ៉ាងតិច 8 តួ)")

    vault = open_vault(args)
    secret = (args.totp or "").strip()
    if secret:
        secret = totp.normalize_secret(secret)
        try:
            totp.code_at(secret)
        except ValueError as exc:
            die(str(exc))
    username = (args.user or "").strip() or ("" if looks_email else ident)
    acc = Account(
        email=ident.lower() if looks_email else "",
        label=args.label or "",
        tags=[t.strip() for t in (args.tags or "").split(",") if t.strip()],
        totp_secret=secret,
        note=args.note or "",
        kind=kind,
        username=username,
        password=password or "",
        server=(args.zone or "").strip(),
        url=(args.url or "").strip(),
    )
    try:
        vault.add(acc)
    except StoreError as exc:
        die(str(exc))
    print(c("✔ បន្ថែមរួចរាល់", GREEN) + f" {acc.key}  {c('[' + kind + ']', DIM)}")
    if secret:
        print(f"  2FA code ឥឡូវ៖ {c(totp.code_at(secret), CYAN)}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    vault = open_vault(args)
    accounts = vault.accounts
    if args.tag:
        accounts = [a for a in accounts if args.tag.lower() in [t.lower() for t in a.tags]]
    if args.kind:
        accounts = [a for a in accounts if a.kind == args.kind]
    if args.json:
        print(json.dumps([a.to_dict() | {"has_totp": bool(a.totp_secret)}
                          for a in accounts], ensure_ascii=False, indent=2))
        return 0
    if not accounts:
        print(c("(ទំនេរ) គ្មានគណនីទេ", DIM))
        return 0
    print(c(f"{_pad('KIND', 10)}{_pad('ACCOUNT', 36)}{_pad('LABEL', 18)}"
            f"{_pad('2FA', 5)}TAGS", BOLD))
    for acc in accounts:
        totp_mark = "✔" if acc.totp_secret else "-"
        kind_cell = _pad(acc.kind, 10)
        print(f"{c(kind_cell, DIM)}"
              f"{_pad(acc.key, 36)}{_pad(acc.label, 18)}{_pad(totp_mark, 5)}"
              f"{','.join(acc.tags)}")
    print(c(f"\nសរុប {len(accounts)} គណនី", DIM))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    vault = open_vault(args)
    acc = require_account(vault, args.email)
    created = time.strftime("%Y-%m-%d %H:%M", time.localtime(acc.created_at))
    updated = time.strftime("%Y-%m-%d %H:%M", time.localtime(acc.updated_at))
    print(c(acc.key, BOLD) + "  " + c(f"[{acc.kind}]", DIM))
    print(f"  email   : {acc.email or '-'}")
    print(f"  user/ID : {acc.username or '-'}")
    print(f"  password: {acc.password if args.reveal else mask(acc.password)}"
          + ("" if args.reveal or not acc.password else f"  {c('(--reveal)', DIM)}"))
    print(f"  server  : {acc.server or '-'}")
    print(f"  url     : {acc.url or '-'}")
    print(f"  label   : {acc.label or '-'}")
    print(f"  tags    : {', '.join(acc.tags) or '-'}")
    print(f"  note    : {acc.note or '-'}")
    print(f"  created : {created}")
    print(f"  updated : {updated}")
    if acc.totp_secret:
        if args.reveal:
            print(f"  2FA key : {acc.totp_secret}")
        else:
            masked = acc.totp_secret[:4] + "•" * max(0, len(acc.totp_secret) - 4)
            print(f"  2FA key : {masked}  {c('(--reveal ដើម្បីបង្ហាញ)', DIM)}")
        print(f"  2FA code: {c(totp.code_at(acc.totp_secret), CYAN)}"
              f"  {c(f'({totp.remaining_seconds()}s)', DIM)}")
    else:
        print("  2FA key : -")
    return 0


def cmd_rm(args: argparse.Namespace) -> int:
    vault = open_vault(args)
    acc = require_account(vault, args.email)
    if not args.yes:
        try:
            answer = input(f"លុប {acc.key} ចេញពី vault? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return 1
        if answer not in ("y", "yes", "យ"):
            print("បោះបង់")
            return 1
    vault.drop(acc)
    print(c("✔ លុបរួចរាល់", GREEN))
    return 0


def cmd_gen(args: argparse.Namespace) -> int:
    try:
        names = generate(args.count, args.seed, args.domain, args.min, args.max)
    except ValueError as exc:
        die(str(exc))
    if args.json:
        print(json.dumps(names, ensure_ascii=False, indent=2))
        return 0
    if args.seed:
        print(c(f"ផ្អែកលើ៖ {normalize_localpart(args.seed)}", DIM))
    for name in names:
        print(name)
    print(c("\nចំណាំ៖ ឈ្មោះទាំងនេះជា 'បេក្ខជន' ប៉ុណ្ណោះ — ត្រូវផ្ទៀងផ្ទាត់ថាទំនេរនៅ "
            "accounts.google.com/signup ដោយខ្លួនឯង។", DIM))
    return 0


def cmd_code(args: argparse.Namespace) -> int:
    vault = open_vault(args)
    acc = require_account(vault, args.email)
    if not acc.totp_secret:
        die(f"{acc.key} មិនមាន 2FA secret ទេ — បន្ថែមដោយ `teta set-totp`")
    if not args.watch:
        print(totp.code_at(acc.totp_secret))
        return 0
    try:
        while True:
            left = totp.remaining_seconds()
            bar = "█" * (left // 2) + "░" * (15 - left // 2)
            print(f"\r{c(totp.code_at(acc.totp_secret), BOLD + CYAN)}  {bar} {left:>2}s ",
                  end="", flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        print()
        return 0


def cmd_set_totp(args: argparse.Namespace) -> int:
    vault = open_vault(args)
    acc = require_account(vault, args.email)
    secret = totp.normalize_secret(args.secret)
    try:
        code = totp.code_at(secret)
    except ValueError as exc:
        die(str(exc))
    acc.totp_secret = secret
    vault.update(acc)
    print(c("✔ កំណត់ 2FA secret រួចរាល់", GREEN) + f" — code ឥឡូវ៖ {code}")
    return 0


def cmd_passwd(args: argparse.Namespace) -> int:
    vault = open_vault(args)
    new = read_password("លេខសម្ងាត់មេថ្មី: ", confirm=True)
    try:
        vault.change_password(new)
    except StoreError as exc:
        die(str(exc))
    print(c("✔ ផ្លាស់ប្តូរលេខសម្ងាត់រួចរាល់", GREEN))
    return 0


def cmd_backup(args: argparse.Namespace) -> int:
    vault = Vault(args.home)
    if not vault.exists():
        die("មិនទាន់មាន vault ទេ")
    dest = Path(args.out) if args.out else vault.base / "backups"
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = dest / f"teta-vault-{stamp}.json"
    vault.backup_to(target)
    print(c("✔ backup រួចរាល់", GREEN) + f" → {target}")
    print(c("ឯកសារនេះនៅអ៊ិនគ្រីបដូចដើម — ត្រូវការលេខសម្ងាត់មេដើម្បីបើក។", DIM))
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    src = Path(args.file)
    if not src.exists():
        die(f"រកមិនឃើញឯកសារ {src}")
    try:
        json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        die("ឯកសារ backup មិនត្រឹមត្រូវ")
    vault = Vault(args.home)
    if vault.exists() and not args.force:
        die("vault មានរួចហើយ — ប្រើ --force ដើម្បីសរសេរជំនួស")
    vault.base.mkdir(parents=True, exist_ok=True, mode=0o700)
    shutil.copy2(src, vault.path)
    try:
        os.chmod(vault.path, 0o600)
    except OSError:
        pass
    print(c("✔ ស្តាររួចរាល់", GREEN) + f" → {vault.path}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    vault = Vault(args.home)
    print(c("Teta", BOLD) + f" v{__version__}")
    print(f"  ទីតាំង vault : {vault.path}")
    print(f"  មាន vault    : {'បាទ/ចាស' if vault.exists() else 'ទេ'}")
    if vault.exists():
        size = vault.path.stat().st_size
        print(f"  ទំហំ          : {size} bytes")
        print(f"  កែចុងក្រោយ    : "
              f"{time.strftime('%Y-%m-%d %H:%M', time.localtime(vault.path.stat().st_mtime))}")
    print(f"  python        : {sys.version.split()[0]}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    vault = open_vault(args)
    q = args.query.lower()
    hits = [a for a in vault.accounts
            if q in a.key.lower() or q in a.label.lower()
            or q in a.username.lower() or q in a.note.lower()
            or any(q in t.lower() for t in a.tags)]
    if not hits:
        print(c("រកមិនឃើញ", DIM))
        return 1
    for acc in hits:
        print(f"{acc.key}{c('  [' + acc.kind + ']', DIM)}")
    return 0


def cmd_edit(args: argparse.Namespace) -> int:
    vault = open_vault(args)
    acc = require_account(vault, args.email)
    edited = Account.from_dict(acc.to_dict())
    changed: list[str] = []

    if args.label is not None:
        edited.label = args.label
        changed.append("label")
    if args.tags is not None:
        edited.tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        changed.append("tags")
    if args.note is not None:
        edited.note = args.note
        changed.append("note")
    if args.kind is not None:
        edited.kind = args.kind
        changed.append("kind")
    if args.user is not None:
        edited.username = args.user.strip()
        changed.append("username")
    if args.zone is not None:
        edited.server = args.zone.strip()
        changed.append("server")
    if args.url is not None:
        edited.url = args.url.strip()
        changed.append("url")
    if args.email_new is not None:
        new_email = args.email_new.strip().lower()
        if new_email and not is_valid_email(new_email):
            die("អ៊ីមែលថ្មីមិនត្រឹមត្រូវ")
        edited.email = new_email
        changed.append("email")
    if args.password is not None:
        edited.password = read_secret_value(args.password, "លេខសម្ងាត់ថ្មី: ")
        changed.append("password")
    if args.totp is not None:
        secret = args.totp.strip()
        if secret:
            secret = totp.normalize_secret(secret)
            try:
                totp.code_at(secret)
            except ValueError as exc:
                die(str(exc))
        edited.totp_secret = secret
        changed.append("2FA")

    if not changed:
        die("គ្មានអ្វីត្រូវកែទេ — ប្រើ --label/--tags/--note/--password/--totp ...")
    if edited.kind == "gmail" and not is_valid_email(edited.email):
        die("គណនី Gmail ត្រូវការអ៊ីមែលត្រឹមត្រូវ")
    if not edited.email and not edited.username:
        die("ត្រូវមានអ៊ីមែល ឬ username យ៉ាងតិចមួយ")
    try:
        vault.replace(acc, edited)
    except StoreError as exc:
        die(str(exc))
    print(c("✔ កែរួចរាល់", GREEN) + f" {edited.key} — {', '.join(changed)}")
    return 0


def cmd_copy(args: argparse.Namespace) -> int:
    vault = open_vault(args)
    acc = require_account(vault, args.email)
    values = {
        "password": acc.password,
        "username": acc.username,
        "email": acc.email,
        "server": acc.server,
        "url": acc.url,
        "note": acc.note,
        "label": acc.label,
        "totp": totp.code_at(acc.totp_secret) if acc.totp_secret else "",
    }
    value = values.get(args.field, "")
    if not value:
        die(f"{acc.key} គ្មាន '{args.field}' ទេ")
    label = f"{acc.key}:{args.field}"
    if copy_to_clipboard(value):
        print(c("✔ ចម្លងចូល clipboard", GREEN) + f" ({label})")
        if args.clear_after > 0:
            _schedule_clipboard_clear(args.clear_after)
    else:
        if not sys.stdout.isatty():
            print(value)
            return 0
        print(c("⚠ រកមិនឃើញ clipboard tool — តម្លៃនៅខាងក្រោម", YELLOW))
        print(value)
        print(c("  ដំឡើង: pkg install termux-api (និង app Termux:API)", DIM))
    return 0


def _schedule_clipboard_clear(seconds: int) -> None:
    import threading

    def worker() -> None:
        time.sleep(seconds)
        copy_to_clipboard("")

    threading.Thread(target=worker, daemon=True).start()
    print(c(f"  clipboard នឹងត្រូវសម្អាតក្នុង {seconds}s", DIM))


def cmd_export(args: argparse.Namespace) -> int:
    vault = open_vault(args)
    accounts = vault.accounts
    if args.kind:
        accounts = [a for a in accounts if a.kind == args.kind]

    fields = ["kind", "key", "email", "username", "password", "server", "url",
              "label", "tags", "note", "totp_secret"]
    rows = []
    for acc in accounts:
        row = acc.to_dict()
        row["key"] = acc.key
        row["tags"] = ",".join(acc.tags)
        rows.append({f: row.get(f, "") for f in fields})

    if args.format == "json":
        payload = json.dumps(rows, ensure_ascii=False, indent=2)
    else:
        import csv
        import io

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        payload = buf.getvalue()

    if args.out in ("-", ""):
        if not sys.stdin.isatty() and not args.yes:
            die("បញ្ចេញ plaintext ទៅ stdout ត្រូវការ --yes")
        print(payload, end="")
        return 0

    target = Path(args.out)
    if not args.yes:
        print(c("⚠ ការនេះនឹងសរសេរលេខសម្ងាត់ជា plaintext (មិនអ៊ិនគ្រីប)!", YELLOW))
        try:
            answer = input(f"សរសេរទៅ {target}? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return 1
        if answer not in ("y", "yes", "យ"):
            print("បោះបង់")
            return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(payload)
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass
    print(c("✔ export រួចរាល់", GREEN) + f" → {target} ({len(rows)} គណនី, plaintext)")
    print(c("  លុបឯកសារនេះភ្លាមក្រោយប្រើ — កុំទុកក្នុង cloud/git។", DIM))
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    vault = open_vault(args)
    findings = audit.audit_accounts(vault.accounts)
    points = audit.score(vault.accounts, findings)

    if args.json:
        print(json.dumps({"score": points,
                          "findings": [f.__dict__ for f in findings]},
                         ensure_ascii=False, indent=2))
        return 0 if not findings else 0

    colors = {audit.ERROR: RED, audit.WARN: YELLOW, audit.INFO: CYAN}
    icons = {audit.ERROR: "✖", audit.WARN: "⚠", audit.INFO: "ℹ"}
    if not findings:
        print(c("✔ គ្មានបញ្ហារកឃើញ — គណនីរបស់អ្នកមានសុខភាពល្អ", GREEN))
    else:
        for f in findings:
            print(f"{c(icons.get(f.level, '•'), colors.get(f.level, DIM))} "
                  f"{c(f.key, BOLD)} — {f.message}")
    bar_len = 20
    filled = round(points / 100 * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    tone = GREEN if points >= 80 else (YELLOW if points >= 50 else RED)
    print(f"\nពិន្ទុសុវត្ថិភាព: {c(f'{points}/100', tone + BOLD)}  {bar}")
    return 0


def cmd_genpass(args: argparse.Namespace) -> int:
    try:
        if args.phrase:
            value = passgen.generate_passphrase(args.words, args.separator,
                                                args.capitalize)
        else:
            value = passgen.generate_password(
                args.length, symbols=not args.no_symbols,
                digits=not args.no_digits, upper=not args.no_upper,
                ambiguous=args.ambiguous,
            )
    except ValueError as exc:
        die(str(exc))
    if args.json:
        print(json.dumps({"password": value,
                          "entropy_bits": passgen.entropy_bits(value),
                          "strength": passgen.strength_label(passgen.entropy_bits(value))},
                         ensure_ascii=False))
        return 0
    print(value)
    if args.verbose:
        bits = passgen.entropy_bits(value)
        print(c(f"  ~{bits} bits · {passgen.strength_label(bits)}", DIM),
              file=sys.stderr)
    return 0


def cmd_recovery(args: argparse.Namespace) -> int:
    """ណែនាំផ្លូវផ្លូវការ ពេលបាត់ការចូលគណនី (គ្មានការតភ្ជាប់បណ្តាញ)។"""
    topic = args.topic
    print(c("ការស្តារគណនី — ផ្លូវផ្លូវការតែមួយគត់", BOLD))
    print()

    if topic in ("all", "moonton"):
        print(c("Mobile Legends / Moonton", BOLD))
        print("  1. account.moontongames.com → ចូលដោយ email/phone/third-party")
        print("     បើចូលបាន → ប្តូរ email/លេខសម្ងាត់បានភ្លាម (ឥតគិតថ្លៃ)")
        print("  2. បើចូលមិនបាន → 'Forgot Password' ឬ 'Account Recovery'")
        print("  3. បើជាប់លក្ខខណ្ឌ → ticket ទៅ Moonton Support ជាមួយ៖")
        print("     • Game ID + Zone ID (ឃើញក្នុង profile ហ្គេម)")
        print("     • ថ្ងៃ/ខែ/ឆ្នាំ បង្កើតគណនី និង server ដែលលេងញឹកញាប់")
        print("     • invoice ទិញ diamond (Google Play / App Store) — សំខាន់បំផុត")
        print("     • ឈ្មោះ device ដែលធ្លាប់ចូល និងឈ្មោះគណនីសង្គមដែលភ្ជាប់")
        print()

    if topic in ("all", "google"):
        print(c("Gmail / Google", BOLD))
        print("  1. accounts.google.com/signup/recovery → ស្តារតាមជំហាន")
        print("  2. បើបាត់អ៊ីមែលស្តារ → https://g.co/recover (ឆ្លើយសំណួរ device/ការទូទាត់)")
        print("  3. មានការទិញ Play Store → ប្រើ invoice ជាភស្តុតាងភាពជាម្ចាស់")
        print()

    print(c("សំគាល់", BOLD) + " — Teta មិនចូលគណនីជំនួសអ្នក និងមិនផ្លាស់ email ភ្ជាប់តាម token ទេ។")
    print(c("ការធ្វើបែបនោះគឺជា account takeover — ខុសច្បាប់ និងធ្វើឱ្យគណនីត្រូវផ្អាក។", DIM))
    return 0


# ---------------- parser ----------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="teta",
        description="ឧបករណ៍គ្រប់គ្រងគណនីផ្ទាល់ខ្លួន (Gmail, Moonton/MLBB, ហ្គេម, social) — vault អ៊ិនគ្រីប + 2FA + audit (offline, Termux)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="ឧទាហរណ៍:\n"
               "  teta init\n"
               "  teta add sokha.chan@gmail.com --label \"main\" --totp JBSWY3DPEHPK3PXP\n"
               "  teta add 123456789 --kind moonton --user 123456789 --zone 2001 --pass -\n"
               "  teta list --kind moonton\n"
               "  teta copy 123456789 -f password\n"
               "  teta audit\n",
    )
    p.add_argument("--version", action="version", version=f"teta {__version__}")
    p.add_argument("--home", dest="home", default=None,
                   help="ថតសម្រាប់ vault (default: ~/.teta)")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser("init", help="បង្កើត vault ថ្មី").set_defaults(func=cmd_init)

    a = sub.add_parser("add", help="បន្ថែមគណនី (Gmail, Moonton, ហ្គេម, ...)")
    a.add_argument("ident", metavar="EMAIL|USERNAME",
                   help="អ៊ីមែល ឬ login name (ឧ. MLBB ID)")
    a.add_argument("--kind", default="auto", choices=("auto", *KINDS),
                   help="ប្រភេទគណនី (default: auto)")
    a.add_argument("--user", default="", help="username / game ID")
    a.add_argument("--pass", dest="password", default="",
                   help="លេខសម្ងាត់គណនី — ប្រើ '-' ដើម្បីវាយដោយលាក់ (សុវត្ថិភាពជាង)")
    a.add_argument("--zone", default="", help="server / zone (ឧ. MLBB Zone ID)")
    a.add_argument("--url", default="", help="ទំព័រចូល ឬ app scheme")
    a.add_argument("--label", default="")
    a.add_argument("--tags", default="")
    a.add_argument("--totp", default="", help="2FA secret (base32) ឬ otpauth:// URI")
    a.add_argument("--note", default="")
    a.set_defaults(func=cmd_add)

    l = sub.add_parser("list", help="បញ្ជីគណនី")
    l.add_argument("--tag", default="")
    l.add_argument("--kind", default="", choices=("", *KINDS))
    l.add_argument("--json", action="store_true")
    l.set_defaults(func=cmd_list)

    s = sub.add_parser("show", help="បង្ហាញព័ត៌មានគណនី")
    s.add_argument("email", metavar="KEY")
    s.add_argument("--reveal", action="store_true", help="បង្ហាញ password / 2FA key ពេញ")
    s.set_defaults(func=cmd_show)

    ed = sub.add_parser("edit", help="កែព័ត៌មានគណនី")
    ed.add_argument("email", metavar="KEY")
    ed.add_argument("--label")
    ed.add_argument("--tags")
    ed.add_argument("--note")
    ed.add_argument("--kind", choices=KINDS)
    ed.add_argument("--user")
    ed.add_argument("--pass", dest="password", help="លេខសម្ងាត់ថ្មី ('-' = វាយលាក់)")
    ed.add_argument("--zone")
    ed.add_argument("--url")
    ed.add_argument("--email-new", dest="email_new")
    ed.add_argument("--totp", help="2FA secret ថ្មី ('' ដើម្បីលុប)")
    ed.set_defaults(func=cmd_edit)

    cp = sub.add_parser("copy", help="ចម្លង password/username/2FA ចូល clipboard")
    cp.add_argument("email", metavar="KEY")
    cp.add_argument("--field", "-f", default="password",
                    choices=("password", "username", "email", "server", "url",
                             "note", "label", "totp"))
    cp.add_argument("--clear-after", type=int, default=0, metavar="SEC",
                    help="សម្អាត clipboard ក្រោយ N វិនាទី")
    cp.set_defaults(func=cmd_copy)

    gp = sub.add_parser("genpass", help="បង្កើតលេខសម្ងាត់ខ្លាំង (offline)")
    gp.add_argument("--length", "-L", type=int, default=20)
    gp.add_argument("--phrase", action="store_true", help="បង្កើត passphrase ពាក្យ")
    gp.add_argument("--words", type=int, default=4)
    gp.add_argument("--separator", default="-")
    gp.add_argument("--capitalize", action="store_true")
    gp.add_argument("--no-symbols", action="store_true")
    gp.add_argument("--no-digits", action="store_true")
    gp.add_argument("--no-upper", action="store_true")
    gp.add_argument("--ambiguous", action="store_true", help="អនុញ្ញាត 0/O/1/l/I")
    gp.add_argument("--json", action="store_true")
    gp.add_argument("--verbose", "-v", action="store_true")
    gp.set_defaults(func=cmd_genpass)

    au = sub.add_parser("audit", help="ពិនិត្យសុវត្ថិភាពគណនី (offline)")
    au.add_argument("--json", action="store_true")
    au.set_defaults(func=cmd_audit)

    ex = sub.add_parser("export", help="export ជា CSV/JSON (plaintext — ប្រយ័ត្ន)")
    ex.add_argument("--format", choices=("csv", "json"), default="csv")
    ex.add_argument("--out", "-o", default="-", help="ឯកសារ ឬ '-' សម្រាប់ stdout")
    ex.add_argument("--kind", default="", choices=("", *KINDS))
    ex.add_argument("--yes", "-y", action="store_true")
    ex.set_defaults(func=cmd_export)

    r = sub.add_parser("rm", help="លុបគណនី")
    r.add_argument("email", metavar="KEY")
    r.add_argument("--yes", "-y", action="store_true")
    r.set_defaults(func=cmd_rm)

    g = sub.add_parser("gen", help="បង្កើតឈ្មោះគណនីថ្មី (candidates)")
    g.add_argument("--seed", default="", help="ឈ្មោះ/ពាក្យគន្លឹះ ដើម្បីបង្កើតពី")
    g.add_argument("--count", "-n", type=int, default=10)
    g.add_argument("--min", type=int, default=8)
    g.add_argument("--max", type=int, default=24)
    g.add_argument("--domain", default="gmail.com", choices=RESERVED_DOMAINS)
    g.add_argument("--json", action="store_true")
    g.set_defaults(func=cmd_gen)

    cd = sub.add_parser("code", help="បង្កើតកូដ 2FA បច្ចុប្បន្ន")
    cd.add_argument("email", metavar="KEY")
    cd.add_argument("--watch", "-w", action="store_true", help="បង្ហាញផ្ទាល់រាល់វិនាទី")
    cd.set_defaults(func=cmd_code)

    st = sub.add_parser("set-totp", help="កំណត់/ផ្លាស់ប្តូរ 2FA secret")
    st.add_argument("email", metavar="KEY")
    st.add_argument("secret")
    st.set_defaults(func=cmd_set_totp)

    sub.add_parser("passwd", help="ផ្លាស់ប្តូរលេខសម្ងាត់មេ").set_defaults(func=cmd_passwd)

    b = sub.add_parser("backup", help="backup vault (នៅអ៊ិនគ្រីប)")
    b.add_argument("--out", default="")
    b.set_defaults(func=cmd_backup)

    rs = sub.add_parser("restore", help="ស្តារ vault ពី backup")
    rs.add_argument("file")
    rs.add_argument("--force", action="store_true")
    rs.set_defaults(func=cmd_restore)

    sub.add_parser("info", help="បង្ហាញព័ត៌មានកម្មវិធី").set_defaults(func=cmd_info)

    rec = sub.add_parser("recovery", help="ណែនាំផ្លូវស្តារគណនីផ្លូវការ")
    rec.add_argument("--topic", choices=("all", "moonton", "google"), default="all")
    rec.set_defaults(func=cmd_recovery)

    se = sub.add_parser("search", help="ស្វែងរកគណនី")
    se.add_argument("query")
    se.set_defaults(func=cmd_search)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    try:
        return int(args.func(args) or 0)
    except SystemExit as exc:          # die() ខាងក្នុង command
        return int(exc.code or 0)
    except KeyboardInterrupt:
        print()
        return 130
    except (StoreError, CryptoError) as exc:
        die(str(exc))
    except BrokenPipeError:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
