"""Command line interface របស់ Teta។"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import sys
import time
from pathlib import Path

from . import __version__
from .generator import RESERVED_DOMAINS, generate, is_valid_email, normalize_localpart
from .store import Account, StoreError, Vault
from .crypto import CryptoError
from . import totp

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
    email = args.email.strip().lower()
    if not is_valid_email(email):
        die("អ៊ីមែលមិនត្រឹមត្រូវ (ត្រូវជា name@gmail.com)")
    vault = open_vault(args)
    secret = (args.totp or "").strip()
    if secret:
        secret = totp.normalize_secret(secret)
        try:
            totp.code_at(secret)
        except ValueError as exc:
            die(str(exc))
    acc = Account(
        email=email,
        label=args.label or "",
        tags=[t.strip() for t in (args.tags or "").split(",") if t.strip()],
        totp_secret=secret,
        note=args.note or "",
    )
    try:
        vault.add(acc)
    except StoreError as exc:
        die(str(exc))
    print(c("✔ បន្ថែមរួចរាល់", GREEN) + f" {email}")
    if secret:
        print(f"  2FA code ឥឡូវ៖ {c(totp.code_at(secret), CYAN)}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    vault = open_vault(args)
    accounts = vault.accounts
    if args.tag:
        accounts = [a for a in accounts if args.tag.lower() in [t.lower() for t in a.tags]]
    if args.json:
        print(json.dumps([a.to_dict() | {"has_totp": bool(a.totp_secret)} for a in accounts],
                         ensure_ascii=False, indent=2))
        return 0
    if not accounts:
        print(c("(ទំនេរ) គ្មានគណនីទេ", DIM))
        return 0
    print(c(f"{_pad('EMAIL', 36)}{_pad('LABEL', 20)}{_pad('2FA', 6)}TAGS", BOLD))
    for acc in accounts:
        totp_mark = "✔" if acc.totp_secret else "-"
        print(f"{_pad(acc.email, 36)}{_pad(acc.label, 20)}{_pad(totp_mark, 6)}"
              f"{','.join(acc.tags)}")
    print(c(f"\nសរុប {len(accounts)} គណនី", DIM))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    vault = open_vault(args)
    acc = vault.find(args.email)
    if not acc:
        die(f"រកមិនឃើញ {args.email}")
    created = time.strftime("%Y-%m-%d %H:%M", time.localtime(acc.created_at))
    print(c(acc.email, BOLD))
    print(f"  label   : {acc.label or '-'}")
    print(f"  tags    : {', '.join(acc.tags) or '-'}")
    print(f"  note    : {acc.note or '-'}")
    print(f"  created : {created}")
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
    acc = vault.find(args.email)
    if not acc:
        die(f"រកមិនឃើញ {args.email}")
    if not args.yes:
        try:
            answer = input(f"លុប {acc.email} ចេញពី vault? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return 1
        if answer not in ("y", "yes", "យ"):
            print("បោះបង់")
            return 1
    vault.remove(acc.email)
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
    acc = vault.find(args.email)
    if not acc:
        die(f"រកមិនឃើញ {args.email}")
    if not acc.totp_secret:
        die(f"{acc.email} មិនមាន 2FA secret ទេ — បន្ថែមដោយ `teta set-totp`")
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
    acc = vault.find(args.email)
    if not acc:
        die(f"រកមិនឃើញ {args.email}")
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
            if q in a.email.lower() or q in a.label.lower()
            or any(q in t.lower() for t in a.tags)]
    if not hits:
        print(c("រកមិនឃើញ", DIM))
        return 1
    for acc in hits:
        print(acc.email)
    return 0


def cmd_menu(args: argparse.Namespace) -> int:
    from .menu import menu as open_menu
    return open_menu(getattr(args, "home", None))


# ---------------- parser ----------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="teta",
        description="ឧបករណ៍គ្រប់គ្រងគណនី Gmail + បង្កើតឈ្មោះថ្មី + 2FA TOTP (offline, Termux)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="ឧទាហរណ៍:\n"
               "  teta init\n"
               "  teta gen --seed sokha --count 8\n"
               "  teta add sokha.chan@gmail.com --label \"main\" --totp JBSWY3DPEHPK3PXP\n"
               "  teta list\n"
               "  teta code sokha.chan@gmail.com --watch\n",
    )
    p.add_argument("--version", action="version", version=f"teta {__version__}")
    p.add_argument("--menu", action="store_true", help="បើក menu អន្តរកម្ម")
    p.add_argument("--home", dest="home", default=None,
                   help="ថតសម្រាប់ vault (default: ~/.teta)")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser("init", help="បង្កើត vault ថ្មី").set_defaults(func=cmd_init)

    a = sub.add_parser("add", help="បន្ថែមគណនី")
    a.add_argument("email")
    a.add_argument("--label", default="")
    a.add_argument("--tags", default="")
    a.add_argument("--totp", default="", help="2FA secret (base32) ឬ otpauth:// URI")
    a.add_argument("--note", default="")
    a.set_defaults(func=cmd_add)

    l = sub.add_parser("list", help="បញ្ជីគណនី")
    l.add_argument("--tag", default="")
    l.add_argument("--json", action="store_true")
    l.set_defaults(func=cmd_list)

    s = sub.add_parser("show", help="បង្ហាញព័ត៌មានគណនី")
    s.add_argument("email")
    s.add_argument("--reveal", action="store_true", help="បង្ហាញ 2FA key ពេញ")
    s.set_defaults(func=cmd_show)

    r = sub.add_parser("rm", help="លុបគណនី")
    r.add_argument("email")
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
    cd.add_argument("email")
    cd.add_argument("--watch", "-w", action="store_true", help="បង្ហាញផ្ទាល់រាល់វិនាទី")
    cd.set_defaults(func=cmd_code)

    st = sub.add_parser("set-totp", help="កំណត់/ផ្លាស់ប្តូរ 2FA secret")
    st.add_argument("email")
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

    mn = sub.add_parser("menu", help="menu អន្តរកម្ម (ងាយប្រើ)")
    mn.set_defaults(func=cmd_menu)

    se = sub.add_parser("search", help="ស្វែងរកគណនី")
    se.add_argument("query")
    se.set_defaults(func=cmd_search)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "menu", False):
        return cmd_menu(args)
    if not getattr(args, "command", None):
        interactive = sys.stdin.isatty() and os.environ.get("TETA_NO_MENU") is None
        if interactive or os.environ.get("TETA_FORCE_MENU"):
            return cmd_menu(args)
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
