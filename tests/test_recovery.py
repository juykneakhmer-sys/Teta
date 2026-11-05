"""តេស្តជំនួយការស្តារគណនី (recovery)."""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from teta import recovery
from teta.store import Account, Vault


class RecoveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "v"

    def tearDown(self):
        self.tmp.cleanup()

    def test_mask_hint_email(self):
        masked = recovery.mask_hint("poeung.old@gmail.com")
        self.assertIn("@gmail.com", masked)
        self.assertIn("*", masked)
        self.assertNotIn("poeung.old", masked)

    def test_mask_hint_short_and_empty(self):
        self.assertEqual(recovery.mask_hint(""), "")
        self.assertEqual(recovery.mask_hint("1234"), "1***")

    def test_guide_contains_official_links_only(self):
        acc = Account(email="poeungpitou18@gmail.com")
        text = recovery.recovery_guide(acc)
        self.assertIn(recovery.RECOVERY_URL, text)
        self.assertIn("poeungpitou18@gmail.com", text)
        self.assertIn("ចំណាំសុវត្ថិភាព", text)
        # ត្រូវបញ្ជាក់ថាមិនចាប់យកសារ
        self.assertIn("មិនអាច", text)

    def test_plan_uses_vault_hints(self):
        acc = Account(email="a1@gmail.com", note="old.backup@gmail.com",
                      tags=["work", "family"])
        rows = dict(recovery.build_plan(acc))
        hint = [v for k, v in rows.items() if "recovery" in k][0]
        self.assertNotIn("old.backup@gmail.com", hint)   # បិទបាំង
        self.assertEqual(rows["ឈ្មោះអ្នកទំនាក់ទំនងញឹកញាប់ (label ឬឈ្មោះក្នុង Gmail)"], "work, family")

    def test_status_counts(self):
        acc = Account(email="a1@gmail.com", note="x@gmail.com", tags=["w"])
        info = recovery.status(acc)
        self.assertEqual(info["total_items"], len(recovery.CHECKLIST))
        self.assertGreaterEqual(info["ready_items"], 3)
        self.assertTrue(info["has_note"])

    def test_save_guide_permissions(self):
        acc = Account(email="a1@gmail.com")
        target = recovery.save_guide(acc, Path(self.tmp.name) / "out")
        self.assertTrue(target.exists())
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertIn("a1_at_gmail.com", target.name)

    def test_invalid_email(self):
        vault = Vault(self.home)
        with self.assertRaises(recovery.RecoveryError):
            recovery.find_account(vault, "not-an-email")


class RecoverCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = str(Path(self.tmp.name) / "v")
        self.env = mock.patch.dict(os.environ, {"TETA_PASSWORD": "master-123"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def run_cli(self, *argv):
        from teta.cli import main
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--home", self.home, *argv])
        return code, out.getvalue(), err.getvalue()

    def test_offline_recover(self):
        code, out, _ = self.run_cli("recover", "poeungpitou18@gmail.com", "--offline",
                                    "--hint", "poeung.old@gmail.com")
        self.assertEqual(code, 0)
        self.assertIn("ផែនការស្តារគណនី", out)
        self.assertNotIn("poeung.old@gmail.com", out.split("ជំហាន ២")[1].split("ជំហាន ៣")[0])

    def test_recover_json_and_save(self):
        code, out, _ = self.run_cli("recover", "poeungpitou18@gmail.com", "--offline", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["email"], "poeungpitou18@gmail.com")

        code, out, _ = self.run_cli("recover", "poeungpitou18@gmail.com", "--offline", "--save")
        self.assertEqual(code, 0)
        files = list((Path(self.home) / "recovery").glob("recovery-*.txt"))
        self.assertEqual(len(files), 1)

    def test_recover_uses_vault_entry(self):
        self.run_cli("init")
        self.run_cli("add", "poeungpitou18@gmail.com", "--label", "ចាស់",
                     "--note", "backup.poeung@gmail.com")
        code, out, _ = self.run_cli("recover", "poeungpitou18@gmail.com")
        self.assertEqual(code, 0)
        self.assertIn("ប្រើព័ត៌មានដែលរក្សាទុក", out)
        self.assertIn("ចាស់", out)

    def test_recover_list(self):
        self.run_cli("init")
        self.run_cli("add", "poeungpitou18@gmail.com", "--tags", "work")
        code, out, _ = self.run_cli("recover-list")
        self.assertEqual(code, 0)
        self.assertIn("poeungpitou18@gmail.com", out)
        self.assertIn("/7", out)

    def test_bad_email(self):
        code, _, err = self.run_cli("recover", "nope", "--offline")
        self.assertEqual(code, 1)
        self.assertIn("មិនត្រឹមត្រូវ", err)


if __name__ == "__main__":
    unittest.main()
