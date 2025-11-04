# GitHub Repository Setup Guide

## Initial Setup

1. **Create a new repository on GitHub**
   - Go to https://github.com/new
   - Name it `morning-brief-assistant` (or your preferred name)
   - Make it **private** (since it contains secrets)
   - Don't initialize with README (we already have one)

2. **Initialize git and push**
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Morning Brief Assistant"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/morning-brief-assistant.git
   git push -u origin main
   ```

## Setting up GitHub Secrets

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** for each variable below

### Required Secrets

- `SLACK_BOT_TOKEN` - Your Slack bot token
- `SLACK_USER_ID` - Your Slack user ID
- `SLACK_FALLBACK_CHANNEL` - Channel name (e.g., `daily-brief`)
- `NOTION_API_KEY` - Your Notion integration token
- `NOTION_TASK_DATABASE_ID` - Your Notion database ID
- `GOOGLE_CALENDAR_ID` - Your Google Calendar ID (usually `primary`)

### Optional Secrets (Google OAuth)

- `GOOGLE_OAUTH_CLIENT_ID` - If not using `client_secret.json`
- `GOOGLE_OAUTH_CLIENT_SECRET` - If not using `client_secret.json`

### Optional Secrets (Gmail)

- `GMAIL_QUERY` - Default: `label:INBOX newer_than:1d`
- `IMPORTANT_SENDERS` - Comma-separated emails (optional)
- `GMAIL_MAX` - Default: `5`

### Optional Secrets (Notion)

- `NOTION_DONE_VALUES` - Default: `Done`

### Optional Secrets (General)

- `DAYS_AHEAD` - Default: `14`
- `TZ` - Default: `Europe/Oslo`

### Optional Secrets (OpenAI)

- `OPENAI_API_KEY` - For natural voice script generation
- `OPENAI_MODEL` - Default: `gpt-4o-mini`

### Optional Secrets (ElevenLabs)

- `ELEVENLABS_API_KEY` - For voice note generation
- `ELEVENLABS_VOICE_ID` - Voice ID to use
- `ELEVENLABS_MODEL_ID` - Default: `eleven_multilingual_v2`
- `VOICE_MIN_SECS` - Default: `45`
- `VOICE_MAX_SECS` - Default: `70`
- `MOCK_ELEVENLABS` - Set to `false` for production, `true` for testing

## Google OAuth Token Setup for GitHub Actions

Since GitHub Actions can't do interactive OAuth, you need to provide a pre-authenticated token:

### Option 1: Upload token.json (Recommended)

1. **Generate token locally:**
   ```bash
   python -m src.main
   ```
   This will open a browser and create `token.json`

2. **Encode token.json:**
   ```bash
   base64 token.json > token_base64.txt
   cat token_base64.txt
   ```

3. **Add as GitHub Secret:**
   - Name: `GOOGLE_TOKEN_BASE64`
   - Value: The base64 string from step 2

4. **Update workflow to decode it:**
   Add this step before the "Run" step in `.github/workflows/run.yml`:
   ```yaml
   - name: Setup Google OAuth Token
     env:
       GOOGLE_TOKEN_BASE64: ${{ secrets.GOOGLE_TOKEN_BASE64 }}
     run: |
       echo "$GOOGLE_TOKEN_BASE64" | base64 -d > token.json
   ```

### Option 2: Use Service Account (Advanced)

1. Create a service account in Google Cloud Console
2. Download the JSON key file
3. Add it as a GitHub secret (base64 encoded)
4. Modify the code to use service account auth instead of OAuth

## Testing the Workflow

1. **Manual trigger:**
   - Go to **Actions** tab
   - Click "Morning Brief" workflow
   - Click "Run workflow" → "Run workflow"

2. **Check logs:**
   - Click on the workflow run
   - Check the logs for any errors
   - The brief should be sent to your Slack DM

## Schedule

The workflow runs daily at **06:30 UTC** (which is 07:30 Europe/Oslo in winter, 08:30 in summer due to daylight saving).

To change the schedule, edit `.github/workflows/run.yml`:
```yaml
schedule:
  - cron: '30 6 * * *'  # Format: minute hour day month day-of-week
```

Cron format: `minute hour day month day-of-week`
- `30 6 * * *` = 06:30 UTC every day
- `0 7 * * *` = 07:00 UTC every day
- `30 7 * * 1-5` = 07:30 UTC on weekdays only

## Troubleshooting GitHub Actions

### Workflow not running
- Check that GitHub Actions is enabled in repository settings
- Verify the cron schedule is correct
- Check timezone (GitHub Actions uses UTC)

### Authentication errors
- Verify all secrets are set correctly
- Check that `token.json` is properly base64 encoded
- Ensure Google OAuth token hasn't expired

### Import errors
- Check that `requirements.txt` includes all dependencies
- Verify Python version in workflow matches local (3.11)

### Missing data
- Check workflow logs for specific errors
- Verify all API keys and IDs are correct
- Ensure databases/integrations have proper access

