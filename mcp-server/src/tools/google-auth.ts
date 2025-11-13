import { Env } from "../index.js";

export async function getGoogleAccessToken(env: Env): Promise<string> {
  // Handle Google OAuth token
  // Option 1: Use base64 encoded token.json
  if (env.GOOGLE_TOKEN_BASE64) {
    // Decode base64 in Cloudflare Workers
    const tokenBytes = Uint8Array.from(atob(env.GOOGLE_TOKEN_BASE64), c => c.charCodeAt(0));
    const tokenStr = new TextDecoder().decode(tokenBytes);
    const tokenJson = JSON.parse(tokenStr);
    // Check if token is expired and refresh if needed
    if (tokenJson.expiry_date && Date.now() >= tokenJson.expiry_date) {
      // Refresh token using OAuth2 client
      const response = await fetch("https://oauth2.googleapis.com/token", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          client_id: env.GOOGLE_OAUTH_CLIENT_ID || "",
          client_secret: env.GOOGLE_OAUTH_CLIENT_SECRET || "",
          refresh_token: tokenJson.refresh_token,
          grant_type: "refresh_token",
        }),
      });
      const refreshed = await response.json();
      if (refreshed.error) {
        throw new Error(`Failed to refresh token: ${refreshed.error}`);
      }
      return refreshed.access_token;
    }
    return tokenJson.access_token;
  }
  throw new Error("Google OAuth token not configured");
}

