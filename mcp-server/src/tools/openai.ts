import { Env } from "../index.js";

export const generateVoiceScriptTool = {
  definition: {
    name: "generate_voice_script",
    description: "Generate a natural voice script from structured data using OpenAI",
    inputSchema: {
      type: "object",
      properties: {
        tz: {
          type: "string",
          description: "Timezone (e.g., 'Europe/Oslo')",
        },
        user_name: {
          type: "string",
          description: "User's name or nickname",
        },
        today_events: {
          type: "array",
          items: { type: "object" },
          description: "Array of today's calendar events",
        },
        tasks_today: {
          type: "array",
          items: { type: "object" },
          description: "Array of today's tasks",
        },
        emails: {
          type: "array",
          items: { type: "object" },
          description: "Array of recent emails",
        },
      },
      required: ["tz", "user_name"],
    },
  },
  handler: async (args: any, env: Env): Promise<{ content: Array<{ type: string; text: string }> }> => {
    try {
      const apiKey = env.OPENAI_API_KEY;
      if (!apiKey) {
        throw new Error("OpenAI API key not configured");
      }

      const model = env.OPENAI_MODEL || "gpt-4o-mini";
      const tz = args.tz || env.TZ || "Europe/Oslo";
      const userName = args.user_name || "Oliver";
      const nickname = userName.toLowerCase() === "oliver" ? "GOAT" : userName;

      const todayEvents = args.today_events || [];
      const tasksToday = (args.tasks_today || []).filter((t: any) => !t.done);
      const emails = args.emails || [];

      const systemPrompt = `
You are a world-class personal assistant creating a 45–70 second VOICE NOTE.
Speak to the user as "${nickname}".

STYLE:
- Warm, crisp, competent; a hint of playful wit.
- Natural speech only: no headings, no bullets, no emoji, no dictation artifacts.
- 24-hour times for ${tz} (e.g., 09:05, 16:30). Say the day and date up front.
- Don't read raw URLs; say "Zoom link", "calendar link", or "location link".
- End with ONE original, funny but tasteful one-liner (not a famous quote, 6–14 words).

INTELLIGENCE:
- CRITICAL: Group ALL Notion tasks by their Area property. Say "For [Area name], you have: [list tasks]". If area is null/empty, group those as "Other tasks: [list]".
- Do NOT mention dates for tasks due today - they're due TODAY, no need to say the date.
- Skip any tasks with done=true.
- Notice back-to-back events; suggest a travel/water/coffee buffer if sensible.
- Collapse noise: keep top 2–3 from Emails unless empty.
- If a section is empty, acknowledge briefly and move on.
- Prefer specifics that matter (time, title, who, where) over generic filler.
- DO NOT mention upcoming events or tasks - only focus on TODAY.

LENGTH:
- Target 45–70 seconds. Keep sentences short and flowing.
`;

      const userPayload = {
        user_nickname: nickname,
        timezone: tz,
        today_events: todayEvents,
        tasks_today: tasksToday,
        emails_top: emails.slice(0, 3),
        instructions: {
          calendar: "Say 'Today you have…' then list briefly with 24-hour times and titles; include location/link only if useful.",
          back_to_back: "If two events are adjacent or locations differ, suggest a short buffer.",
          tasks: "MANDATORY: Group ALL tasks by their 'area' field. Say 'For [Area name], you have: [task 1], [task 2]'. If area is null/empty, say 'Other tasks: [list]'. Do NOT mention dates for tasks due today - they're due TODAY. Skip tasks with done=true. Never mention upcoming tasks or events.",
          emails: "Name top 2–3 senders + brief subject gist.",
          tone: "Natural voice, slight humor, never overdo it. Focus ONLY on today - no future references.",
        },
      };

      const response = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model,
          temperature: 0.35,
          messages: [
            { role: "system", content: systemPrompt.trim() },
            { role: "user", content: JSON.stringify(userPayload) },
          ],
        }),
      });

      if (!response.ok) {
        throw new Error(`OpenAI API error: ${response.statusText}`);
      }

      const data = await response.json();
      const voiceText = data.choices?.[0]?.message?.content?.trim() || "";

      // Soft guardrail for length
      const maxChars = 1200;
      if (voiceText.length > maxChars) {
        const parts = voiceText.split(". ");
        const head = parts.slice(0, 6).join(". ");
        const tail = parts[parts.length - 1];
        const trimmed = `${head}. … ${tail}`.trim();
        return {
          content: [
            {
              type: "text",
              text: trimmed.endsWith(".") ? trimmed : trimmed + ".",
            },
          ],
        };
      }

      return {
        content: [
          {
            type: "text",
            text: voiceText,
          },
        ],
      };
    } catch (error: any) {
      throw new Error(`Failed to generate voice script: ${error.message}`);
    }
  },
};

