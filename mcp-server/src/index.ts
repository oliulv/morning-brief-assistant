// Simple error codes matching MCP protocol
const ErrorCode = {
  MethodNotFound: -32601,
  InvalidParams: -32602,
  InternalError: -32603,
} as const;
import { getCalendarEventsTool } from "./tools/calendar.js";
import { getGmailMessagesTool } from "./tools/gmail.js";
import { getNotionTasksTool } from "./tools/notion.js";
import { generateVoiceScriptTool } from "./tools/openai.js";
import { synthesizeSpeechTool } from "./tools/elevenlabs.js";
import { postToSlackTool, uploadFileToSlackTool } from "./tools/slack.js";

export interface Env {
  SLACK_BOT_TOKEN?: string;
  NOTION_API_KEY?: string;
  ELEVENLABS_API_KEY?: string;
  ELEVENLABS_VOICE_ID?: string;
  ELEVENLABS_MODEL_ID?: string;
  OPENAI_API_KEY?: string;
  OPENAI_MODEL?: string;
  GOOGLE_OAUTH_CLIENT_ID?: string;
  GOOGLE_OAUTH_CLIENT_SECRET?: string;
  GOOGLE_TOKEN_BASE64?: string;
  GOOGLE_CALENDAR_ID?: string;
  GMAIL_QUERY?: string;
  GMAIL_MAX?: string;
  IMPORTANT_SENDERS?: string;
  NOTION_TASK_DATABASE_ID?: string;
  NOTION_DONE_VALUES?: string;
  DAYS_AHEAD?: string;
  TZ?: string;
  SLACK_USER_ID?: string;
  SLACK_FALLBACK_CHANNEL?: string;
}

// HTTP handler for Cloudflare Workers
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
        },
      });
    }

    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405 });
    }

    try {
      const body = await request.json();
      const { method, params } = body;

      let result;
      if (method === "tools/list") {
        result = {
          tools: [
            getCalendarEventsTool.definition,
            getGmailMessagesTool.definition,
            getNotionTasksTool.definition,
            generateVoiceScriptTool.definition,
            synthesizeSpeechTool.definition,
            postToSlackTool.definition,
            uploadFileToSlackTool.definition,
          ],
        };
      } else if (method === "tools/call") {
        const toolName = params.name;
        const toolArgs = params.arguments || {};

        // Route to appropriate tool handler
        switch (toolName) {
          case "get_calendar_events":
            result = await getCalendarEventsTool.handler(toolArgs, env);
            break;
          case "get_gmail_messages":
            result = await getGmailMessagesTool.handler(toolArgs, env);
            break;
          case "get_notion_tasks":
            result = await getNotionTasksTool.handler(toolArgs, env);
            break;
          case "generate_voice_script":
            result = await generateVoiceScriptTool.handler(toolArgs, env);
            break;
          case "synthesize_speech":
            result = await synthesizeSpeechTool.handler(toolArgs, env);
            break;
          case "post_to_slack":
            result = await postToSlackTool.handler(toolArgs, env);
            break;
          case "upload_file_to_slack":
            result = await uploadFileToSlackTool.handler(toolArgs, env);
            break;
          default:
            return new Response(
              JSON.stringify({
                error: {
                  code: ErrorCode.MethodNotFound,
                  message: `Unknown tool: ${toolName}`,
                },
              }),
              { status: 404, headers: { "Content-Type": "application/json" } }
            );
        }
      } else {
        return new Response(
          JSON.stringify({ error: `Unknown method: ${method}` }),
          { status: 400, headers: { "Content-Type": "application/json" } }
        );
      }

      return new Response(JSON.stringify({ result }), {
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      });
    } catch (error: any) {
      return new Response(
        JSON.stringify({
          error: {
            code: -1,
            message: error.message || "Internal server error",
          },
        }),
        {
          status: 500,
          headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
          },
        }
      );
    }
  },
};

