"""តេស្ត menu អន្តរកម្ម (បញ្ចូលចម្លើយជាមុន តាមលំដាប់)។

ចំណាំ៖ ក្នុង menu — `n` = បង្កើត vault, `1` = បន្ថែមគណនី, `2` = បញ្ជី, ...
"""

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from teta import menu as menu_mod


class MenuTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = str(Path(self.tmp.name) / "v")
        self.env = mock.patch.dict(os.environ, {
            "TETA_PASSWORD": "master-123",
            "TETA_NO_CLEAR": "1",
            "TETA_NO_PAUSE": "1",
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def run_menu(self, keys):
        out = io.StringIO()
        with mock.patch("builtins.input", side_effect=keys), redirect_stdout(out):
            code = menu_mod.menu(self.home)
        return code, out.getvalue()

    def test_init_then_list_then_quit(self):
        code, out = self.run_menu(["n", "2", "q"])
        self.assertEqual(code, 0)
        self.assertIn("បង្កើត vault", out)
        self.assertIn("(ទំនេរ)", out)
        self.assertTrue((Path(self.home) / "vault.json").exists())

    def test_full_flow_add_code_search(self):
        code, out = self.run_menu([
            "n",                                    # init
            "1", "sokha.chan@gmail.com", "main", "work", "JBSWY3DPEHPK3PXP", "note",
            "2",                                    # list
            "3", "1",                               # code → គណនីទី ១
            "7", "sokha",                           # search
            "0",
        ])
        self.assertEqual(code, 0)
        self.assertIn("sokha.chan@gmail.com", out)
        self.assertRegex(out, r"កូដ: \d{6}")
        self.assertIn("សរុប 1 គណនី", out)

    def test_shortcut_letters(self):
        code, out = self.run_menu(["n", "a", "dara168@gmail.com", "", "", "", "", "l", "q"])
        self.assertEqual(code, 0)
        self.assertIn("dara168@gmail.com", out)

    def test_pick_by_email_and_edit(self):
        code, out = self.run_menu([
            "n",
            "1", "sokha.chan@gmail.com", "main", "", "JBSWY3DPEHPK3PXP", "",
            "5", "sokha.chan@gmail.com", "n", "edited", "", "",
            "2",
            "0",
        ])
        self.assertEqual(code, 0)
        self.assertIn("edited", out)
        self.assertIn("បានធ្វើបច្ចុប្បន្នភាព", out)

    def test_remove_and_backup(self):
        code, out = self.run_menu([
            "n",
            "1", "sokha.chan@gmail.com", "", "", "", "",
            "9",                                    # backup
            "8", "1", "y",                          # remove
            "2",                                    # list → empty
            "0",
        ])
        self.assertEqual(code, 0)
        self.assertIn("backup", out)
        backups = list((Path(self.home) / "backups").glob("teta-vault-*.json"))
        self.assertEqual(len(backups), 1)

    def test_wrong_password_message(self):
        self.run_menu(["n", "0"])
        with mock.patch.dict(os.environ, {"TETA_PASSWORD": "wrong-pass"}):
            code, out = self.run_menu(["2", "0"])
        self.assertEqual(code, 0)
        self.assertIn("មិនត្រឹមត្រូវ", out)

    def test_unknown_choice_and_help(self):
        code, out = self.run_menu(["x", "?", "0"])
        self.assertEqual(code, 0)
        self.assertIn("មិនស្គាល់ជម្រើស", out)
        self.assertIn("ជំនួយរហ័ស", out)

    def test_doctor_runs(self):
        code, out = self.run_menu(["d", "0"])
        self.assertEqual(code, 0)
        self.assertIn("ការពិនិត្យបរិស្ថាន", out)

    def test_add_without_vault_is_refused(self):
        code, out = self.run_menu(["1", "0"])
        self.assertEqual(code, 0)
        self.assertIn("មិនទាន់មាន vault", out)


if __name__ == "__main__":
    unittest.main()
