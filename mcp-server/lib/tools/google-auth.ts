interface Env {
  GOOGLE_TOKEN_BASE64?: string;
  GOOGLE_OAUTH_CLIENT_ID?: string;
  GOOGLE_OAUTH_CLIENT_SECRET?: string;
}

export async function getGoogleAccessToken(env: Env): Promise<string> {
  // Handle Google OAuth token
  // Option 1: Use base64 encoded token.json
  if (env.GOOGLE_TOKEN_BASE64) {
    // Decode base64 in Node.js/Vercel
    const tokenBytes = Uint8Array.from(atob(env.GOOGLE_TOKEN_BASE64), (c) => c.charCodeAt(0));
    const tokenStr = new TextDecoder().decode(tokenBytes);
    const tokenJson = JSON.parse(tokenStr);
    
    // Handle different token.json formats
    // Some have "token", others have "access_token"
    const accessToken = tokenJson.access_token || tokenJson.token;
    
    // Check if token is expired and refresh if needed
    // Handle both expiry_date (number) and expiry (ISO string) formats
    let isExpired = false;
    if (tokenJson.expiry_date) {
      // expiry_date is a number (milliseconds since epoch)
      isExpired = Date.now() >= tokenJson.expiry_date;
    } else if (tokenJson.expiry) {
      // expiry is an ISO string
      isExpired = Date.now() >= new Date(tokenJson.expiry).getTime();
    }
    
    // Always try to refresh if we have a refresh_token (tokens expire after 1 hour)
    // This ensures we always use a fresh token
    if (tokenJson.refresh_token && (isExpired || !accessToken)) {
      // Use env vars if available, otherwise fall back to values from token.json
      const clientId = env.GOOGLE_OAUTH_CLIENT_ID || tokenJson.client_id;
      const clientSecret = env.GOOGLE_OAUTH_CLIENT_SECRET || tokenJson.client_secret;
      
      if (!clientId || !clientSecret) {
        throw new Error('GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET are required for token refresh (set in Vercel env vars or include in token.json)');
      }
      
      // Refresh token using OAuth2 client
      const response = await fetch('https://oauth2.googleapis.com/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          client_id: clientId,
          client_secret: clientSecret,
          refresh_token: tokenJson.refresh_token,
          grant_type: 'refresh_token',
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(`Failed to refresh token: ${response.statusText} - ${JSON.stringify(errorData)}`);
      }
      
      const refreshed = await response.json();
      if (refreshed.error) {
        throw new Error(`Failed to refresh token: ${refreshed.error} - ${refreshed.error_description || ''}`);
      }
      
      if (!refreshed.access_token) {
        throw new Error('No access_token in refresh response');
      }
      
      return refreshed.access_token;
    }
    
    if (!accessToken) {
      throw new Error('No access_token or token in token.json and no refresh_token available');
    }
    
    return accessToken;
  }
  throw new Error('Google OAuth token not configured');
}

