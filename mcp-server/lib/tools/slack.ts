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
      throw new Error(`Failed to get Slack channel ID: ${dmData.error || 'Unknown error'}`);
    }

    const channelId = dmData.channel.id;

    // Decode base64 file data
    const fileBuffer = Buffer.from(args.file_data, 'base64');
    const fileSize = fileBuffer.length;

    // Step 1: Get upload URL from Slack
    const getUrlResponse = await fetch('https://slack.com/api/files.getUploadURLExternal', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        filename: args.filename,
        length: fileSize,
      }),
    });

    const urlData = await getUrlResponse.json();
    if (!urlData.ok) {
      throw new Error(`Failed to get upload URL: ${urlData.error || 'Unknown error'}`);
    }

    // Step 2: Upload file to the provided URL
    const uploadResponse = await fetch(urlData.upload_url, {
      method: 'POST',
      body: fileBuffer,
    });

    if (!uploadResponse.ok) {
      throw new Error(`Failed to upload file: ${uploadResponse.statusText}`);
    }

    // Step 3: Complete the upload
    const completeResponse = await fetch('https://slack.com/api/files.completeUploadExternal', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        files: [
          {
            id: urlData.file_id,
            title: args.title || args.filename,
          },
        ],
        channel_id: channelId,
        initial_comment: args.initial_comment || '',
      }),
    });

    const completeData = await completeResponse.json();
    if (!completeData.ok) {
      throw new Error(`Failed to complete upload: ${completeData.error || 'Unknown error'}`);
    }

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            success: true,
            file_id: completeData.files?.[0]?.id || urlData.file_id,
          }),
        },
      ],
    };
  } catch (error: any) {
    throw new Error(`Failed to upload file to Slack: ${error.message}`);
  }
}

