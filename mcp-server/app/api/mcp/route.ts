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

// Simple HTTP handler for MCP protocol
export async function GET(request: Request) {
  return handleRequest(request);
}

export async function POST(request: Request) {
  return handleRequest(request);
}

export async function DELETE(request: Request) {
  return handleRequest(request);
}

async function handleRequest(request: Request): Promise<Response> {
  // Handle CORS
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      },
    });
  }

  try {
    const body = await request.json().catch(() => ({}));
    const { method, params } = body;

    let result: any;

    if (method === 'tools/list') {
      result = {
        tools: [
          {
            name: 'get_calendar_events',
            description: 'Fetch calendar events from Google Calendar for a time range',
            inputSchema: {
              type: 'object',
              properties: {
                calendar_id: { type: 'string', description: 'Google Calendar ID (default: primary)' },
                time_min: { type: 'string', description: 'Start time in ISO 8601 format' },
                time_max: { type: 'string', description: 'End time in ISO 8601 format' },
              },
              required: ['time_min', 'time_max'],
            },
          },
          {
            name: 'get_gmail_messages',
            description: 'Search and fetch Gmail messages with optional importance filtering',
            inputSchema: {
              type: 'object',
              properties: {
                query: { type: 'string', description: 'Gmail search query' },
                important_senders: { type: 'array', items: { type: 'string' } },
                max_results: { type: 'number', description: 'Maximum number of results' },
              },
            },
          },
          {
            name: 'get_notion_tasks',
            description: 'Query Notion tasks database for today, overdue, and upcoming tasks',
            inputSchema: {
              type: 'object',
              properties: {
                api_key: { type: 'string' },
                database_id: { type: 'string' },
                today_start_iso: { type: 'string' },
                today_end_iso: { type: 'string' },
                days_ahead: { type: 'number' },
                tz: { type: 'string' },
              },
              required: ['today_start_iso', 'today_end_iso'],
            },
          },
          {
            name: 'generate_voice_script',
            description: 'Generate a natural voice script from structured data using OpenAI',
            inputSchema: {
              type: 'object',
              properties: {
                tz: { type: 'string' },
                user_name: { type: 'string' },
                today_events: { type: 'array' },
                tasks_today: { type: 'array' },
                emails: { type: 'array' },
              },
              required: ['tz', 'user_name'],
            },
          },
          {
            name: 'synthesize_speech',
            description: 'Synthesize speech from text using ElevenLabs TTS',
            inputSchema: {
              type: 'object',
              properties: {
                text: { type: 'string' },
                voice_id: { type: 'string' },
                model_id: { type: 'string' },
              },
              required: ['text'],
            },
          },
          {
            name: 'post_to_slack',
            description: 'Post a message to Slack (DM or channel)',
            inputSchema: {
              type: 'object',
              properties: {
                user_id: { type: 'string' },
                channel: { type: 'string' },
                text: { type: 'string' },
              },
              required: ['text'],
            },
          },
          {
            name: 'upload_file_to_slack',
            description: 'Upload a file to Slack (DM or channel)',
            inputSchema: {
              type: 'object',
              properties: {
                user_id: { type: 'string' },
                file_data: { type: 'string' },
                filename: { type: 'string' },
                title: { type: 'string' },
                initial_comment: { type: 'string' },
              },
              required: ['user_id', 'file_data', 'filename'],
            },
          },
        ],
      };
    } else if (method === 'tools/call') {
      const toolName = params?.name;
      const toolArgs = params?.arguments || {};
      const env = getEnv();

      switch (toolName) {
        case 'get_calendar_events':
          result = await getCalendarEvents(
            {
              calendar_id: toolArgs.calendar_id,
              time_min: toolArgs.time_min,
              time_max: toolArgs.time_max,
            },
            env,
          );
          break;
        case 'get_gmail_messages':
          result = await getGmailMessages(
            {
              query: toolArgs.query,
              important_senders: toolArgs.important_senders,
              max_results: toolArgs.max_results,
            },
            env,
          );
          break;
        case 'get_notion_tasks':
          result = await getNotionTasks(
            {
              api_key: toolArgs.api_key,
              database_id: toolArgs.database_id,
              today_start_iso: toolArgs.today_start_iso,
              today_end_iso: toolArgs.today_end_iso,
              days_ahead: toolArgs.days_ahead,
              tz: toolArgs.tz,
            },
            env,
          );
          break;
        case 'generate_voice_script':
          result = await generateVoiceScript(
            {
              tz: toolArgs.tz,
              user_name: toolArgs.user_name,
              today_events: toolArgs.today_events,
              tasks_today: toolArgs.tasks_today,
              emails: toolArgs.emails,
            },
            env,
          );
          break;
        case 'synthesize_speech':
          result = await synthesizeSpeech(
            {
              text: toolArgs.text,
              voice_id: toolArgs.voice_id,
              model_id: toolArgs.model_id,
            },
            env,
          );
          break;
        case 'post_to_slack':
          result = await postToSlack(
            {
              user_id: toolArgs.user_id,
              channel: toolArgs.channel,
              text: toolArgs.text,
            },
            env,
          );
          break;
        case 'upload_file_to_slack':
          result = await uploadFileToSlack(
            {
              user_id: toolArgs.user_id,
              file_data: toolArgs.file_data,
              filename: toolArgs.filename,
              title: toolArgs.title,
              initial_comment: toolArgs.initial_comment,
            },
            env,
          );
          break;
        default:
          return new Response(
            JSON.stringify({
              error: {
                code: -32601,
                message: `Unknown tool: ${toolName}`,
              },
            }),
            {
              status: 404,
              headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
              },
            },
          );
      }
    } else {
      return new Response(
        JSON.stringify({ error: `Unknown method: ${method}` }),
        {
          status: 400,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        },
      );
    }

    return new Response(JSON.stringify({ result }), {
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });
  } catch (error: any) {
    return new Response(
      JSON.stringify({
        error: {
          code: -32603,
          message: error.message || 'Internal server error',
        },
      }),
      {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      },
    );
  }
}
