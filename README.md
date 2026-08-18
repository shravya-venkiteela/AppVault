# AppVault

A command-line tool that connects to your email inbox via IMAP, automatically detects and logs job application status updates, and tells you which applications deserve your follow-up attention today, and why.

## What it does

- **`add`** — manually log a job application
- **`list`** — see everything you've logged
- **`sync`** — scan your inbox and automatically log new application confirmations, rejections, and offers
- **`prioritize`** — rank your open applications by follow-up priority, with reasoning
- **`status set`** / **`status rate`** — update an application's status or your interest rating
- **`duplicate-check`** — check if a company name looks similar to something already logged
- **`delete`** — remove a record

## Installation

```bash
git clone https://github.com/shravya-venkiteela/AppVault.git
cd AppVault
poetry install
```

## Setting up email access

This is the part of setup that's genuinely more involved than a typical CLI tool, because it needs read access to your inbox. Take it slowly, a rushed setup here is the most common source of confusing errors later.

### 1. Generate an app-specific password

AppVault connects via IMAP using an **app-specific password**, not your normal Google account password. Your normal password will not work here, and using it is not supported.

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Confirm **2-Step Verification** is turned on. App-specific passwords are only available once 2FA is enabled.
3. Go directly to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
4. Create a new app password (name it something like "AppVault")
5. Google shows you the password **once**. Copy it immediately, you cannot view it again later.

**Important:** if you ever change your main Google account password, Google automatically revokes all app-specific passwords tied to it. If `sync` suddenly starts failing with an authentication error after you've changed your password, this is almost always why, generate a new app password and update your environment variables.

### 2. Set your credentials as environment variables

AppVault reads three environment variables. **Never put these in a file that could be committed to git.**

```
APPVAULT_EMAIL_ADDRESS   — your full email address
APPVAULT_EMAIL_PASSWORD  — the app-specific password from step 1
APPVAULT_IMAP_HOST       — your provider's IMAP host (imap.gmail.com for Gmail)
```

**Recommended approach (PowerShell):** use a setup script that prompts for the password securely, so it never gets typed in plaintext or saved to your shell history:

```powershell
# setup-env.ps1  (this file should be in your .gitignore)
$securePassword = Read-Host -AsSecureString "Enter APPVAULT_EMAIL_PASSWORD"
$env:APPVAULT_EMAIL_PASSWORD = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
)
$env:APPVAULT_EMAIL_ADDRESS = "you@example.com"
$env:APPVAULT_IMAP_HOST = "imap.gmail.com"
```

Run it at the start of each terminal session:
```powershell
. .\setup-env.ps1
```

Environment variables set this way only last for the current terminal session, you'll need to re-run this each time you open a new one. This is a deliberate tradeoff: nothing sensitive ever touches disk.

### 3. Verify the connection

```bash
poetry run appvault sync --limit 1
```

If this fails with an authentication error, double check:
- You're using the app-specific password, not your regular password
- The password hasn't been revoked (check [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) — if AppVault isn't listed, generate a new one)
- `APPVAULT_IMAP_HOST` is correct for your provider (no `https://`, no trailing slash, no port, just the bare hostname)

## Configuring email-matching patterns

AppVault detects application-related emails and extracts company/role/status using regex patterns defined in [`examples/patterns.yaml`](examples/patterns.yaml), not hardcoded in Python. This means you can adapt the matching to a different inbox, provider, or wording style without touching any code.

The file has six sections:

- **`offer`**, **`rejected`**, **`received`**, **`interview`** — lists of phrases that indicate each application status. Checked in that priority order (an email matching both "offer" and "received" language is treated as an offer).
- **`company_extraction`**, **`role_extraction`** — patterns with exactly one capture group each, used to pull the company name and role title out of the email body.
- **`junk_company_names`** — a list of common words (like "us", "the", "our") that get rejected even if a pattern technically matches them, to avoid false positives like a stray "join us" being logged as a company named "us".

If you edit `patterns.yaml`, run the test suite afterward (`poetry run pytest tests/test_parser.py`) to catch anything that broke.

## Sample `prioritize` output

```
Top 3 to follow up on:

1. iSpot - Data Scientist (PENDING, 30 pts)
   - interest rating 5/5 (20 pts)

2. Lyft - Data Analyst (PENDING, 26 pts)
   - interest rating 4/5 (16 pts)

3. Hive - Analyst (PENDING, 18 pts)
   - interest rating 2/5 (8 pts)
```

Scoring combines application status, how overdue a response is relative to a 14-day default benchmark, your own 1–5 interest rating, and whether an application has gone completely silent versus shown some momentum (interview scheduled, contact logged). The exact weighting is in [`src/appvault/scoring.py`](src/appvault/scoring.py) — adjust the constants there if `prioritize` isn't surfacing the right things for you after some real use.

Rejected and withdrawn applications are excluded from ranking entirely — there's nothing to follow up on.

## Testing

The full test suite runs entirely offline — no real network access or live credentials required:

```bash
poetry run pytest
```

To confirm this claim rather than take it on faith, disconnect from the internet and run the suite again; it should still pass fully green.

See [LIMITATIONS.md](LIMITATIONS.md) for known gaps and simplifications.
