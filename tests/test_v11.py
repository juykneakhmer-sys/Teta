"""ការសាកល្បងសម្រាប់មុខងារថ្មី v1.1: គណនីហ្គេម, edit, copy, export, audit, genpass។"""

import csv
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from teta import audit, passgen
from teta.cli import main
from teta.store import Account, Vault


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = str(Path(self.tmp.name) / "v")
        self._old = os.environ.get("TETA_PASSWORD")
        os.environ["TETA_PASSWORD"] = "master-123"

    def tearDown(self):
        if self._old is None:
            os.environ.pop("TETA_PASSWORD", None)
        else:
            os.environ["TETA_PASSWORD"] = self._old
        self.tmp.cleanup()

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--home", self.home, *argv])
        return code, out.getvalue(), err.getvalue()


class GameAccountTest(Base):
    def test_moonton_account_roundtrip(self):
        self.assertEqual(self.run_cli("init")[0], 0)
        code, _, _ = self.run_cli("add", "654321987", "--kind", "moonton",
                                  "--user", "654321987", "--zone", "2001",
                                  "--pass", "Str0ng-Pass!", "--label", "smurf")
        self.assertEqual(code, 0)

        code, out, _ = self.run_cli("show", "654321987", "--reveal")
        self.assertIn("Str0ng-Pass!", out)
        self.assertIn("2001", out)

        # មិនបង្ហាញ password បើគ្មាន --reveal
        code, out, _ = self.run_cli("show", "654321987")
        self.assertNotIn("Str0ng-Pass!", out)

    def test_resolve_by_username_and_label(self):
        self.run_cli("init")
        self.run_cli("add", "sokha.chan@gmail.com", "--label", "main")
        self.run_cli("add", "888888", "--kind", "game", "--user", "ign.kh")
        vault = Vault(self.home)
        vault.unlock("master-123")
        self.assertEqual(vault.resolve("sokha.chan@gmail.com").email, "sokha.chan@gmail.com")
        self.assertEqual(vault.resolve("main").email, "sokha.chan@gmail.com")
        self.assertEqual(vault.resolve("ign.kh").username, "ign.kh")

    def test_password_from_stdin_marker(self):
        self.run_cli("init")
        home = self.home
        env_home = Path(home)
        self.assertTrue(env_home.exists() or True)
        # '-' + stdin មិនមែន tty → អានបន្ទាត់
        import sys

        class FakeStdin:
            def isatty(self):
                return False

            def readline(self):
                return "from-stdin-999\n"

        old_stdin = sys.stdin
        sys.stdin = FakeStdin()
        try:
            code, _, _ = self.run_cli("add", "777777", "--kind", "game",
                                      "--pass", "-")
        finally:
            sys.stdin = old_stdin
        self.assertEqual(code, 0)
        vault = Vault(self.home)
        vault.unlock("master-123")
        self.assertEqual(vault.resolve("777777").password, "from-stdin-999")

    def test_duplicate_username_same_kind_rejected(self):
        self.run_cli("init")
        self.run_cli("add", "111", "--kind", "game")
        code, _, err = self.run_cli("add", "111", "--kind", "game")
        self.assertEqual(code, 1)


class EditTest(Base):
    def test_edit_fields(self):
        self.run_cli("init")
        self.run_cli("add", "dara.sok@gmail.com", "--label", "old")
        code, out, _ = self.run_cli("edit", "dara.sok@gmail.com", "--label", "new",
                                    "--tags", "main,work", "--note", "hi")
        self.assertEqual(code, 0)
        code, out, _ = self.run_cli("show", "dara.sok@gmail.com")
        self.assertIn("new", out)
        self.assertIn("main", out)
        self.assertIn("work", out)
        self.assertIn("hi", out)

    def test_edit_without_changes_errors(self):
        self.run_cli("init")
        self.run_cli("add", "dara.sok@gmail.com")
        code, _, err = self.run_cli("edit", "dara.sok@gmail.com")
        self.assertEqual(code, 1)

    def test_edit_email_validation(self):
        self.run_cli("init")
        self.run_cli("add", "dara.sok@gmail.com")
        code, _, _ = self.run_cli("edit", "dara.sok@gmail.com", "--email-new", "bad@@x")
        self.assertEqual(code, 1)

    def test_edit_password(self):
        self.run_cli("init")
        self.run_cli("add", "dara.sok@gmail.com", "--pass", "old-password-123")
        self.run_cli("edit", "dara.sok@gmail.com", "--pass", "new-password-456")
        vault = Vault(self.home)
        vault.unlock("master-123")
        self.assertEqual(vault.resolve("dara.sok@gmail.com").password, "new-password-456")


class CopyExportTest(Base):
    def test_copy_falls_back_to_stdout(self):
        self.run_cli("init")
        self.run_cli("add", "dara.sok@gmail.com", "--pass", "sekret-123")
        code, out, _ = self.run_cli("copy", "dara.sok@gmail.com", "-f", "password")
        self.assertEqual(code, 0)
        self.assertIn("sekret-123", out)

    def test_copy_totp(self):
        self.run_cli("init")
        self.run_cli("add", "dara.sok@gmail.com", "--totp", "JBSWY3DPEHPK3PXP")
        code, out, _ = self.run_cli("copy", "dara.sok@gmail.com", "-f", "totp")
        self.assertEqual(code, 0)
        self.assertRegex(out.strip(), r"^\d{6}$")

    def test_copy_missing_field(self):
        self.run_cli("init")
        self.run_cli("add", "dara.sok@gmail.com")
        code, _, _ = self.run_cli("copy", "dara.sok@gmail.com", "-f", "password")
        self.assertEqual(code, 1)

    def test_export_csv_to_stdout(self):
        self.run_cli("init")
        self.run_cli("add", "dara.sok@gmail.com", "--pass", "pw-123456")
        self.run_cli("add", "999", "--kind", "game")
        code, out, _ = self.run_cli("export", "--format", "csv", "-o", "-", "--yes")
        self.assertEqual(code, 0)
        rows = list(csv.DictReader(io.StringIO(out)))
        self.assertEqual(len(rows), 2)
        self.assertIn("password", rows[0])
        self.assertTrue(any(r["kind"] == "game" for r in rows))

    def test_export_file_permissions(self):
        self.run_cli("init")
        self.run_cli("add", "dara.sok@gmail.com", "--pass", "pw-123456")
        target = Path(self.tmp.name) / "out" / "accounts.csv"
        code, _, _ = self.run_cli("export", "-o", str(target), "--yes")
        self.assertEqual(code, 0)
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_export_requires_confirmation_when_interactive(self):
        self.run_cli("init")
        target = Path(self.tmp.name) / "x.csv"
        # stdin មិនមែន tty → input() បរាជ័យ → បោះបង់ (exit 1)
        code, _, _ = self.run_cli("export", "-o", str(target))
        self.assertEqual(code, 1)
        self.assertFalse(target.exists())

    def test_export_kind_filter(self):
        self.run_cli("init")
        self.run_cli("add", "dara.sok@gmail.com")
        self.run_cli("add", "555", "--kind", "game")
        code, out, _ = self.run_cli("export", "--format", "json", "--kind", "game",
                                    "-o", "-", "--yes")
        data = json.loads(out)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["kind"], "game")


class AuditTest(Base):
    def test_weak_and_reused_passwords_flagged(self):
        self.run_cli("init")
        self.assertEqual(self.run_cli("add", "dara.sok@gmail.com",
                                      "--pass", "password")[0], 0)
        self.assertEqual(self.run_cli("add", "bopha.kh@gmail.com",
                                      "--pass", "password")[0], 0)
        code, out, _ = self.run_cli("audit")
        self.assertEqual(code, 0)
        self.assertIn("ខ្សោយ", out)
        self.assertIn("ដដែល", out)

    def test_clean_vault_scores_high(self):
        self.run_cli("init")
        self.run_cli("add", "dara.sok@gmail.com", "--pass", "Xk9$mQ2vLp7#Rt4w",
                     "--totp", "JBSWY3DPEHPK3PXP")
        findings = audit.audit_accounts([Account(email="dara.sok@gmail.com",
                                                 password="Xk9$mQ2vLp7#Rt4w",
                                                 totp_secret="JBSWY3DPEHPK3PXP")])
        self.assertEqual(findings, [])
        self.assertEqual(audit.score([Account(email="dara.sok@gmail.com")], findings), 100)

    def test_audit_json(self):
        self.run_cli("init")
        code, out, _ = self.run_cli("audit", "--json")
        data = json.loads(out)
        self.assertIn("score", data)
        self.assertEqual(data["findings"], [])

    def test_stale_account_info(self):
        old = Account(email="old.teta@gmail.com", totp_secret="JBSWY3DPEHPK3PXP",
                      password="Xk9$mQ2vLp7#Rt4w")
        old.updated_at = 0
        findings = audit.audit_accounts([old])
        self.assertTrue(any(f.level == audit.INFO for f in findings))


class GenPassTest(Base):
    def test_length_and_charset(self):
        code, out, _ = self.run_cli("genpass", "-L", "24")
        self.assertEqual(code, 0)
        pw = out.strip()
        self.assertEqual(len(pw), 24)
        self.assertTrue(any(ch.islower() for ch in pw))
        self.assertTrue(any(ch.isupper() for ch in pw))
        self.assertTrue(any(ch.isdigit() for ch in pw))
        self.assertTrue(any(not ch.isalnum() for ch in pw))

    def test_no_symbols(self):
        code, out, _ = self.run_cli("genpass", "--no-symbols", "--no-digits",
                                    "--no-upper")
        self.assertEqual(code, 0)
        self.assertTrue(out.strip().islower())

    def test_passphrase(self):
        code, out, _ = self.run_cli("genpass", "--phrase", "--words", "5")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip().count("-"), 5)

    def test_json_output(self):
        code, out, _ = self.run_cli("genpass", "--json")
        data = json.loads(out)
        self.assertIn("entropy_bits", data)
        self.assertIn(data["strength"], ("ខ្សោយ", "មធ្យម", "ល្អ", "ខ្លាំង"))

    def test_too_short_rejected(self):
        code, _, _ = self.run_cli("genpass", "-L", "4")
        self.assertEqual(code, 1)

    def test_uniqueness(self):
        samples = {passgen.generate_password(20) for _ in range(50)}
        self.assertEqual(len(samples), 50)


class MigrationTest(Base):
    def test_v1_vault_still_opens(self):
        """Vault schema 1 (គ្មាន kind/username) ត្រូវតែបើកបានដូចដើម។"""
        from teta import crypto

        base = Path(self.home)
        base.mkdir(parents=True)
        payload = {"schema": 1, "updated_at": 0,
                   "accounts": [{"email": "old.teta@gmail.com", "label": "legacy",
                                 "tags": ["a"], "totp_secret": "", "note": "",
                                 "created_at": 1.0, "updated_at": 1.0}]}
        blob = crypto.encrypt("master-123",
                              json.dumps(payload).encode("utf-8"))
        (base / "vault.json").write_text(blob)

        vault = Vault(self.home)
        vault.unlock("master-123")
        acc = vault.resolve("old.teta@gmail.com")
        self.assertIsNotNone(acc)
        self.assertEqual(acc.kind, "gmail")     # default ត្រូវបានបំពេញ

        # សរសេរឡើងវិញ → schema 2
        vault.save()
        self.assertEqual(json.loads(crypto.decrypt(
            "master-123", (base / "vault.json").read_text()))["schema"], 2)


if __name__ == "__main__":
    unittest.main()
