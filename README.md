# Teta — ឧបករណ៍គ្រប់គ្រងគណនីផ្ទាល់ខ្លួន សម្រាប់ Termux

ឧបករណ៍ command-line (Python សុទ្ធ, គ្មាន dependency) សម្រាប់ **គ្រប់គ្រងគណនី
ផ្ទាល់ខ្លួនរបស់អ្នក** នៅលើទូរស័ព្ទ Android តាម Termux — ទាំង Gmail, គណនី
Mobile Legends (Moonton), ហ្គេមផ្សេងៗ និង social។

អ្វីៗរក្សាទុកក្នុងទូរស័ព្ទតែមួយកន្លែង អ៊ិនគ្រីបដោយលេខសម្ងាត់មេ —
**គ្មានអ្វីចេញទៅ internet ទេ** គ្មាន server គ្មាន cloud គ្មាន telemetry។

| មុខងារ | បញ្ជា |
|---|---|
| ឃ្លាំងគណនីអ៊ិនគ្រីប (vault) | `teta init` / `add` / `list` / `show` / `edit` / `rm` |
| គណនីហ្គេម (ID + Zone + password) | `teta add 654321987 --kind moonton --zone 2001 --pass -` |
| ចម្លងលឿនទៅ clipboard | `teta copy 654321987 -f password --clear-after 30` |
| បង្កើតលេខសម្ងាត់ខ្លាំង | `teta genpass -L 24` / `teta genpass --phrase` |
| កូដ 2FA ៦ ខ្ទង់ offline | `teta code sokha.chan@gmail.com --watch` |
| ពិនិត្យសុវត្ថិភាពគណនី | `teta audit` |
| Backup / export / ស្តារ | `teta backup` / `export` / `restore` |
| ប្តូរលេខសម្ងាត់មេ | `teta passwd` |
| ណែនាំផ្លូវស្តារគណនីផ្លូវការ | `teta recovery` |

## អ្វីដែលឧបករណ៍នេះ **ធ្វើ** និង **មិនធ្វើ**

✔ រក្សាទុកបញ្ជីគណនីរបស់អ្នក (អ៊ីមែល, game ID, password, zone, 2FA secret, note)
ក្នុងទូរស័ព្ទ អ៊ិនគ្រីបដោយលេខសម្ងាត់មេ (scrypt + HMAC-SHA256)។
✔ ជួយអ្នក *គ្រប់គ្រង* គណនីខ្លួនឯង៖ ស្វែងរក, ចម្លង password, បង្កើតកូដ 2FA,
ពិនិត្យថាតើ password ណាខ្សោយ ឬប្រើដដែល។
✔ បង្កើតឈ្មោះបេក្ខជនថ្មីៗ ដែលអ្នកអាចទៅសាកបង្កើតនៅ Gmail ដោយខ្លួនឯង។

✘ **មិនចូលគណនីដោយប្រើ token/session ជំនួសអ្នកទេ** ហើយ**មិនផ្លាស់ប្តូរ
email ភ្ជាប់ (Moonton/Gmail) តាម API ក្រៅផ្លូវការទេ** — ការធ្វើបែបនោះគឺ
account takeover៖ ខុសលក្ខខណ្ឌ Moonton/Google, ធ្វើឱ្យគណនីត្រូវផ្អាក និងមាន
បញ្ហាច្បាប់។ បើអ្នកបាត់ការចូលគណនីខ្លួនឯង សូមប្រើ `teta recovery`។
✘ មិនបង្កើតគណនីស្វ័យប្រវត្តិ មិនឆ្លងកាត់ captcha/phone verification។
✘ មិនទាញ OTP ពីលេខទូរស័ព្ទអ្នកដទៃ ឬឧបករណ៍ណាដែលរំលោភលក្ខខណ្ឌ។

> បើគណនី MLBB របស់អ្នកត្រូវបានគេយក សូមប្តូរ password ភ្លាមនៅ
> account.moontongames.com និងផ្ញើ ticket ទៅ Moonton Support។ `teta recovery`
> មានបញ្ជីឯកសារដែលត្រូវផ្តល់។

## ដំឡើងលើ Termux

```sh
pkg update && pkg install python git -y
git clone https://github.com/juykneakhmer-sys/Teta.git
cd Teta
sh install.sh          # ដំឡើង `teta` ចូល $PREFIX/bin
teta --version
```

ជម្រើស (សម្រាប់ `teta copy` ចូល clipboard):

```sh
pkg install termux-api -y     # ព្រមទាំងដំឡើង app "Termux:API" ពី F-Droid
```

ឬដំណើរការដោយមិនដំឡើង៖ `./teta.sh --help`

## ចាប់ផ្តើមរហ័ស

```sh
teta init                                   # បង្កើត vault + កំណត់លេខសម្ងាត់មេ

# គណនី Gmail
teta add sokha.chan@gmail.com --label "មេ" --tags main,work \
         --totp JBSWY3DPEHPK3PXP --pass -

# គណនី Mobile Legends (Game ID + Zone ID)
teta add 654321987 --kind moonton --user 654321987 --zone 2001 \
         --label "smurf main" --tags mlbb

teta list                                   # បញ្ជីទាំងអស់
teta list --kind moonton                    # តែគណនីហ្គេម
teta show "smurf main"                      # password ត្រូវបានលាក់
teta copy "smurf main" -f password --clear-after 30
teta code sokha.chan@gmail.com --watch      # កូដ 2FA ចល័ត
teta audit                                  # ពិន្ទុសុវត្ថិភាព + បញ្ហាដែលត្រូវកែ
teta backup                                 # backup អ៊ិនគ្រីប
```

`--pass -` មានន័យថា **វាយលេខសម្ងាត់ដោយលាក់** (មិនបង្ហាញក្នុង terminal
ឬក្នុង process list)។ បើសរសេរ `--pass 'abc'` ត្រង់ៗ វានឹងឃើញក្នុង `ps` —
ដូច្នេះប្រើ `--pass -` ឬ `teta edit KEY --pass -` ជាទូទៅ។

`--totp` ទទួលបានទាំង secret base32 និង `otpauth://totp/...?...&secret=...` URI។

## ប្រភេទគណនី (`--kind`)

| kind | ប្រើសម្រាប់ | ឧទាហរណ៍ |
|---|---|---|
| `gmail` | គណនី Google (default បើជាអ៊ីមែល Gmail) | `teta add you@gmail.com` |
| `email` | អ៊ីមែលផ្សេង (Yahoo, Outlook, ...) | `teta add you@outlook.com` |
| `moonton` | គណនី Moonton / Mobile Legends | `teta add 654321987 --kind moonton --zone 2001` |
| `game` | ហ្គេមផ្សេង | `teta add 12345678 --kind game --user myign` |
| `social` | Facebook, TikTok, Discord, ... | `teta add me@x.com --kind social` |
| `other` | អ្វីផ្សេងទៀត | `teta add shopee-user --kind other` |

## បញ្ជាទាំងអស់

```
teta init
teta add EMAIL|USERNAME [--kind] [--user] [--pass] [--zone] [--url]
                        [--label] [--tags] [--totp] [--note]
teta list [--kind KIND] [--tag TAG] [--json]
teta show KEY [--reveal]
teta edit KEY [--label] [--tags] [--note] [--kind] [--user] [--pass]
             [--zone] [--url] [--email-new] [--totp]
teta copy KEY [-f password|username|email|server|url|totp|note] [--clear-after SEC]
teta rm KEY [-y]
teta search QUERY
teta gen [--seed TEXT] [-n N] [--min] [--max] [--domain] [--json]
teta genpass [-L N] [--phrase] [--words N] [--no-symbols] [--json] [-v]
teta code KEY [-w|--watch]
teta set-totp KEY SECRET
teta audit [--json]
teta export [--format csv|json] [-o FILE|-] [--kind KIND] [-y]
teta backup [--out DIR]
teta restore FILE [--force]
teta passwd
teta recovery [--topic all|moonton|google]
teta info
```

`KEY` = អ៊ីមែល, login name/Game ID, ឬ label (បើ label មានតែមួយ)។

ជម្រើសសកល៖ `--home DIR` (ទីតាំង vault), `--version`.
Environment៖ `TETA_PASSWORD` (សម្រាប់ script — ប្រយ័ត្ន), `TETA_HOME`, `NO_COLOR`។

## សុវត្ថិភាព

- Vault គឺ `~/.teta/vault.json` — អ៊ិនគ្រីបទាំងស្រុង (stream cipher HMAC-SHA256
  + encrypt-then-MAC)។ គ្មានអ្វីចេញទៅ internet ទេ។
- KDF៖ scrypt N=2¹⁴, r=8, p=1 (~16 MB RAM — ស្រាលសម្រាប់ទូរស័ព្ទ)។
- File permission `0600`, ថត `0700`, សរសេរបែប atomic។
- បើបាត់លេខសម្ងាត់មេ → ទិន្នន័យចាត់បាត់វិញ ដោយចេតនា (ការពារ)។
- `teta export` បញ្ចេញ **plaintext** — ត្រូវការ `--yes`/ការបញ្ជាក់ ហើយសរសេរ
  ជា `0600`។ លុបឯកសារនោះភ្លាមក្រោយប្រើ។
- `teta audit` ដំណើរការ offline៖ រក password ខ្សោយ, password ប្រើដដែល,
  គណនីគ្មាន 2FA, និងគណនីមិនបានពិនិត្យយូរ។

> ⚠️ កុំដាក់ vault ក្នុង git/cloud សាធារណៈ។ ទោះអ៊ិនគ្រីបក៏ដោយ កុំចែករំលែក។

## ការសាកល្បង

```sh
python -m unittest discover -s tests -t . -v
```

## បញ្ហាដែលជួបញឹកញាប់

| បញ្ហា | ដំណោះស្រាយ |
|---|---|
| `រកមិនឃើញ python` | `pkg install python` |
| បើក vault មិនបាន / លេខសម្ងាត់ខុស | លេខសម្ងាត់មេខុស — សាក `teta restore` ពី backup ដែលដឹងលេខសម្ងាត់ |
| `teta copy` មិនចម្លង | `pkg install termux-api` + ដំឡើង app Termux:API |
| កូដ 2FA មិនត្រូវ | ពេលវេលាទូរស័ព្ទខុស — បើក automatic time (Settings → Date & time) |
| ចង់ផ្លាស់ឯកសារ vault | `teta --home /sdcard/teta ...` |

## License

MIT
