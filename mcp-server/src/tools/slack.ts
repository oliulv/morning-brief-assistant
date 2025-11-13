import { Env } from "../index.js";

export const postToSlackTool = {
  definition: {
    name: "post_to_slack",
    description: "Post a message to Slack (DM or channel)",
    inputSchema: {
      type: "object",
      properties: {
        user_id: {
          type: "string",
          description: "Slack user ID for DM (optional if channel is provided)",
        },
        channel: {
          type: "string",
          description: "Slack channel name for posting (fallback if user_id fails)",
        },
        text: {
          type: "string",
          description: "Message text to post",
        },
      },
      required: ["text"],
    },
  },
  handler: async (args: any, env: Env): Promise<{ content: Array<{ type: string; text: string }> }> => {
    try {
      const token = env.SLACK_BOT_TOKEN;
      if (!token) {
        throw new Error("Slack bot token not configured");
      }

      const text = args.text;
      const userId = args.user_id || env.SLACK_USER_ID;
      const channel = args.channel || env.SLACK_FALLBACK_CHANNEL;

      let channelId: string | undefined;

      // Try DM first if user_id provided
      if (userId) {
        try {
          const dmResponse = await fetch("https://slack.com/api/conversations.open", {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ users: userId }),
          });

          if (dmResponse.ok) {
            const dmData = await dmResponse.json();
            if (dmData.ok && dmData.channel?.id) {
              channelId = dmData.channel.id;
            }
          }
        } catch (e) {
          // Fall through to channel
        }
      }

      // Fallback to channel if DM failed
      if (!channelId && channel) {
        channelId = channel.startsWith("#") ? channel.slice(1) : channel;
      }

      if (!channelId) {
        throw new Error("No valid Slack channel or user ID provided");
      }

      const postResponse = await fetch("https://slack.com/api/chat.postMessage", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          channel: channelId,
          text,
        }),
      });

      const postData = await postResponse.json();

      if (!postData.ok) {
        throw new Error(`Slack API error: ${postData.error || "Unknown error"}`);
      }

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({ success: true, channel: channelId }),
          },
        ],
      };
    } catch (error: any) {
      throw new Error(`Failed to post to Slack: ${error.message}`);
    }
  },
};

export const uploadFileToSlackTool = {
  definition: {
    name: "upload_file_to_slack",
    description: "Upload a file to Slack (DM or channel)",
    inputSchema: {
      type: "object",
      properties: {
        user_id: {
          type: "string",
          description: "Slack user ID for DM",
        },
        file_data: {
          type: "string",
          description: "Base64-encoded file data",
        },
        filename: {
          type: "string",
          description: "Filename for the upload",
        },
        title: {
          type: "string",
          description: "File title",
        },
        initial_comment: {
          type: "string",
          description: "Initial comment with the file",
        },
      },
      required: ["user_id", "file_data", "filename"],
    },
  },
  handler: async (args: any, env: Env): Promise<{ content: Array<{ type: string; text: string }> }> => {
    try {
      const token = env.SLACK_BOT_TOKEN;
      if (!token) {
        throw new Error("Slack bot token not configured");
      }

      const userId = args.user_id || env.SLACK_USER_ID;
      if (!userId) {
        throw new Error("Slack user ID not provided");
      }

      // Open DM channel
      const dmResponse = await fetch("https://slack.com/api/conversations.open", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ users: userId }),
      });

      if (!dmResponse.ok) {
        throw new Error("Failed to open Slack DM");
      }

      const dmData = await dmResponse.json();
      if (!dmData.ok || !dmData.channel?.id) {
        throw new Error("Failed to get Slack channel ID");
      }

      const channelId = dmData.channel.id;

      // Decode base64 file data in Cloudflare Workers
      const fileBytes = Uint8Array.from(atob(args.file_data), c => c.charCodeAt(0));
      const fileBuffer = fileBytes.buffer;

      // Upload file using multipart form
      const formData = new FormData();
      formData.append("channels", channelId);
      formData.append("file", new Blob([fileBuffer]), args.filename);
      formData.append("title", args.title || args.filename);
      if (args.initial_comment) {
        formData.append("initial_comment", args.initial_comment);
      }

      const uploadResponse = await fetch("https://slack.com/api/files.upload", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const uploadData = await uploadResponse.json();

      if (!uploadData.ok) {
        throw new Error(`Slack API error: ${uploadData.error || "Unknown error"}`);
      }

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({ success: true, file_id: uploadData.file?.id }),
          },
        ],
      };
    } catch (error: any) {
      throw new Error(`Failed to upload file to Slack: ${error.message}`);
    }
  },
};

