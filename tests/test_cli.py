import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

from teta.cli import main


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = str(Path(self.tmp.name) / "v")
        self.env = {"TETA_PASSWORD": "master-123"}
        self._old = {k: os.environ.get(k) for k in self.env}
        os.environ.update(self.env)

    def tearDown(self):
        for k, v in self._old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--home", self.home, *argv])
        return code, out.getvalue(), err.getvalue()

    def test_full_flow(self):
        self.assertEqual(self.run_cli("init")[0], 0)
        self.assertEqual(self.run_cli("add", "sokha@gmail.com", "--label", "main",
                                      "--totp", "JBSWY3DPEHPK3PXP")[0], 0)
        code, out, _ = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertIn("sokha@gmail.com", out)

        code, out, _ = self.run_cli("list", "--json")
        data = json.loads(out)
        self.assertTrue(data[0]["has_totp"])

        code, out, _ = self.run_cli("code", "sokha@gmail.com")
        self.assertRegex(out.strip(), r"^\d{6}$")

        code, out, _ = self.run_cli("show", "sokha@gmail.com")
        self.assertIn("2FA code", out)

        self.assertEqual(self.run_cli("rm", "sokha@gmail.com", "--yes")[0], 0)
        code, out, _ = self.run_cli("list")
        self.assertIn("ទំនេរ", out)

    def test_missing_vault(self):
        code, _, err = self.run_cli("list")
        self.assertEqual(code, 1)
        self.assertIn("init", err)

    def test_invalid_email(self):
        self.run_cli("init")
        code, _, err = self.run_cli("add", "not-an-email", "--kind", "gmail")
        self.assertEqual(code, 1)

    def test_username_account_without_email(self):
        self.run_cli("init")
        code, _, _ = self.run_cli("add", "123456789", "--kind", "moonton",
                                  "--zone", "2001")
        self.assertEqual(code, 0)
        code, out, _ = self.run_cli("list", "--json")
        data = json.loads(out)
        self.assertEqual(data[0]["kind"], "moonton")
        self.assertEqual(data[0]["server"], "2001")

    def test_gen_json(self):
        code, out, _ = self.run_cli("gen", "-n", "5", "--json")
        self.assertEqual(code, 0)
        names = json.loads(out)
        self.assertEqual(len(names), 5)
        self.assertTrue(all(n.endswith("@gmail.com") for n in names))

    def test_backup_and_restore(self):
        self.run_cli("init")
        self.run_cli("add", "xyz.abc@gmail.com")
        dest = Path(self.tmp.name) / "bk"
        self.assertEqual(self.run_cli("backup", "--out", str(dest))[0], 0)
        files = list(dest.glob("teta-vault-*.json"))
        self.assertEqual(len(files), 1)

        other = Path(self.tmp.name) / "v2"
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["--home", str(other), "restore", str(files[0])])
        self.assertEqual(code, 0)
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["--home", str(other), "search", "xyz.abc@gmail.com"])
        self.assertEqual(code, 0)
        self.assertIn("xyz.abc@gmail.com", out.getvalue())

    def test_version(self):
        with self.assertRaises(SystemExit):
            main(["--version"])


if __name__ == "__main__":
    unittest.main()
