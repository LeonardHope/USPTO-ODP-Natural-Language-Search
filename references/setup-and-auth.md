# Setup and Authentication Guide

## Table of Contents

1. [API Keys Required](#api-keys-required)
2. [Getting Your API Keys](#getting-your-api-keys)
3. [Setting Environment Variables](#setting-environment-variables)
4. [Verifying Your Setup](#verifying-your-setup)
5. [Rate Limits](#rate-limits)
6. [Security Best Practices](#security-best-practices)
7. [Troubleshooting](#troubleshooting)

---

## API Keys Required

This skill uses two API keys:

| Variable | Required | APIs Covered |
|----------|----------|-------------|
| `USPTO_ODP_API_KEY` | Yes | ODP File Wrapper, PTAB, Assignments, Legacy OA APIs |
| `PATENTSVIEW_API_KEY` | Yes | PatentsView PatentSearch API |

Both keys are free. No paid tier is required.

---

## Getting Your API Keys

### USPTO Open Data Portal Key

1. Go to https://data.uspto.gov/myodp
2. Sign in or create a USPTO.gov account
3. Link your ID.me account for identity verification (one-time step)
4. Your API key will be displayed on the My ODP page
5. Copy the key — you will need it for the environment variable

For detailed instructions: https://data.uspto.gov/apis/getting-started

### PatentsView API Key

1. Go to https://patentsview.org/apis/keyrequest
2. Fill out the request form (name, email, organization, intended use)
3. Your API key will be emailed to you
4. Copy the key from the email

---

## Interactive Setup (Recommended)

The easiest way to configure your keys is the interactive setup script:

```bash
python get_started.py
```

This will:
1. Prompt you for each API key
2. Show a masked preview of the value you entered
3. Save both keys to a `.env` file in the project root
4. Support updating individual keys without losing the other

You can re-run it anytime to update a key.

---

## Setting Environment Variables (Alternative)

If you prefer not to use `.env` files, set environment variables directly.

### macOS / Linux (bash/zsh)

Add these lines to your shell profile (`~/.bashrc`, `~/.zshrc`, or `~/.profile`):

```bash
export USPTO_ODP_API_KEY="your_odp_key_here"
export PATENTSVIEW_API_KEY="your_patentsview_key_here"
```

Then reload your shell:
```bash
source ~/.zshrc    # or ~/.bashrc
```

### Windows (PowerShell)

Set persistent environment variables:
```powershell
[Environment]::SetEnvironmentVariable("USPTO_ODP_API_KEY", "your_odp_key_here", "User")
[Environment]::SetEnvironmentVariable("PATENTSVIEW_API_KEY", "your_patentsview_key_here", "User")
```

Restart your terminal for changes to take effect.

### Windows (Command Prompt)

```cmd
setx USPTO_ODP_API_KEY "your_odp_key_here"
setx PATENTSVIEW_API_KEY "your_patentsview_key_here"
```

### For a single session only (temporary)

```bash
export USPTO_ODP_API_KEY="your_key"
export PATENTSVIEW_API_KEY="your_key"
```

These will only last until you close the terminal.

---

## Verifying Your Setup

Run the key check script:

```bash
cd scripts/
python uspto_client.py
```

Expected output:
```
API Key Status:
  odp_key_set: OK
  patentsview_key_set: OK
```

If any key shows `MISSING`, check that the environment variable is set correctly.

### Quick API test

```bash
# Test PatentsView
python patentsview_search.py patent 10000000

# Test ODP
python odp_search.py get 16000000
```

---

## Rate Limits

| API | Requests/Minute | PDF/ZIP Downloads |
|-----|-----------------|-------------------|
| ODP (File Wrapper, PTAB) | 60 | 4/min |
| PatentsView | 45 | N/A |
| Legacy (Office Actions) | 60 | N/A |
| Assignment Search | 60 | N/A |

The scripts handle rate limiting automatically with a token bucket algorithm.
If you hit a limit, the script will wait and retry. You will see a log message:
```
Rate limit reached. Waiting 5.1s...
```

For bulk operations, the scripts respect the lower PDF/ZIP rate limit of
4 requests per minute.

---

## Security Best Practices

### Do

- Store API keys in environment variables only
- Use `.env.example` as a template (never put real keys in it)
- Rotate your keys periodically
- Use separate keys for development and production if possible

### Do Not

- Commit API keys to version control (git)
- Put keys in source code, config files, or scripts
- Share keys in emails, chat, or documentation
- Log or print API keys in output
- Store keys in browser localStorage or cookies

### If a Key is Compromised

1. Generate a new key immediately from the respective portal
2. Update your environment variables with the new key
3. Revoke the old key if possible (check the portal settings)
4. Review any logs for unauthorized usage

### .gitignore

If you create a local `.env` file for convenience, ensure `.env` is in your
`.gitignore`:

```
.env
.env.local
.env.*.local
```

---

## Troubleshooting

### "API key not set" error

Verify the variable is exported (not just set):
```bash
echo $USPTO_ODP_API_KEY    # Should show your key
echo $PATENTSVIEW_API_KEY  # Should show your key
```

If blank, re-export and check your shell profile file.

### 401 Unauthorized

- Key may be invalid or expired
- Check you copied the full key with no trailing whitespace
- Try regenerating the key from the portal

### 429 Too Many Requests

- You are hitting the rate limit
- The scripts automatically retry with backoff
- If you see this frequently, reduce your query frequency
- Consider caching results for repeated queries

### 404 Not Found

- Check the application/patent number format
- ODP expects numbers without slashes: `16123456` not `16/123,456`
- PatentsView expects patent numbers without commas: `10000000` not `10,000,000`

### Connection Errors

- Check your internet connection
- The APIs may be temporarily down for maintenance
- Try again in a few minutes
- Check https://data.uspto.gov for any maintenance notices

### "requests" library not found

Install all dependencies:
```bash
pip install -r requirements.txt
```

### .env file not being loaded

If keys are set in `.env` but scripts report them as missing:
- Ensure `python-dotenv` is installed: `pip install python-dotenv`
- Verify the `.env` file is in the project root (same directory as `get_started.py`)
- Check the file format — each line should be `KEY="value"` with no extra spaces
- Run `python get_started.py` to regenerate the file if needed
