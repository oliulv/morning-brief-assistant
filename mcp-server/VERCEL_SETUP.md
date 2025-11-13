# Vercel Deployment Troubleshooting

## Common 404 Issues

If you're getting 404 errors, check these:

### 1. Root Directory Setting

**CRITICAL**: In Vercel project settings, make sure:
- Go to **Settings** → **General**
- Under **Root Directory**, set it to: `mcp-server`
- If it's set to `/` or empty, Vercel won't find your Next.js app!

### 2. Check Deployment Logs

1. Go to your Vercel project
2. Click on **Deployments** tab
3. Click on the latest deployment
4. Check the **Build Logs** for errors

Common build errors:
- Missing dependencies (should be fixed now with React added)
- TypeScript errors
- Missing environment variables (won't cause 404, but will cause runtime errors)

### 3. Verify the Route Exists

After deployment, test:
```bash
curl -X POST https://your-project.vercel.app/api/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list", "params": {}}'
```

Should return JSON with tools list, not 404.

### 4. Test Locally First

Before deploying, test locally:
```bash
cd mcp-server
npm install
npm run dev
```

Then test:
```bash
curl -X POST http://localhost:3000/api/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list", "params": {}}'
```

If local works but Vercel doesn't, it's a deployment configuration issue.

### 5. Re-deploy After Fixes

After fixing package.json or adding React:
1. Commit changes
2. Push to GitHub (if connected)
3. Or manually redeploy in Vercel dashboard

## Quick Fix Checklist

- [ ] Root Directory set to `mcp-server` in Vercel settings
- [ ] React and react-dom added to dependencies (✅ done)
- [ ] Build succeeds (check deployment logs)
- [ ] Environment variables set in Vercel
- [ ] Route file exists at `app/api/mcp/route.ts` (✅ exists)

