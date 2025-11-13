import React from 'react';

export default function Home() {
  return (
    <div style={{ padding: '2rem', fontFamily: 'system-ui' }}>
      <h1>Morning Brief MCP Server</h1>
      <p>MCP server is running. API endpoint: <code>/api/mcp</code></p>
      <p>Test with:</p>
      <pre style={{ background: '#f5f5f5', padding: '1rem', borderRadius: '4px' }}>
        {`curl -X POST ${process.env.VERCEL_URL || 'http://localhost:3000'}/api/mcp \\
  -H "Content-Type: application/json" \\
  -d '{"method": "tools/list", "params": {}}'`}
      </pre>
    </div>
  );
}

