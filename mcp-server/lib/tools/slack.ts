interface Env {
  SLACK_BOT_TOKEN?: string;
  SLACK_USER_ID?: string;
  SLACK_FALLBACK_CHANNEL?: string;
}

export async function postToSlack(
  args: { user_id?: string; channel?: string; text: string },
  env: Env,
): Promise<{ content: Array<{ type: string; text: string }> }> {
  try {
    const token = env.SLACK_BOT_TOKEN;
    if (!token) {
      throw new Error('Slack bot token not configured');
    }

    const text = args.text;
    const userId = args.user_id || env.SLACK_USER_ID;
    const channel = args.channel || env.SLACK_FALLBACK_CHANNEL;

    let channelId: string | undefined;

    // Try DM first if user_id provided
    if (userId) {
      try {
        const dmResponse = await fetch('https://slack.com/api/conversations.open', {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
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
      channelId = channel.startsWith('#') ? channel.slice(1) : channel;
    }

    if (!channelId) {
      throw new Error('No valid Slack channel or user ID provided');
    }

    const postResponse = await fetch('https://slack.com/api/chat.postMessage', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        channel: channelId,
        text,
      }),
    });

    const postData = await postResponse.json();

    if (!postData.ok) {
      throw new Error(`Slack API error: ${postData.error || 'Unknown error'}`);
    }

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ success: true, channel: channelId }),
        },
      ],
    };
  } catch (error: any) {
    throw new Error(`Failed to post to Slack: ${error.message}`);
  }
}

export async function uploadFileToSlack(
  args: {
    user_id: string;
    file_data: string;
    filename: string;
    title?: string;
    initial_comment?: string;
  },
  env: Env,
): Promise<{ content: Array<{ type: string; text: string }> }> {
  try {
    const token = env.SLACK_BOT_TOKEN;
    if (!token) {
      throw new Error('Slack bot token not configured');
    }

    const userId = args.user_id || env.SLACK_USER_ID;
    if (!userId) {
      throw new Error('Slack user ID not provided');
    }

    // Open DM channel
    const dmResponse = await fetch('https://slack.com/api/conversations.open', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ users: userId }),
    });

    if (!dmResponse.ok) {
      throw new Error('Failed to open Slack DM');
    }

    const dmData = await dmResponse.json();
    if (!dmData.ok || !dmData.channel?.id) {
      throw new Error('Failed to get Slack channel ID');
    }

    const channelId = dmData.channel.id;

    // Decode base64 file data in Node.js/Vercel
    const fileBytes = Uint8Array.from(atob(args.file_data), (c) => c.charCodeAt(0));

    // Use files.uploadV2 (newer API) or fall back to posting message with file
    // files.upload is deprecated, so we'll use files.uploadV2
    const formData = new FormData();
    formData.append('channel_id', channelId);
    formData.append('file', new Blob([fileBytes]), args.filename);
    formData.append('filename', args.filename);
    if (args.title) {
      formData.append('title', args.title);
    }
    if (args.initial_comment) {
      formData.append('initial_comment', args.initial_comment);
    }

    const uploadResponse = await fetch('https://slack.com/api/files.uploadV2', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    const uploadData = await uploadResponse.json();

    // If uploadV2 fails for any reason, fallback to legacy files.upload
    // uploadV2 might not be available for all workspaces
    if (!uploadData.ok) {
      // Fallback to legacy files.upload (even though deprecated, it still works)
      const legacyFormData = new FormData();
      legacyFormData.append('channels', channelId);
      legacyFormData.append('file', new Blob([fileBytes]), args.filename);
      legacyFormData.append('title', args.title || args.filename);
      if (args.initial_comment) {
        legacyFormData.append('initial_comment', args.initial_comment);
      }

      const legacyResponse = await fetch('https://slack.com/api/files.upload', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: legacyFormData,
      });

      const legacyData = await legacyResponse.json();
      if (!legacyData.ok) {
        // Even if deprecated, it might still work - check if file was uploaded despite error
        // Slack may return method_deprecated as error but still upload the file
        if ((legacyData.error === 'method_deprecated' || legacyData.warning === 'method_deprecated') && legacyData.file) {
          // It worked despite deprecation warning/error
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify({ success: true, file_id: legacyData.file.id }),
              },
            ],
          };
        }
        throw new Error(`Slack API error: ${legacyData.error || 'Unknown error'}`);
      }
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({ success: true, file_id: legacyData.file?.id }),
          },
        ],
      };
    }

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({ success: true, file_id: uploadData.file?.id || uploadData.id }),
        },
      ],
    };
  } catch (error: any) {
    throw new Error(`Failed to upload file to Slack: ${error.message}`);
  }
}

