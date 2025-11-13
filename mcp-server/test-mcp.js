// Simple Node.js test script for MCP server
// Usage: node test-mcp.js [url]

const url = process.argv[2] || 'http://localhost:3000/api/mcp';

async function testMCP() {
  console.log(`Testing MCP server at: ${url}\n`);

  // Test 1: List tools
  console.log('=== Test 1: List Tools ===');
  try {
    const listResponse = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        method: 'tools/list',
        params: {},
      }),
    });
    const listData = await listResponse.json();
    console.log('Tools available:', listData.result?.tools?.length || 0);
    if (listData.result?.tools) {
      listData.result.tools.forEach((tool) => {
        console.log(`  - ${tool.name}: ${tool.description}`);
      });
    }
    console.log('');
  } catch (error) {
    console.error('Error listing tools:', error.message);
  }

  // Test 2: Call a tool (example - adjust based on your env vars)
  console.log('=== Test 2: Call Tool (Example) ===');
  console.log('To test actual tools, you need environment variables set.');
  console.log('Example call:');
  console.log(`
  curl -X POST "${url}" \\
    -H "Content-Type: application/json" \\
    -d '{
      "method": "tools/call",
      "params": {
        "name": "get_calendar_events",
        "arguments": {
          "time_min": "2024-01-01T00:00:00Z",
          "time_max": "2024-01-02T00:00:00Z"
        }
      }
    }'
  `);
}

testMCP().catch(console.error);

