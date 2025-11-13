interface Env {
  ELEVENLABS_API_KEY?: string;
  ELEVENLABS_VOICE_ID?: string;
  ELEVENLABS_MODEL_ID?: string;
}

export async function synthesizeSpeech(
  args: { text: string; voice_id?: string; model_id?: string },
  env: Env,
): Promise<{ content: Array<{ type: string; data: string; mimeType: string }> }> {
  try {
    const apiKey = env.ELEVENLABS_API_KEY;
    if (!apiKey) {
      throw new Error('ElevenLabs API key not configured');
    }

    const text = args.text;
    const voiceId = args.voice_id || env.ELEVENLABS_VOICE_ID;
    const modelId = args.model_id || env.ELEVENLABS_MODEL_ID || 'eleven_multilingual_v2';

    if (!voiceId) {
      throw new Error('ElevenLabs voice ID not configured');
    }

    // Preprocess text to speed up speech
    const textFast = text.replace(/\//g, ' and ').replace(/ — /g, ', ').replace(/ → /g, ', ');

    const response = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`, {
      method: 'POST',
      headers: {
        'xi-api-key': apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text: textFast,
        model_id: modelId,
        voice_settings: {
          stability: 0.4,
          similarity_boost: 0.75,
        },
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`ElevenLabs API error: ${response.statusText} - ${errorText}`);
    }

    const audioBuffer = await response.arrayBuffer();
    // Convert ArrayBuffer to base64 in Node.js/Vercel
    // Use chunked approach for large files
    const bytes = new Uint8Array(audioBuffer);
    let binary = '';
    const chunkSize = 8192;
    for (let i = 0; i < bytes.length; i += chunkSize) {
      const chunk = bytes.subarray(i, i + chunkSize);
      binary += String.fromCharCode(...chunk);
    }
    // Use btoa for base64 encoding (available in Node.js 16+)
    const base64Audio = btoa(binary);

    return {
      content: [
        {
          type: 'data',
          data: base64Audio,
          mimeType: 'audio/mpeg',
        },
      ],
    };
  } catch (error: any) {
    throw new Error(`Failed to synthesize speech: ${error.message}`);
  }
}

