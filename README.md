# Teta — ឧបករណ៍ Gmail សម្រាប់ Termux

ឧបករណ៍ command-line (Python សុទ្ធ, គ្មាន dependency) សម្រាប់ **គ្រប់គ្រងគណនី Gmail
របស់អ្នក** នៅលើទូរស័ព្ទ Android តាម Termux៖

| មុខងារ | បញ្ជា |
|---|---|
| ឃ្លាំងគណនីអ៊ិនគ្រីប (vault) | `teta init` / `add` / `list` / `show` / `rm` |
| បង្កើតឈ្មោះគណនីថ្មីៗ (បេក្ខជន) | `teta gen --seed sokha` |
| កូដ 2FA ៦ ខ្ទង់ offline | `teta code you@gmail.com --watch` |
| ស្វែងរក / tag / ចំណាំ | `teta search`, `teta list --tag work` |
| Backup និងស្តារ | `teta backup` / `teta restore` |
| ប្តូរលេខសម្ងាត់មេ | `teta passwd` |

## អ្វីដែលឧបករណ៍នេះ **ធ្វើ** និង **មិនធ្វើ**

✔ រក្សាទុកបញ្ជី Gmail របស់អ្នកក្នុងទូរស័ព្ទ អ៊ិនគ្រីបដោយលេខសម្ងាត់មេ (scrypt + HMAC)។
✔ បង្កើតឈ្មោះបេក្ខជនថ្មីៗ ដែលអាចទៅសាកបង្កើតនៅ Gmail ដោយខ្លួនឯង។
✔ បង្កើតកូដ 2FA (TOTP) ពី secret ដែលអ្នកបានរក្សាទុកពេលកំណត់ 2FA។

✘ មិនបង្កើតគណនី Gmail ស្វ័យប្រវត្តិ មិនឆ្លងកាត់ captcha/phone verification ទេ។
✘ មិនបង្កើតគណនីជំនួសគណនីដែលបាត់ (Google មិនអនុញ្ញាតឱ្យយកឈ្មោះដែលមានរួចមកវិញទេ)។
✘ មិនទាញ OTP ពីលេខទូរស័ព្ទអ្នកដទៃ ឬឧបករណ៍ណាដែលរំលោភលក្ខខណ្ឌ Google។
   ការធ្វើបែបនោះធ្វើឱ្យគណនីត្រូវបានផ្អាក និងអាចមានបញ្ហាច្បាប់។

## ដំឡើងលើ Termux

```sh
pkg update && pkg install python git -y
git clone https://github.com/juykneakhmer-sys/Teta.git
cd Teta
sh install.sh          # ដំឡើង `teta` ចូល $PREFIX/bin
teta --version
```

ឬដំណើរការដោយមិនដំឡើង៖ `./teta.sh --help`

## ចាប់ផ្តើមរហ័ស

```sh
teta init                                   # បង្កើត vault + កំណត់លេខសម្ងាត់មេ
teta gen --seed sokha -n 10                 # ឈ្មោះបេក្ខជន ១០
teta add sokha.chan@gmail.com --label "មេ" --tags main,work \
         --totp JBSWY3DPEHPK3PXP            # បន្ថែមគណនី + 2FA
teta list                                   # បញ្ជី
teta code sokha.chan@gmail.com --watch      # កូដ 2FA ចល័ត
teta backup                                 # backup អ៊ិនគ្រីប
```

`--totp` ទទួលបានទាំង secret base32 និង `otpauth://totp/...?...&secret=...` URI។

## ការពារ និងឯកជនភាព

- Vault គឺ `~/.teta/vault.json` — អ៊ិនគ្រីបទាំងស្រុង (AES មិនទេ តែ stream cipher
  HMAC-SHA256 + encrypt-then-MAC)។ គ្មានអ្វីចេញទៅ internet ទេ។
- KDF៖ scrypt N=2¹⁴, r=8, p=1 (~16 MB RAM — ស្រាលសម្រាប់ទូរស័ព្ទ)។
- File permission 0600, ថត 0700, សរសេរបែប atomic។
- បើបាត់លេខសម្ងាត់មេ → ទិន្នន័យចាត់បាត់វិញ ដោយចេតនា (ការពារ)។

> ⚠️ កុំដាក់ vault ក្នុង git/cloud សាធារណៈ។ ទោះអ៊ិនគ្រីបក៏ដោយ កុំចែករំលែក។

## បញ្ជាទាំងអស់

```
teta init                     បង្កើត vault
teta add EMAIL [--label][--tags][--totp][--note]
teta list [--tag TAG] [--json]
teta show EMAIL [--reveal]
teta rm EMAIL [-y]
teta gen [--seed TEXT] [-n N] [--min][--max] [--domain] [--json]
teta code EMAIL [-w|--watch]
teta set-totp EMAIL SECRET
teta search QUERY
teta passwd
teta backup [--out DIR]
teta restore FILE [--force]
teta info
```

ជម្រើសសកល៖ `--home DIR` (ទីតាំង vault), `--version`.
Environment៖ `TETA_PASSWORD` (សម្រាប់ script — ប្រយ័ត្ន), `TETA_HOME`, `NO_COLOR`។

## ការសាកល្បង

```sh
python -m unittest discover -s tests -t . -v
```

## បញ្ហាដែលជួបញឹកញាប់

| បញ្ហា | ដំណោះស្រាយ |
|---|---|
| `រកមិនឃើញ python` | `pkg install python` |
| បើក vault មិនបាន / លេខសម្ងាត់ខុស | លេខសម្ងាត់មេខុស — សាក `teta restore` ពី backup ដែលដឹងលេខសម្ងាត់ |
| កូដ 2FA មិនត្រូវ | ពេលវេលាទូរស័ព្ទខុស — `pkg install termux-api` ឬបើក automatic time |
| ចង់ផ្លាស់ឯកសារ vault | `teta --home /sdcard/teta ...` |

## License

MIT
