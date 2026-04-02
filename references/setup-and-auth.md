# Setup and Authentication Guide

## Table of Contents

1. [API Key Required](#api-key-required)
2. [Getting Your API Key](#getting-your-api-key)
3. [Setting the API Key](#setting-the-api-key)
4. [Verifying Your Setup](#verifying-your-setup)
5. [Rate Limits](#rate-limits)
6. [Security Best Practices](#security-best-practices)
7. [Troubleshooting](#troubleshooting)

---

## API Key Required

This skill uses a single API key:

| Variable | Required | APIs Covered |
|----------|----------|-------------|
| `USPTO_ODP_API_KEY` | Yes | ODP Patent Search, File Wrapper, PTAB, Assignments, Petitions, Bulk Data, Legacy OA APIs, TSDR |

One free key covers all USPTO APIs used by this skill. No paid tier is required.

---

## Getting Your API Key

1. Go to https://data.uspto.gov/myodp
2. Sign in or create a USPTO.gov account
3. Complete ID.me identity verification (one-time step -- requires a government-issued ID)
4. Once verified, your API key will be displayed on the My ODP page
5. Copy the key -- you will need it for the environment variable

For detailed instructions: https://data.uspto.gov/apis/getting-started

---

## Interactive Setup (Recommended)

The easiest way to configure your key is the interactive setup script:

```bash
python get_started.py
```

This will:
1. Prompt you for your ODP API key
2. Show a masked preview of the value you entered
3. Save the key to a `.env` file in the project root
4. Create a virtual environment and install dependencies

You can re-run it anytime to update the key.

---

## Setting the API Key (Alternative)

If you prefer not to use the interactive setup, you can configure the key manually.

### Option 1: .env file

Create a `.env` file in the project root:

```
USPTO_ODP_API_KEY="your_odp_key_here"
```

### Option 2: Shell environment variable

#### macOS / Linux (bash/zsh)

Add this line to your shell profile (`~/.bashrc`, `~/.zshrc`, or `~/.profile`):

```bash
export USPTO_ODP_API_KEY="your_odp_key_here"
```

Then reload your shell:
```bash
source ~/.zshrc    # or ~/.bashrc
```

#### Windows (PowerShell)

```powershell
[Environment]::SetEnvironmentVariable("USPTO_ODP_API_KEY", "your_odp_key_here", "User")
```

Restart your terminal for changes to take effect.

#### Windows (Command Prompt)

```cmd
setx USPTO_ODP_API_KEY "your_odp_key_here"
```

#### For a single session only (temporary)

```bash
export USPTO_ODP_API_KEY="your_key"
```

This will only last until you close the terminal.

---

## Verifying Your Setup

Run the client verification script:

```bash
cd scripts/
python uspto_client.py
```

Expected output:
```
API Key Status:
  odp_key_set: OK
```

If the key shows `MISSING`, check that the environment variable is set correctly.

### Quick API test

```bash
cd scripts/
python patent_search.py patent 10000000
```

This should return metadata for US Patent 10,000,000.

---

## Rate Limits

| API Family | Weekly Limit | Burst Limit |
|------------|-------------|-------------|
| ODP Metadata APIs (Search, PTAB, Assignments, etc.) | 5,000,000 requests/week | 1 request/second |
| ODP Document APIs (PDF/ZIP downloads) | 1,200,000 requests/week | 1 request/second |
| TSDR (Trademarks) | Similar limits | 1 request/second |

The scripts handle rate limiting automatically with a token bucket algorithm.
If you hit a limit, the script will wait and retry. You will see a log message:
```
Rate limit reached. Waiting 5.1s...
```

For bulk operations, the scripts respect the document download rate limits automatically.

---

## Security Best Practices

### Do

- Store your API key in environment variables or a `.env` file only
- Use `.env.example` as a template (never put real keys in it)
- Rotate your key periodically via the My ODP portal

### Do Not

- Commit API keys to version control (git)
- Put keys in source code, config files, or scripts
- Share keys in emails, chat, or documentation
- Log or print API keys in output

### If Your Key is Compromised

1. Go to https://data.uspto.gov/myodp and regenerate your key
2. Update your `.env` file or environment variable with the new key
3. Review any logs for unauthorized usage

### .gitignore

If you create a local `.env` file, ensure `.env` is in your `.gitignore`:

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
```

If blank, re-export and check your shell profile file. If using a `.env` file, ensure it is in the project root directory.

### 401 Unauthorized

- Key may be invalid or expired
- Check you copied the full key with no trailing whitespace
- Try regenerating the key from https://data.uspto.gov/myodp

### 429 Too Many Requests

- You are hitting the rate limit
- The scripts automatically retry with backoff
- If you see this frequently, reduce your query frequency
- Consider caching results for repeated queries

### 404 Not Found

- Check the application/patent number format
- ODP expects application numbers without slashes: `16123456` not `16/123,456`
- Patent numbers should be plain digits: `10000000` not `10,000,000`
- The scripts clean these formats automatically, but verify the underlying number is correct

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

Or use the interactive setup which handles this automatically:
```bash
python get_started.py
```

### .env file not being loaded

If your key is set in `.env` but scripts report it as missing:
- Ensure `python-dotenv` is installed: `pip install python-dotenv`
- Verify the `.env` file is in the project root (same directory as `get_started.py`)
- Check the file format -- each line should be `KEY="value"` with no extra spaces
- Run `python get_started.py` to regenerate the file if needed
