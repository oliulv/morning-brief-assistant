# Morning Brief MCP Server

This is a Vercel-hosted MCP (Model Context Protocol) server that provides tools for the morning brief assistant.

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Configure environment variables in Vercel:
   - Go to your Vercel project settings
   - Add environment variables:
     - `SLACK_BOT_TOKEN`
     - `NOTION_API_KEY`
     - `ELEVENLABS_API_KEY`
     - `OPENAI_API_KEY`
     - `GOOGLE_OAUTH_CLIENT_ID`
     - `GOOGLE_OAUTH_CLIENT_SECRET`
     - `GOOGLE_TOKEN_BASE64`
     - `GOOGLE_CALENDAR_ID`
     - `GMAIL_QUERY`
     - `GMAIL_MAX`
     - `IMPORTANT_SENDERS`
     - `NOTION_TASK_DATABASE_ID`
     - `NOTION_DONE_VALUES`
     - `DAYS_AHEAD`
     - `TZ`
     - `SLACK_USER_ID`
     - `SLACK_FALLBACK_CHANNEL`
     - `ELEVENLABS_VOICE_ID`
     - `ELEVENLABS_MODEL_ID`
     - `OPENAI_MODEL`

3. Deploy:
   ```bash
   vercel deploy --prod
   ```

   Or connect your GitHub repository to Vercel for automatic deployments.

## Local Development

```bash
npm run dev
```

The MCP server will be available at `http://localhost:3000/api/mcp`

## Tools

- `get_calendar_events` - Fetch Google Calendar events
- `get_gmail_messages` - Search Gmail messages
- `get_notion_tasks` - Query Notion tasks
- `generate_voice_script` - Generate voice script with OpenAI
- `synthesize_speech` - Synthesize speech with ElevenLabs
- `post_to_slack` - Post message to Slack
- `upload_file_to_slack` - Upload file to Slack

## Testing

Use the MCP Inspector to test:
```bash
npx @modelcontextprotocol/inspector@latest http://localhost:3000
```

Then connect to `http://localhost:3000/api/mcp` in the inspector.
