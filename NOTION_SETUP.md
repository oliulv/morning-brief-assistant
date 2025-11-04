# Notion Setup for Area Relations

## The Problem

If your tasks have an "Area" relation property but the relation array is empty in the API response, you need to:

1. **Ensure your Notion integration has access to the Areas database**
2. **Share the Areas database with your integration**

## Steps to Fix

### 1. Check if Tasks Have Areas Assigned

In Notion, open a task that should have an Area. Check if the Area field is actually populated. If it's empty in Notion UI, it will be empty in the API.

### 2. Grant Access to Areas Database

1. Go to your Areas database in Notion
2. Click the "..." menu in the top right
3. Click "Add connections" or "Connections"
4. Search for your integration name (the one you created for this bot)
5. Select it and grant access

### 3. Verify Access

Run the test script:
```bash
python -m src.debug.test_notion_area
```

You should now see:
- Relation array length > 0 for tasks with Areas
- Area names being fetched successfully

## Why This Happens

Notion relations work like this:
- **Relation IDs**: Can be seen even without access to the related database
- **Relation names/content**: Requires access to the related database

If the relation array is empty, it means either:
1. The task doesn't have an Area assigned (check in Notion UI)
2. The integration doesn't have permission to see the relation (rare, but possible)

## Configuration

You don't need to configure anything special in `.env` - just ensure the integration has access to both:
- ✅ Your Tasks database (already configured)
- ✅ Your Areas database (needs to be shared)

That's it! Once the Areas database is shared with your integration, the code will automatically fetch area names when it sees relation IDs.

