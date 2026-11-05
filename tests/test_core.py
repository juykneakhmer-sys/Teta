import json
import tempfile
import unittest
from pathlib import Path

from teta import crypto, totp
from teta.generator import generate, is_valid_email, normalize_localpart
from teta.store import Account, StoreError, Vault


class CryptoTest(unittest.TestCase):
    def test_roundtrip(self):
        blob = crypto.encrypt("pw-123456", b"hello world" * 10)
        self.assertEqual(crypto.decrypt("pw-123456", blob), b"hello world" * 10)

    def test_wrong_password(self):
        blob = crypto.encrypt("right-pass", b"secret data")
        with self.assertRaises(crypto.CryptoError):
            crypto.decrypt("wrong-pass", blob)

    def test_tamper_detected(self):
        blob = json.loads(crypto.encrypt("pw-123456", b"abc"))
        raw = bytearray(crypto._b64d(blob["ciphertext"]))
        raw[0] ^= 0xFF
        blob["ciphertext"] = crypto._b64e(bytes(raw))
        with self.assertRaises(crypto.CryptoError):
            crypto.decrypt("pw-123456", json.dumps(blob))

    def test_unicode_payload(self):
        blob = crypto.encrypt("pw-123456", "ជំរាបសួរ 🇰🇭".encode())
        self.assertEqual(crypto.decrypt("pw-123456", blob).decode(), "ជំរាបសួរ 🇰🇭")


class TotpTest(unittest.TestCase):
    def test_rfc6238_vector(self):
        # RFC 6238 test key "12345678901234567890" → SHA1, T=59
        secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
        self.assertEqual(totp.code_at(secret, timestamp=59), "287082")

    def test_otpauth_uri(self):
        uri = "otpauth://totp/me%40gmail.com?secret=JBSWY3DPEHPK3PXP&issuer=x"
        self.assertEqual(totp.normalize_secret(uri), "JBSWY3DPEHPK3PXP")
        self.assertRegex(totp.code_at(uri), r"^\d{6}$")

    def test_remaining(self):
        self.assertTrue(1 <= totp.remaining_seconds() <= 30)

    def test_bad_secret(self):
        with self.assertRaises(ValueError):
            totp.code_at("not base32 !!")


class VaultTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "vault"
        self.vault = Vault(self.home)
        self.vault.init("master-123")

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_persist_reload(self):
        self.vault.add(Account(email="a@gmail.com", label="main", tags=["work"],
                               totp_secret="JBSWY3DPEHPK3PXP"))
        again = Vault(self.home)
        again.unlock("master-123")
        acc = again.find("A@GMAIL.COM")
        self.assertIsNotNone(acc)
        self.assertEqual(acc.label, "main")
        self.assertEqual(acc.tags, ["work"])

    def test_duplicate_rejected(self):
        self.vault.add(Account(email="a@gmail.com"))
        with self.assertRaises(StoreError):
            self.vault.add(Account(email="a@gmail.com"))

    def test_wrong_password_rejected(self):
        with self.assertRaises(StoreError):
            Vault(self.home).unlock("nope")

    def test_remove_and_change_password(self):
        self.vault.add(Account(email="a@gmail.com"))
        self.assertTrue(self.vault.remove("a@gmail.com"))
        self.assertFalse(self.vault.remove("a@gmail.com"))
        self.vault.change_password("new-master")
        v2 = Vault(self.home)
        v2.unlock("new-master")
        self.assertEqual(v2.accounts, [])

    def test_plaintext_not_on_disk(self):
        self.vault.add(Account(email="hidden@gmail.com", note="super secret note"))
        text = (self.home / "vault.json").read_text()
        self.assertNotIn("hidden@gmail.com", text)
        self.assertNotIn("super secret note", text)

    def test_file_permissions(self):
        mode = (self.home / "vault.json").stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)


class GeneratorTest(unittest.TestCase):
    def test_generates_valid_unique(self):
        names = generate(30, "sokha", "gmail.com", 8, 24)
        self.assertEqual(len(names), len(set(names)))
        for name in names:
            self.assertTrue(is_valid_email(name), name)

    def test_normalize(self):
        self.assertEqual(normalize_localpart("  Sokha!! Chan.. "), "sokhachan")
        self.assertEqual(normalize_localpart(".Sokha..Chan."), "sokha.chan")

    def test_bad_domain(self):
        with self.assertRaises(ValueError):
            generate(3, domain="yahoo.com")

    def test_seed_reproducible(self):
        self.assertEqual(generate(5, "dara"), generate(5, "dara"))


if __name__ == "__main__":
    unittest.main()
