import { Env } from "../index.js";
import { getGoogleAccessToken } from "./google-auth.js";

interface CalendarEvent {
  id: string;
  title: string;
  start_iso: string;
  end_iso: string;
  all_day: boolean;
  location?: string;
  meeting_link?: string;
}

export const getCalendarEventsTool = {
  definition: {
    name: "get_calendar_events",
    description: "Fetch calendar events from Google Calendar for a time range",
    inputSchema: {
      type: "object",
      properties: {
        calendar_id: {
          type: "string",
          description: "Google Calendar ID (default: 'primary')",
        },
        time_min: {
          type: "string",
          description: "Start time in ISO 8601 format",
        },
        time_max: {
          type: "string",
          description: "End time in ISO 8601 format",
        },
      },
      required: ["time_min", "time_max"],
    },
  },
  handler: async (args: any, env: Env): Promise<{ content: Array<{ type: string; text: string }> }> => {
    try {
      const calendarId = args.calendar_id || env.GOOGLE_CALENDAR_ID || "primary";
      const timeMin = args.time_min;
      const timeMax = args.time_max;

      const accessToken = await getGoogleAccessToken(env);

      const url = new URL(`https://www.googleapis.com/calendar/v3/calendars/${encodeURIComponent(calendarId)}/events`);
      url.searchParams.set("timeMin", timeMin);
      url.searchParams.set("timeMax", timeMax);
      url.searchParams.set("singleEvents", "true");
      url.searchParams.set("orderBy", "startTime");

      const response = await fetch(url.toString(), {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Google Calendar API error: ${response.statusText}`);
      }

      const data = await response.json();
      const items = data.items || [];

      const events: CalendarEvent[] = items.map((e: any) => {
        const start = e.start || {};
        const end = e.end || {};
        const startIso = start.dateTime || `${start.date}T00:00:00`;
        const endIso = end.dateTime || `${end.date}T00:00:00`;
        const allDay = !start.dateTime;

        let meetingLink: string | undefined;
        const hangoutLink = e.hangoutLink;
        if (hangoutLink) {
          meetingLink = hangoutLink;
        } else {
          const conference = e.conferenceData?.entryPoints || [];
          for (const ep of conference) {
            if (ep.uri) {
              meetingLink = ep.uri;
              break;
            }
          }
        }

        return {
          id: e.id || "",
          title: e.summary || "(No title)",
          start_iso: startIso,
          end_iso: endIso,
          all_day: allDay,
          location: e.location || undefined,
          meeting_link: meetingLink,
        };
      });

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(events),
          },
        ],
      };
    } catch (error: any) {
      throw new Error(`Failed to fetch calendar events: ${error.message}`);
    }
  },
};

