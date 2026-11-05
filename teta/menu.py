"""Menu អន្តរកម្ម (interactive) សម្រាប់ Teta — ងាយប្រើសម្រាប់ទូរស័ព្ទ។

លក្ខណៈ
  • បើក vault តែម្តង ហើយប្រើបានពេញ session (មិនសួរលេខសម្ងាត់រាល់ដង)
  • header ថេរ + ស្ថានភាព vault/ចំនួនគណនី
  • ជ្រើសដោយលេខ ឬអក្សរកាត់ (a/l/c/g/s/…)
  • ជ្រើសគណនីពីបញ្ជីដោយលេខ (មិនត្រូវវាយអ៊ីមែល)
  • Ctrl+C → ត្រឡប់ទៅ menu (ចេញតែ 0/q)
"""

from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

from . import __version__
from .crypto import CryptoError
from .generator import RESERVED_DOMAINS as DOMAINS, generate as generate_names, is_valid_email as valid_email
from .store import Account, StoreError, Vault
from .totp import code_at, normalize_secret, remaining_seconds
from .cli import BOLD, CYAN, DIM, GREEN, RED, YELLOW, _pad as pad, c

HELP_TEXT = f"""\
{c('Teta ' + __version__ + ' — ជំនួយរហ័ស', BOLD)}
  បញ្ជាក្នុង menu (អក្សរកាត់ក៏បាន)៖
    1 / a   បន្ថែមគណនី Gmail        add
    2 / l   បញ្ជីគណនី               list
    3 / c   កូដ 2FA ឥឡូវ            code
    4 / w   កូដ 2FA ចល័ត (live)      code --watch
    5 / i   ព័ត៌មានគណនី           show
    6 / g   បង្កើតឈ្មោះ Gmail ថ្មី    gen
    7 / s   ស្វែងរក / តម្រង tag        search
    8 / r   លុបគណនី                rm
    9 / b   backup vault            backup
   10 / p   ប្តូរលេខសម្ងាត់មេ         passwd
   11 / t   ដំឡើង command `teta`     install
    d       ពិនិត្យបរិស្ថាន          doctor
    ?       ជំនួយនេះ
    0 / q   ចាកចេញ

  ខាងក្រៅ menu (Termux)៖
    teta add EMAIL --totp SECRET
    teta code EMAIL --watch
    teta gen --seed sokha -n 10
    teta backup
"""

# ─────────────────────────── helpers ───────────────────────────

def is_interactive() -> bool:
    return sys.stdin.isatty() and os.environ.get("TETA_NO_CLEAR") is None


def clear() -> None:
    if is_interactive() and os.environ.get("TERM") != "dumb":
        sys.stdout.write("\033[H\033[2J")
        sys.stdout.flush()


def ask(prompt: str, default: str = "") -> str:
    try:
        answer = input(f"  {prompt}{f' [{default}]' if default else ''} › ").strip()
    except EOFError:
        print()
        raise SystemExit(0)
    return answer or default


def pause() -> None:
    if os.environ.get("TETA_NO_PAUSE"):
        return
    try:
        input(c("  ↵ Enter ដើម្បីបន្ត", DIM))
    except (EOFError, KeyboardInterrupt):
        print()


def note(message: str) -> None:
    print(c("  " + message, DIM))


def error(message: str) -> None:
    print(c("  ✖ ", RED) + message)


def success(message: str) -> None:
    print(c("  ✔ ", GREEN) + message)


# ─────────────────────────── session ───────────────────────────

class Session:
    """រក្សា vault ដែលបើករួច ដើម្បីមិនសួរលេខសម្ងាត់រាល់ដង។"""

    def __init__(self, home: str | None = None) -> None:
        self.vault = Vault(home)
        self.unlocked = False

    @property
    def ready(self) -> bool:
        return self.vault.exists()

    def unlock(self, force: bool = False) -> bool:
        if self.unlocked and not force:
            return True
        if not self.ready:
            error("មិនទាន់មាន vault — ជ្រើស [1] ដើម្បីបង្កើត")
            return False
        password = os.environ.get("TETA_PASSWORD")
        if not password:
            import getpass
            try:
                password = getpass.getpass("  លេខសម្ងាត់មេ › ")
            except (EOFError, KeyboardInterrupt):
                print()
                return False
        try:
            self.vault.unlock(password)
        except (StoreError, CryptoError) as exc:
            error(str(exc))
            return False
        self.unlocked = True
        return True

    def relock(self) -> None:
        self.vault = Vault(self.vault.base)
        self.unlocked = False

    @property
    def accounts(self) -> "list[Account]":
        return self.vault.accounts if self.unlocked else []


# ─────────────────────────── views ───────────────────────────

def header(session: Session) -> None:
    if session.ready:
        if session.unlocked:
            state = c(f"● បើករួច ({len(session.accounts)} គណនី)", GREEN)
        else:
            state = c("○ ចាក់សោ", YELLOW)
    else:
        state = c("○ មិនទាន់មាន vault", YELLOW)
    print()
    print(c(f"  TETA v{__version__}  ·  Gmail Vault + 2FA", BOLD))
    print(c("  " + "─" * 52, DIM))
    print(f"  {state}   {c(str(session.vault.path), DIM)}")
    print(c("  " + "─" * 52, DIM))


def main_menu(session: Session) -> None:
    print("  " + c("[1]", CYAN) + " បន្ថែមគណនី          " + c("[6]", CYAN) + " បង្កើតឈ្មោះ Gmail")
    print("  " + c("[2]", CYAN) + " បញ្ជីគណនី           " + c("[7]", CYAN) + " ស្វែងរក / tag")
    print("  " + c("[3]", CYAN) + " កូដ 2FA ឥឡូវ         " + c("[8]", CYAN) + " លុបគណនី")
    print("  " + c("[4]", CYAN) + " កូដ 2FA ចល័ត       " + c("[9]", CYAN) + " backup vault")
    print("  " + c("[5]", CYAN) + " ព័ត៌មានគណនី        " + c("[10]", CYAN) + " ប្តូរលេខសម្ងាត់មេ")
    print("  " + c("[11]", CYAN) + " ដំឡើង `teta`        " + c("[d]", CYAN) + " doctor   " + c("[?]", CYAN) + " ជំនួយ")
    print("  " + c("[0]", CYAN) + " ចាកចេញ")
    print(c("  " + "─" * 52, DIM))


def table(accounts: "list[Account]") -> None:
    print("  " + c(pad("#", 4) + pad("EMAIL", 34) + pad("LABEL", 18) + pad("2FA", 5) + "TAGS", BOLD))
    for index, acc in enumerate(accounts, start=1):
        mark = "✔" if acc.totp_secret else "-"
        print("  " + pad(index, 4) + pad(acc.email, 34) + pad(acc.label or "-", 18)
              + pad(mark, 5) + ",".join(acc.tags))
    print(c(f"\n  សរុប {len(accounts)} គណនី", DIM))


def pick_account(session: Session, title: str = "ជ្រើសគណនី") -> "Account | None":
    accounts = session.accounts
    if not accounts:
        error("គ្មានគណនី — បន្ថែមដោយ [1] សិន")
        return None
    table(accounts)
    choice = ask(f"{title} (លេខ ឬអ៊ីមែល, Enter=បោះបង់)")
    if not choice:
        return None
    if choice.isdigit():
        index = int(choice)
        if 1 <= index <= len(accounts):
            return accounts[index - 1]
        error("លេខមិនត្រឹមត្រូវ")
        return None
    found = session.vault.find(choice)
    if not found:
        error(f"រកមិនឃើញ {choice}")
    return found


# ─────────────────────────── actions ───────────────────────────

def act_init(session: Session) -> None:
    import getpass
    vault = session.vault
    if vault.exists():
        error("vault មានរួចហើយ")
        return
    note("ចងចាំលេខសម្ងាត់មេឱ្យបាន — បើបាត់ ទិន្នន័យយកមកវិញមិនបានទេ")
    password = os.environ.get("TETA_PASSWORD") or getpass.getpass("  លេខសម្ងាត់មេថ្មី › ")
    if not os.environ.get("TETA_PASSWORD"):
        again = getpass.getpass("  វាយម្តងទៀត › ")
        if again != password:
            error("លេខសម្ងាត់មិនដូចគ្នា")
            return
    try:
        vault.init(password)
    except StoreError as exc:
        error(str(exc))
        return
    session.unlocked = True
    success(f"បង្កើត vault → {vault.path}")


def act_add(session: Session) -> None:
    if not session.unlock():
        return
    email = ask("អ៊ីមែល Gmail").lower()
    if not valid_email(email):
        error("អ៊ីមែលមិនត្រឹមត្រូវ (ឧ. sokha.chan@gmail.com)")
        return
    label = ask("label (ស្រេចចិត្ត)")
    tags = [t.strip() for t in ask("tags ដោយប្រើ , (ស្រេចចិត្ត)").split(",") if t.strip()]
    secret = normalize_secret(ask("2FA secret (ស្រេចចិត្ត)"))
    note_text = ask("ចំណាំ (ស្រេចចិត្ត)")
    if secret:
        try:
            code_at(secret)
        except ValueError as exc:
            error(str(exc))
            return
    try:
        session.vault.add(Account(email=email, label=label, tags=tags,
                                 totp_secret=secret, note=note_text))
    except StoreError as exc:
        error(str(exc))
        return
    success(f"បន្ថែម {email}")
    if secret:
        print(f"  កូដ 2FA ឥឡូវ: {c(code_at(secret), BOLD + CYAN)}")


def act_list(session: Session) -> None:
    if not session.unlock():
        return
    if not session.accounts:
        note("(ទំនេរ) — បន្ថែមគណនីដោយ [1]")
        return
    table(session.accounts)


def act_code(session: Session) -> None:
    if not session.unlock():
        return
    acc = pick_account(session, "យកកូដ 2FA របស់")
    if not acc:
        return
    if not acc.totp_secret:
        error(f"{acc.email} គ្មាន 2FA secret — បន្ថែមពេល [1] ឬ `teta set-totp`")
        return
    print(f"\n  {c(acc.email, BOLD)}")
    print(f"  កូដ: {c(code_at(acc.totp_secret), BOLD + CYAN)}"
          f"   {c(f'(នៅសល់ {remaining_seconds()}s)', DIM)}")


def act_watch(session: Session) -> None:
    if not session.unlock():
        return
    acc = pick_account(session, "បង្ហាញកូដចល័តរបស់")
    if not acc or not acc.totp_secret:
        if acc:
            error("គណនីនេះគ្មាន 2FA secret")
        return
    print(c("\n  ចុច Ctrl+C ដើម្បីឈប់\n", DIM))
    try:
        while True:
            left = remaining_seconds()
            bar = "█" * (left // 2) + "░" * (15 - left // 2)
            print(f"\r  {c(acc.email, DIM)}  {c(code_at(acc.totp_secret), BOLD + CYAN)}"
                  f"  {bar} {left:>2}s ", end="", flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        print()


def act_show(session: Session) -> None:
    if not session.unlock():
        return
    acc = pick_account(session, "ព័ត៌មានគណនី")
    if not acc:
        return
    reveal = ask("បង្ហាញ 2FA key ពេញ? (y/N)").lower().startswith("y")
    print()
    print("  " + c(acc.email, BOLD))
    print(f"  label   : {acc.label or '-'}")
    print(f"  tags    : {', '.join(acc.tags) or '-'}")
    print(f"  note    : {acc.note or '-'}")
    print(f"  created : {time.strftime('%Y-%m-%d %H:%M', time.localtime(acc.created_at))}")
    if acc.totp_secret:
        shown = acc.totp_secret if reveal else acc.totp_secret[:4] + "•" * max(0, len(acc.totp_secret) - 4)
        print(f"  2FA key : {shown}")
        print(f"  2FA code: {c(code_at(acc.totp_secret), CYAN)} ({remaining_seconds()}s)")
    else:
        print("  2FA key : -")
    new_label = ask("label ថ្មី (Enter=រក្សា)")
    new_tags = ask("tags ថ្មី (Enter=រក្សា)")
    new_note = ask("ចំណាំថ្មី (Enter=រក្សា)")
    if new_label or new_tags or new_note:
        acc.label = new_label or acc.label
        if new_tags:
            acc.tags = [t.strip() for t in new_tags.split(",") if t.strip()]
        acc.note = new_note or acc.note
        acc.updated_at = time.time()
        session.vault.update(acc)
        success("បានធ្វើបច្ចុប្បន្នភាព")


def act_gen(_: Session) -> None:
    seed = ask("ពាក្យគន្លឹះ/ឈ្មោះ (ស្រេចចិត្ត)")
    count_text = ask("ចំនួន", "10")
    count = int(count_text) if count_text.isdigit() else 10
    domain = ask("domain", "gmail.com")
    try:
        names = generate_names(count, seed, domain if domain in DOMAINS else "gmail.com")
    except ValueError as exc:
        error(str(exc))
        return
    for name in names:
        print("  " + c(name, CYAN))
    note("ទាំងនេះជាឈ្មោះ 'បេក្ខជន' — ផ្ទៀងផ្ទាត់ថាទំនេរនៅ accounts.google.com/signup ដោយខ្លួនឯង")


def act_search(session: Session) -> None:
    if not session.unlock():
        return
    query = ask("ពាក្យស្វែងរក (អ៊ីមែល/label/tag)").lower()
    if not query:
        return
    hits = [a for a in session.accounts
            if query in a.email.lower() or query in a.label.lower()
            or any(query in t.lower() for t in a.tags)]
    if not hits:
        note("រកមិនឃើញ")
        return
    table(hits)


def act_rm(session: Session) -> None:
    if not session.unlock():
        return
    acc = pick_account(session, "លុបគណនី")
    if not acc:
        return
    if not ask(f"លុប {acc.email} ចេញ? (y/N)").lower().startswith("y"):
        note("បោះបង់")
        return
    session.vault.remove(acc.email)
    success("លុបរួចរាល់")


def act_backup(session: Session) -> None:
    if not session.unlock():
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = session.vault.base / "backups" / f"teta-vault-{stamp}.json"
    try:
        session.vault.backup_to(target)
    except OSError as exc:
        error(str(exc))
        return
    success(f"backup → {target}")
    note("ឯកសារនៅអ៊ិនគ្រីប — ត្រូវការលេខសម្ងាត់មេដើម្បីបើក")


def act_passwd(session: Session) -> None:
    import getpass
    if not session.unlock():
        return
    new = os.environ.get("TETA_PASSWORD") or getpass.getpass("  លេខសម្ងាត់មេថ្មី › ")
    if not os.environ.get("TETA_PASSWORD") and getpass.getpass("  វាយម្តងទៀត › ") != new:
        error("លេខសម្ងាត់មិនដូចគ្នា")
        return
    session.vault.change_password(new)
    success("ផ្លាស់ប្តូរលេខសម្ងាត់រួចរាល់")


def act_doctor(session: Session) -> None:
    print(c("  ការពិនិត្យបរិស្ថាន", BOLD))
    checks = [
        ("python ≥ 3.8", sys.version_info >= (3, 8), sys.version.split()[0]),
        ("scrypt", hasattr(__import__("hashlib"), "scrypt"), "ok"),
        ("HOME អាចសរសេរ", os.access(Path.home(), os.W_OK), str(Path.home())),
    ]
    for name, good, detail in checks:
        print(f"  {'✔' if good else '✖'} {pad(name, 20)}{c(detail, DIM)}")
    print(f"  {'✔' if session.ready else '•'} {pad('vault', 20)}{c(str(session.vault.path), DIM)}")
    if session.ready:
        mode = oct(session.vault.path.stat().st_mode & 0o777)
        print(f"  {'✔' if mode == '0o600' else '⚠'} {pad('សិទ្ធិ', 20)}{c(mode, DIM)}")
    found = shutil.which("teta")
    print(f"  {'✔' if found else '•'} {pad('command teta', 20)}{c(found or 'មិនទាន់ដំឡើង (ជ្រើស [11])', DIM)}")


def act_install(_: Session) -> None:
    prefix = os.environ.get("PREFIX") or str(Path.home() / ".local")
    bin_dir = Path(prefix) / "bin"
    entry = Path(__file__).resolve().parent.parent / "teta.sh"
    try:
        bin_dir.mkdir(parents=True, exist_ok=True)
        wrapper = bin_dir / "teta"
        if entry.exists():
            wrapper.write_text(f'#!/bin/sh\nexec sh "{entry}" "$@"\n', encoding="utf-8")
        else:
            wrapper.write_text(
                f'#!/bin/sh\nPYTHONPATH="{Path(__file__).resolve().parent.parent}" '
                f'exec {sys.executable} -m teta "$@"\n', encoding="utf-8")
        os.chmod(wrapper, 0o755)
    except OSError as exc:
        error(f"សរសេរមិនបាន: {exc}")
        return
    success(f"បង្កើត {wrapper}")
    if str(bin_dir) not in os.environ.get("PATH", "").split(":"):
        note(f"បន្ថែម PATH: export PATH=\"{bin_dir}:$PATH\"")
    note("សាកល្បង: hash -r && teta --version")


def act_help(_: Session) -> None:
    print()
    print(HELP_TEXT)


ACTIONS = {
    "1": act_add, "a": act_add,
    "2": act_list, "l": act_list,
    "3": act_code, "c": act_code,
    "4": act_watch, "w": act_watch,
    "5": act_show, "i": act_show,
    "6": act_gen, "g": act_gen,
    "7": act_search, "s": act_search,
    "8": act_rm, "r": act_rm,
    "9": act_backup, "b": act_backup,
    "10": act_passwd, "p": act_passwd,
    "11": act_install, "t": act_install,
    "d": act_doctor,
    "?": act_help, "h": act_help,
}


def menu(home: str | None = None) -> int:
    """បើក menu អន្តរកម្មរហូតដល់អ្នកប្រើចេញ។"""
    session = Session(home)
    first = True
    while True:
        if not first:
            clear()
        first = False
        header(session)
        main_menu(session)
        try:
            choice = input(c("  ជ្រើសលេខ › ", CYAN)).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  លាហើយ 👋")
            return 0
        if choice in ("0", "q", "quit", "exit"):
            print("  លាហើយ 👋")
            return 0
        if choice == "":
            choice = "1" if not session.ready else "2"
        if choice in ("n", "new"):
            clear()
            header(session)
            act_init(session)
            pause()
            continue
        action = ACTIONS.get(choice)
        if not action:
            error("មិនស្គាល់ជម្រើស — វាយ [?] សម្រាប់ជំនួយ")
            time.sleep(0.6)
            continue
        clear()
        if not is_interactive():
            header(session)
        try:
            action(session)
        except (StoreError, CryptoError) as exc:
            error(str(exc))
        except KeyboardInterrupt:
            print()
            note("បោះបង់")
        if choice not in ("4", "w"):     # watch mode គ្រប់គ្រងខ្លួនឯង
            pause()
