import { z } from 'zod';
import { createMcpHandler } from 'mcp-handler';
import { getCalendarEvents } from '@/lib/tools/calendar';
import { getGmailMessages } from '@/lib/tools/gmail';
import { getNotionTasks } from '@/lib/tools/notion';
import { generateVoiceScript } from '@/lib/tools/openai';
import { synthesizeSpeech } from '@/lib/tools/elevenlabs';
import { postToSlack, uploadFileToSlack } from '@/lib/tools/slack';

// Get environment variables (Vercel provides these via process.env)
function getEnv() {
  return {
    SLACK_BOT_TOKEN: process.env.SLACK_BOT_TOKEN,
    NOTION_API_KEY: process.env.NOTION_API_KEY,
    ELEVENLABS_API_KEY: process.env.ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID: process.env.ELEVENLABS_VOICE_ID,
    ELEVENLABS_MODEL_ID: process.env.ELEVENLABS_MODEL_ID,
    OPENAI_API_KEY: process.env.OPENAI_API_KEY,
    OPENAI_MODEL: process.env.OPENAI_MODEL,
    GOOGLE_OAUTH_CLIENT_ID: process.env.GOOGLE_OAUTH_CLIENT_ID,
    GOOGLE_OAUTH_CLIENT_SECRET: process.env.GOOGLE_OAUTH_CLIENT_SECRET,
    GOOGLE_TOKEN_BASE64: process.env.GOOGLE_TOKEN_BASE64,
    GOOGLE_CALENDAR_ID: process.env.GOOGLE_CALENDAR_ID,
    GMAIL_QUERY: process.env.GMAIL_QUERY,
    GMAIL_MAX: process.env.GMAIL_MAX,
    IMPORTANT_SENDERS: process.env.IMPORTANT_SENDERS,
    NOTION_TASK_DATABASE_ID: process.env.NOTION_TASK_DATABASE_ID,
    NOTION_DONE_VALUES: process.env.NOTION_DONE_VALUES,
    DAYS_AHEAD: process.env.DAYS_AHEAD,
    TZ: process.env.TZ,
    SLACK_USER_ID: process.env.SLACK_USER_ID,
    SLACK_FALLBACK_CHANNEL: process.env.SLACK_FALLBACK_CHANNEL,
  };
}

const handler = createMcpHandler(
  (server) => {
    // Register calendar tool
    server.tool(
      'get_calendar_events',
      'Fetch calendar events from Google Calendar for a time range',
      {
        calendar_id: z.string().optional(),
        time_min: z.string(),
        time_max: z.string(),
      },
      async ({ calendar_id, time_min, time_max }) => {
        return await getCalendarEvents({ calendar_id, time_min, time_max }, getEnv());
      },
    );

    // Register Gmail tool
    server.tool(
      'get_gmail_messages',
      'Search and fetch Gmail messages with optional importance filtering',
      {
        query: z.string().optional(),
        important_senders: z.array(z.string()).optional(),
        max_results: z.number().optional(),
      },
      async ({ query, important_senders, max_results }) => {
        return await getGmailMessages({ query, important_senders, max_results }, getEnv());
      },
    );

    // Register Notion tool
    server.tool(
      'get_notion_tasks',
      'Query Notion tasks database for today, overdue, and upcoming tasks',
      {
        api_key: z.string().optional(),
        database_id: z.string().optional(),
        today_start_iso: z.string(),
        today_end_iso: z.string(),
        days_ahead: z.number().optional(),
        tz: z.string().optional(),
      },
      async ({ api_key, database_id, today_start_iso, today_end_iso, days_ahead, tz }) => {
        return await getNotionTasks(
          { api_key, database_id, today_start_iso, today_end_iso, days_ahead, tz },
          getEnv(),
        );
      },
    );

    // Register OpenAI voice script tool
    server.tool(
      'generate_voice_script',
      'Generate a natural voice script from structured data using OpenAI',
      {
        tz: z.string(),
        user_name: z.string(),
        today_events: z.array(z.any()).optional(),
        tasks_today: z.array(z.any()).optional(),
        emails: z.array(z.any()).optional(),
      },
      async ({ tz, user_name, today_events, tasks_today, emails }) => {
        return await generateVoiceScript(
          { tz, user_name, today_events, tasks_today, emails },
          getEnv(),
        );
      },
    );

    // Register ElevenLabs TTS tool
    server.tool(
      'synthesize_speech',
      'Synthesize speech from text using ElevenLabs TTS',
      {
        text: z.string(),
        voice_id: z.string().optional(),
        model_id: z.string().optional(),
      },
      async ({ text, voice_id, model_id }) => {
        return await synthesizeSpeech({ text, voice_id, model_id }, getEnv());
      },
    );

    // Register Slack post tool
    server.tool(
      'post_to_slack',
      'Post a message to Slack (DM or channel)',
      {
        user_id: z.string().optional(),
        channel: z.string().optional(),
        text: z.string(),
      },
      async ({ user_id, channel, text }) => {
        return await postToSlack({ user_id, channel, text }, getEnv());
      },
    );

    // Register Slack file upload tool
    server.tool(
      'upload_file_to_slack',
      'Upload a file to Slack (DM or channel)',
      {
        user_id: z.string(),
        file_data: z.string(),
        filename: z.string(),
        title: z.string().optional(),
        initial_comment: z.string().optional(),
      },
      async ({ user_id, file_data, filename, title, initial_comment }) => {
        return await uploadFileToSlack(
          { user_id, file_data, filename, title, initial_comment },
          getEnv(),
        );
      },
    );
  },
  {},
  { basePath: '/api' },
);

export { handler as GET, handler as POST, handler as DELETE };

