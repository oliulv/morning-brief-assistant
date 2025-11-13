import { Env } from "../index.js";
import { getGoogleAccessToken } from "./google-auth.js";

interface Email {
  id: string;
  thread_id?: string;
  from_name?: string;
  from_email?: string;
  subject?: string;
  snippet?: string;
  date_iso?: string;
}

export const getGmailMessagesTool = {
  definition: {
    name: "get_gmail_messages",
    description: "Search and fetch Gmail messages with optional importance filtering",
    inputSchema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "Gmail search query (e.g., 'label:INBOX newer_than:1d')",
        },
        important_senders: {
          type: "array",
          items: { type: "string" },
          description: "List of important sender email addresses to filter by",
        },
        max_results: {
          type: "number",
          description: "Maximum number of results to return",
        },
      },
      required: ["query"],
    },
  },
  handler: async (args: any, env: Env): Promise<{ content: Array<{ type: string; text: string }> }> => {
    try {
      const query = args.query || env.GMAIL_QUERY || "label:INBOX newer_than:1d";
      const importantSenders = args.important_senders || 
        (env.IMPORTANT_SENDERS ? env.IMPORTANT_SENDERS.split(",").map((s: string) => s.trim()) : []);
      const maxResults = args.max_results || parseInt(env.GMAIL_MAX || "5", 10);

      const accessToken = await getGoogleAccessToken(env);

      // Fetch messages
      const listUrl = new URL("https://gmail.googleapis.com/gmail/v1/users/me/messages");
      listUrl.searchParams.set("q", query);
      listUrl.searchParams.set("maxResults", String(maxResults * 10)); // Fetch more for deduplication

      const listResponse = await fetch(listUrl.toString(), {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (!listResponse.ok) {
        throw new Error(`Gmail API error: ${listResponse.statusText}`);
      }

      const listData = await listResponse.json();
      const messageIds = (listData.messages || []).map((m: any) => m.id);

      // Fetch message metadata
      const emails: Email[] = [];
      const messageMetadata: Map<string, any> = new Map();

      for (const mid of messageIds) {
        try {
          const msgUrl = `https://gmail.googleapis.com/gmail/v1/users/me/messages/${mid}?format=metadata&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=Date`;
          const msgResponse = await fetch(msgUrl, {
            headers: {
              Authorization: `Bearer ${accessToken}`,
            },
          });

          if (!msgResponse.ok) continue;

          const msg = await msgResponse.json();
          const headers = (msg.payload?.headers || []).reduce((acc: any, h: any) => {
            acc[h.name.toLowerCase()] = h.value;
            return acc;
          }, {});

          const fromHeader = headers.from || "";
          let fromName: string | undefined;
          let fromEmail: string | undefined;

          if (fromHeader.includes("<") && fromHeader.includes(">")) {
            const namePart = fromHeader.split("<")[0].trim().replace(/^"|"$/g, "");
            const emailPart = fromHeader.split("<")[1].split(">")[0].trim();
            fromName = namePart || undefined;
            fromEmail = emailPart || undefined;
          } else {
            fromEmail = fromHeader || undefined;
          }

          const email: Email = {
            id: mid,
            thread_id: msg.threadId,
            from_name: fromName,
            from_email: fromEmail,
            subject: headers.subject || "(No subject)",
            snippet: (msg.snippet || "").trim(),
            date_iso: headers.date,
          };

          emails.push(email);
          messageMetadata.set(mid, {
            email,
            internal_date: parseInt(msg.internalDate || "0", 10),
            labels: msg.labelIds || [],
          });
        } catch (e) {
          // Skip failed messages
          continue;
        }
      }

      // Deduplicate by thread_id
      const threadToEmail = new Map<string, Email>();
      const threadToMetadata = new Map<string, any>();

      for (const [mid, metadata] of messageMetadata.entries()) {
        const email = metadata.email;
        const threadId = email.thread_id || mid;
        const internalDate = metadata.internal_date;

        if (!threadToMetadata.has(threadId) || internalDate > threadToMetadata.get(threadId).internal_date) {
          threadToEmail.set(threadId, email);
          threadToMetadata.set(threadId, metadata);
        }
      }

      const uniqueThreads = Array.from(threadToEmail.values());

      // Apply importance filter if configured
      let important: Email[] = [];
      if (importantSenders.length > 0) {
        const senders = new Set(importantSenders.map((s: string) => s.toLowerCase()));
        important = uniqueThreads.filter((e) => e.from_email && senders.has(e.from_email.toLowerCase()));
      }

      // If no important senders matched or none configured, use all threads
      if (important.length === 0) {
        important = uniqueThreads;
      }

      // Sort by internal date (most recent first) and limit
      const sorted = important
        .sort((a, b) => {
          const aDate = messageMetadata.get(a.id)?.internal_date || 0;
          const bDate = messageMetadata.get(b.id)?.internal_date || 0;
          return bDate - aDate;
        })
        .slice(0, maxResults);

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(sorted),
          },
        ],
      };
    } catch (error: any) {
      throw new Error(`Failed to fetch Gmail messages: ${error.message}`);
    }
  },
};

