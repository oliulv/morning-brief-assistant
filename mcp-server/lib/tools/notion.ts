interface Task {
  id: string;
  name: string;
  due_iso?: string;
  area?: string;
  done?: boolean;
  url?: string;
}

interface Env {
  NOTION_API_KEY?: string;
  NOTION_TASK_DATABASE_ID?: string;
  NOTION_DONE_VALUES?: string;
  DAYS_AHEAD?: string;
  TZ?: string;
}

export async function getNotionTasks(
  args: {
    api_key?: string;
    database_id?: string;
    today_start_iso: string;
    today_end_iso: string;
    days_ahead?: number;
    tz?: string;
  },
  env: Env,
): Promise<{ content: Array<{ type: string; text: string }> }> {
  try {
    const apiKey = args.api_key || env.NOTION_API_KEY;
    const databaseId = args.database_id || env.NOTION_TASK_DATABASE_ID;
    const todayStart = args.today_start_iso;
    const todayEnd = args.today_end_iso;
    const daysAhead = args.days_ahead || parseInt(env.DAYS_AHEAD || '14', 10);
    const tz = args.tz || env.TZ || 'Europe/Oslo';

    if (!apiKey || !databaseId) {
      throw new Error('Notion API key and database ID are required');
    }

    const notionHeaders = {
      Authorization: `Bearer ${apiKey}`,
      'Notion-Version': '2022-06-28',
      'Content-Type': 'application/json',
    };

    // Get database properties to find due date and status fields
    const dbUrl = `https://api.notion.com/v1/databases/${databaseId}`;
    const dbResponse = await fetch(dbUrl, {
      headers: notionHeaders,
    });

    if (!dbResponse.ok) {
      throw new Error(`Notion API error: ${dbResponse.statusText}`);
    }

    const db = await dbResponse.json();
    const properties = db.properties || {};

    // Find due date property
    let dueProp = 'Due';
    for (const cand of ['Due', 'Due date', 'Due Date', 'Date']) {
      if (properties[cand]?.type === 'date') {
        dueProp = cand;
        break;
      }
    }

    // Find status/done property
    let statusProp: string | undefined;
    const doneValues = new Set(
      (env.NOTION_DONE_VALUES || 'Done')
        .split(',')
        .map((v: string) => v.trim())
        .filter(Boolean),
    );

    for (const [name, prop] of Object.entries(properties)) {
      const propType = (prop as any).type;
      if ((propType === 'status' || propType === 'select') && name.toLowerCase() === 'done') {
        statusProp = name;
        break;
      }
    }

    // Build filters
    const buildFilter = (dateFilter: any) => {
      const parts = [dateFilter];
      if (statusProp && doneValues.size > 0) {
        if (doneValues.size === 1) {
          parts.push({
            property: statusProp,
            status: { does_not_equal: Array.from(doneValues)[0] },
          });
        } else {
          parts.push({
            or: Array.from(doneValues).map((dv) => ({
              property: statusProp,
              status: { does_not_equal: dv },
            })),
          });
        }
      }
      return { and: parts };
    };

    // Query tasks
    const queryUrl = `https://api.notion.com/v1/databases/${databaseId}/query`;

    // Overdue tasks
    const overdueFilter = buildFilter({
      property: dueProp,
      date: { before: todayStart },
    });

    // Today's tasks
    const todayFilter = buildFilter({
      and: [
        { property: dueProp, date: { on_or_after: todayStart } },
        { property: dueProp, date: { on_or_before: todayEnd } },
      ],
    });

    // Upcoming tasks
    const futureEnd = new Date(Date.now() + daysAhead * 24 * 60 * 60 * 1000).toISOString();
    const upcomingFilter = buildFilter({
      and: [
        { property: dueProp, date: { after: todayEnd } },
        { property: dueProp, date: { before: futureEnd } },
      ],
    });

    const [overdueRes, todayRes, upcomingRes] = await Promise.all([
      fetch(queryUrl, {
        method: 'POST',
        headers: notionHeaders,
        body: JSON.stringify({
          filter: overdueFilter,
          sorts: [{ property: dueProp, direction: 'ascending' }],
          page_size: 100,
        }),
      }),
      fetch(queryUrl, {
        method: 'POST',
        headers: notionHeaders,
        body: JSON.stringify({
          filter: todayFilter,
          sorts: [{ property: dueProp, direction: 'ascending' }],
          page_size: 100,
        }),
      }),
      fetch(queryUrl, {
        method: 'POST',
        headers: notionHeaders,
        body: JSON.stringify({
          filter: upcomingFilter,
          sorts: [{ property: dueProp, direction: 'ascending' }],
          page_size: 100,
        }),
      }),
    ]);

    const [overdueData, todayData, upcomingData] = await Promise.all([
      overdueRes.json(),
      todayRes.json(),
      upcomingRes.json(),
    ]);

    // Convert pages to tasks
    const pageToTask = async (page: any): Promise<Task> => {
      const props = page.properties || {};

      // Find title property
      let titleProp: string | undefined;
      for (const [name, prop] of Object.entries(props)) {
        if ((prop as any).type === 'title') {
          titleProp = name;
          break;
        }
      }

      const nameVal = titleProp
        ? (props[titleProp] as any).title?.map((t: any) => t.plain_text).join('') || page.id
        : page.id;

      // Get due date
      const dueDate = props[dueProp]?.date?.start;

      // Get area (relation property)
      let area: string | undefined;
      for (const [name, prop] of Object.entries(props)) {
        if ((prop as any).type === 'relation' && name.toLowerCase() === 'area') {
          const relations = (prop as any).relation || [];
          if (relations.length > 0) {
            // Fetch related page to get title
            try {
              const relatedUrl = `https://api.notion.com/v1/pages/${relations[0].id}`;
              const relatedRes = await fetch(relatedUrl, {
                headers: notionHeaders,
              });
              if (relatedRes.ok) {
                const relatedPage = await relatedRes.json();
                const relatedProps = relatedPage.properties || {};
                for (const [rName, rProp] of Object.entries(relatedProps)) {
                  if ((rProp as any).type === 'title') {
                    area = (rProp as any).title?.map((t: any) => t.plain_text).join('');
                    break;
                  }
                }
              }
            } catch (e) {
              // Skip area if fetch fails
            }
          }
          break;
        }
      }

      // Get done status
      let done = false;
      if (statusProp && props[statusProp]) {
        const statusData = props[statusProp];
        if (statusData.type === 'status') {
          const statusName = statusData.status?.name || '';
          done = doneValues.has(statusName);
        } else if (statusData.type === 'select') {
          const selectName = statusData.select?.name || '';
          done = doneValues.has(selectName);
        }
      }

      return {
        id: page.id,
        name: nameVal || '(Untitled)',
        due_iso: dueDate,
        area,
        done,
        url: page.url,
      };
    };

    const [overdueTasks, todayTasks, upcomingTasks] = await Promise.all([
      Promise.all((overdueData.results || []).map(pageToTask)),
      Promise.all((todayData.results || []).map(pageToTask)),
      Promise.all((upcomingData.results || []).map(pageToTask)),
    ]);

    // Filter out done tasks
    const filterDone = (tasks: Task[]) => tasks.filter((t) => !t.done);

    const result = {
      today: filterDone(todayTasks),
      overdue: filterDone(overdueTasks),
      upcoming: filterDone(upcomingTasks),
    };

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(result),
        },
      ],
    };
  } catch (error: any) {
    throw new Error(`Failed to fetch Notion tasks: ${error.message}`);
  }
}

