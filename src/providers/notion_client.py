from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List, Optional
import os
import requests

import pytz
from notion_client import Client

from src.models.task_models import Task


logger = logging.getLogger(__name__)


def _extract_first_date_property(properties: dict) -> Optional[str]:
    for name, prop in properties.items():
        if prop.get("type") == "date":
            return name
    return None


def _rich_text_to_plain(rt_arr: list) -> str:
    parts = []
    for rt in rt_arr or []:
        txt = (rt.get("plain_text") or "").strip()
        if txt:
            parts.append(txt)
    return "".join(parts)


def _title_to_plain(tl_arr: list) -> str:
    return _rich_text_to_plain(tl_arr)


def _prop_text(properties: dict, key: str) -> Optional[str]:
    prop = properties.get(key)
    if not prop:
        return None
    t = prop.get("type")
    if t == "title":
        return _title_to_plain(prop.get("title", []))
    if t == "rich_text":
        return _rich_text_to_plain(prop.get("rich_text", []))
    if t == "select":
        sel = prop.get("select")
        return sel.get("name") if sel else None
    if t == "relation":
        # For relations, get the first related page name if available
        relation_arr = prop.get("relation", [])
        if relation_arr:
            # We'd need to fetch the page to get its title, but for now return a placeholder
            return None  # Relations need additional API calls
    if t == "multi_select":
        multi_arr = prop.get("multi_select", [])
        if multi_arr:
            return multi_arr[0].get("name") if multi_arr else None
    return None


def _prop_date_iso(properties: dict, key: str) -> Optional[str]:
    prop = properties.get(key)
    if not prop or prop.get("type") != "date":
        return None
    date = prop.get("date") or {}
    if date.get("start"):
        return date["start"]
    return None


def query_tasks(
    api_key: str,
    database_id: str,
    tz_name: str,
    days_ahead: int,
    today_start_iso: str,
    today_end_iso: str,
) -> tuple[List[Task], List[Task], List[Task]]:
    try:
        client = Client(auth=api_key)
        notion_headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

        def query_db(payload: dict) -> dict:
            # Always expand relations to get full relation data (not just IDs)
            if "filter" in payload:
                # Expand relations for Area, Project, etc.
                payload.setdefault("page_size", 100)
            # Prefer SDK, but fall back to raw HTTP if query method is unavailable
            try:
                result = client.databases.query(database_id=database_id, **payload)
                # Note: Relations might need explicit expansion - check if relation data is populated
                return result
            except AttributeError:
                url = f"https://api.notion.com/v1/databases/{database_id}/query"
                resp = requests.post(url, headers=notion_headers, json=payload, timeout=30)
                resp.raise_for_status()
                return resp.json()
        # We try to identify the due date property dynamically
        # by pulling one page and inspecting properties
        db = client.databases.retrieve(database_id=database_id)
        properties = db.get("properties", {})
        logger.info("DEBUG: Database properties from retrieve: %s", list(properties.keys()) if properties else "EMPTY")
        
        # If database properties are empty, fetch a sample page to get properties
        if not properties:
            logger.warning("DEBUG: Database properties empty, fetching sample page to detect properties")
            try:
                sample = query_db({"page_size": 1})
                if sample.get("results"):
                    sample_props = sample["results"][0].get("properties", {})
                    properties = {k: {"type": v.get("type")} for k, v in sample_props.items()}
                    logger.info("DEBUG: Sample page properties: %s", {k: v.get("type") for k, v in sample_props.items()})
            except Exception as e:
                logger.warning("DEBUG: Failed to fetch sample page: %s", e)
        
        due_override = os.getenv("NOTION_DUE_PROPERTY")
        # Done is a STATUS property (Notion's status type), not select!
        status_prop = os.getenv("NOTION_STATUS_PROPERTY")
        logger.info("DEBUG: Initial status_prop from env: %s", status_prop)
        if not status_prop:
            # Auto-detect status property named "Done" or "Status"
            logger.info("DEBUG: Attempting auto-detection, properties available: %s", {k: v.get("type") if isinstance(v, dict) else type(v).__name__ for k, v in properties.items()})
            for prop_name, prop_data in properties.items():
                prop_type = prop_data.get("type") if isinstance(prop_data, dict) else None
                if not prop_type and isinstance(prop_data, dict):
                    # Try to infer type from structure
                    continue
                logger.debug("DEBUG: Checking property '%s' with type '%s'", prop_name, prop_type)
                if prop_type == "status" and prop_name.lower() in ("done", "status"):
                    status_prop = prop_name
                    logger.info("Auto-detected Notion Done status property: %s (type: %s)", status_prop, prop_type)
                    break
            # Fallback to select if status not found
            if not status_prop:
                logger.info("DEBUG: Status type not found, trying select fallback")
                for prop_name, prop_data in properties.items():
                    prop_type = prop_data.get("type") if isinstance(prop_data, dict) else None
                    if prop_type == "select" and prop_name.lower() in ("done", "status"):
                        status_prop = prop_name
                        logger.info("Auto-detected Notion Done as select property: %s", status_prop)
                        break
        
        done_values = {v.strip() for v in (os.getenv("NOTION_DONE_VALUES", "")).split(",") if v.strip()}
        if not done_values and status_prop:
            # Default done values if not set
            done_values = {"Done", "done", "Completed", "completed"}
            
            # Try to get actual status options - first from database, then from sample page
            status_prop_def = None
            if properties and status_prop in properties:
                status_prop_def = properties[status_prop]
            elif not properties:
                # Re-fetch database to get full property definitions including options
                try:
                    db_full = client.databases.retrieve(database_id=database_id)
                    db_props = db_full.get("properties", {})
                    if status_prop in db_props:
                        status_prop_def = db_props[status_prop]
                except Exception as e:
                    logger.debug("Could not re-fetch database for status options: %s", e)
            
            if status_prop_def and isinstance(status_prop_def, dict):
                logger.info("DEBUG: status_prop_def structure: %s", list(status_prop_def.keys()))
                if status_prop_def.get("type") == "status":
                    # Status options are in status_prop_def.status.options
                    status_config = status_prop_def.get("status", {})
                    status_options = status_config.get("options", [])
                    if status_options:
                        all_option_names = []
                        for opt in status_options:
                            opt_name = opt.get("name", "")
                            all_option_names.append(opt_name)
                            opt_name_lower = opt_name.lower()
                            if opt_name_lower in ("done", "completed", "finished", "closed"):
                                done_values.add(opt_name)  # Use exact case
                        logger.info("Notion status options found: %s (added to done_values: %s)", all_option_names, done_values)
                    else:
                        logger.warning("DEBUG: No status options found in status_prop_def.status")
        
        logger.info("Notion detection: status_prop='%s', done_values=%s", status_prop, done_values)
        
        # Legacy checkbox support (but Done is actually a select)
        done_checkbox_prop = os.getenv("NOTION_DONE_CHECKBOX_PROPERTY")
        if done_checkbox_prop:
            for prop_name, prop_data in properties.items():
                if prop_data.get("type") == "checkbox" and prop_name.lower() == done_checkbox_prop.lower():
                    logger.info("Using Notion Done checkbox property: %s", prop_name)
                    break
        due_prop = due_override or None
        for cand in ("Due", "Due date", "Due Date", "Date"):
            if not due_prop and cand in properties and properties[cand].get("type") == "date":
                due_prop = cand
                break
        if not due_prop:
            due_prop = _extract_first_date_property(properties) or "Due"

        # Build status filter to exclude done - Done is a STATUS property!
        status_not_done_filter = None
        if status_prop and done_values:
            # Check if it's status type or select type
            prop_type = None
            if properties and status_prop in properties:
                prop_type = properties.get(status_prop, {}).get("type")
            # If not found in properties, check from sample page we might have seen
            if not prop_type:
                # We know from task properties that 'Done' is type 'status', so default to that
                prop_type = "status"  # Default assumption since we saw it in task properties
            
            if prop_type == "status":
                # Status type uses "status" filter
                if len(done_values) == 1:
                    status_not_done_filter = {"property": status_prop, "status": {"does_not_equal": list(done_values)[0]}}
                else:
                    # Multiple values - use OR of does_not_equal
                    status_not_done_filter = {
                        "or": [{"property": status_prop, "status": {"does_not_equal": dv}} for dv in done_values]
                    }
                logger.info("Notion: Excluding tasks where %s status is in %s", status_prop, done_values)
            else:
                # Select type (fallback)
                if len(done_values) == 1:
                    status_not_done_filter = {"property": status_prop, "select": {"does_not_equal": list(done_values)[0]}}
                else:
                    status_not_done_filter = {
                        "and": [{"property": status_prop, "select": {"does_not_equal": dv}} for dv in done_values]
                    }
                logger.info("Notion: Excluding tasks where %s select is in %s", status_prop, done_values)
        elif status_prop:
            prop_type = None
            if properties and status_prop in properties:
                prop_type = properties.get(status_prop, {}).get("type")
            if not prop_type:
                prop_type = "status"  # Default assumption
            
            if prop_type == "status":
                status_not_done_filter = {"property": status_prop, "status": {"is_not_empty": True}}
            else:
                status_not_done_filter = {"property": status_prop, "select": {"is_not_empty": True}}

        # Legacy checkbox support (but Done is actually a select)
        checkbox_not_done_filter = None
        if done_checkbox_prop:
            checkbox_not_done_filter = {"property": done_checkbox_prop, "checkbox": {"equals": False}}
            logger.info("Notion: Also excluding tasks where %s checkbox is True", done_checkbox_prop)

        # Pull tasks using three filters
        # Overdue: due < today_start
        overdue_and_parts = [
            {"property": due_prop, "date": {"before": today_start_iso}},
        ]
        if status_not_done_filter:
            overdue_and_parts.append(status_not_done_filter)
        if checkbox_not_done_filter:
            overdue_and_parts.append(checkbox_not_done_filter)
        overdue_filter = {"and": overdue_and_parts}
        overdue_sort = [{"property": due_prop, "direction": "ascending"}]

        # Due today: between start and end
        today_and_parts = [
            {"property": due_prop, "date": {"on_or_after": today_start_iso}},
            {"property": due_prop, "date": {"on_or_before": today_end_iso}},
        ]
        if status_not_done_filter:
            today_and_parts.append(status_not_done_filter)
        if checkbox_not_done_filter:
            today_and_parts.append(checkbox_not_done_filter)
        today_filter = {"and": today_and_parts}

        # Upcoming within N days
        tz = pytz.timezone(tz_name)
        now = datetime.now(tz)
        future_end = (now + timedelta(days=days_ahead)).isoformat()
        upcoming_and_parts = [
            {"property": due_prop, "date": {"after": today_end_iso}},
            {"property": due_prop, "date": {"before": future_end}},
        ]
        if status_not_done_filter:
            upcoming_and_parts.append(status_not_done_filter)
        if checkbox_not_done_filter:
            upcoming_and_parts.append(checkbox_not_done_filter)
        upcoming_filter = {"and": upcoming_and_parts}
        overdue_pages = query_db({"filter": overdue_filter, "sorts": overdue_sort})
        today_pages = query_db({"filter": today_filter, "sorts": overdue_sort})
        upcoming_pages = query_db({"filter": upcoming_filter, "sorts": overdue_sort})

        # Diagnostic: if all zero, pull a small unfiltered sample to inspect property keys
        if (
            not overdue_pages.get("results")
            and not today_pages.get("results")
            and not upcoming_pages.get("results")
        ):
            try:
                sample = query_db({"page_size": 5})
                logger.warning(
                    "Notion returned 0 across filters. Sample first page properties: %s",
                    list((sample.get("results", [{}])[0]).get("properties", {}).keys()) if sample.get("results") else [],
                )
            except Exception:  # noqa: BLE001
                pass

        def page_to_task(page: dict) -> Task:
            props = page.get("properties", {})
            
            # DEBUG: Log all property names and types for first task
            if not hasattr(page_to_task, "_logged"):
                logger.warning("DEBUG: Notion task properties available: %s", {k: v.get("type") for k, v in props.items()})
                page_to_task._logged = True
            
            title_prop = None
            for name, prop in props.items():
                if prop.get("type") == "title":
                    title_prop = name
                    break
            name_val = _prop_text(props, title_prop) if title_prop else page.get("id", "Task")
            due_iso = _prop_date_iso(props, due_prop)
            
            # Extract area - Area is a RELATION property!
            area = None
            area_prop_name = None
            # Find the Area relation property
            for prop_name, prop_data in props.items():
                if prop_data.get("type") == "relation" and prop_name.lower() == "area":
                    area_prop_name = prop_name
                    relation_arr = prop_data.get("relation", [])
                    # DEBUG: Log Area relation structure and raw prop_data
                    if not hasattr(page_to_task, "_area_logged"):
                        logger.warning("DEBUG: Found Area relation property '%s' with %d relations. Raw data: %s", 
                                    prop_name, len(relation_arr), str(prop_data)[:200])
                        page_to_task._area_logged = True
                    if relation_arr:
                        # Fetch the first related page to get its title
                        try:
                            related_page_id = relation_arr[0].get("id")
                            if related_page_id:
                                # Use the Notion client or fallback to HTTP
                                try:
                                    related_page = client.pages.retrieve(page_id=related_page_id)
                                except AttributeError:
                                    # Fallback to HTTP
                                    resp = requests.get(
                                        f"https://api.notion.com/v1/pages/{related_page_id}",
                                        headers=notion_headers,
                                        timeout=30
                                    )
                                    resp.raise_for_status()
                                    related_page = resp.json()
                                
                                related_props = related_page.get("properties", {})
                                # Get the title property of the related page
                                for rp_name, rp_data in related_props.items():
                                    if rp_data.get("type") == "title":
                                        area = _prop_text(related_props, rp_name)
                                        if area:
                                            logger.debug("Fetched Area '%s' for task '%s'", area, name_val[:50])
                                        break
                        except Exception as e:
                            logger.warning("Failed to fetch Area relation for task '%s': %s", name_val[:50], e)
                    else:
                        # Relation array is empty - task doesn't have Area assigned
                        logger.debug("Task '%s' has Area property but no relation assigned", name_val[:50])
                    break
            
            # If Area not found, try select type as fallback
            if not area:
                # DEBUG: Check if any relation properties exist
                if not hasattr(page_to_task, "_no_area_logged"):
                    relation_props = [k for k, v in props.items() if v.get("type") == "relation"]
                    if relation_props:
                        logger.warning("DEBUG: No 'area' relation found, but found relation properties: %s", relation_props)
                    else:
                        logger.warning("DEBUG: No relation properties found at all. Looking for select/other types...")
                    page_to_task._no_area_logged = True
                
                area_candidates = ["Area", "area", "AREA", "Category", "category", "Project", "project"]
                for cand in area_candidates:
                    if cand in props:
                        val = _prop_text(props, cand)
                        if val:
                            area = val
                            if not hasattr(page_to_task, "_area_select_found_logged"):
                                logger.info("DEBUG: Found Area as select property '%s': '%s'", cand, val)
                                page_to_task._area_select_found_logged = True
                            break
            
            # Extract done - Done is a STATUS property!
            done_val = False  # Default to False
            if status_prop and status_prop in props:
                prop_data = props[status_prop]
                prop_type = prop_data.get("type")
                status_value = None
                
                if prop_type == "status":
                    status_obj = prop_data.get("status")
                    if status_obj:
                        status_value = status_obj.get("name", "")
                elif prop_type == "select":
                    sel = prop_data.get("select")
                    if sel:
                        status_value = sel.get("name", "")
                
                if status_value:
                    # Check if status value is in done_values
                    done_val = status_value in done_values
                    if done_val:
                        logger.debug("Found done=True on task %s: status='%s'", name_val, status_value)
                    # DEBUG: Log status value for first task
                    if not hasattr(page_to_task, "_status_logged"):
                        logger.warning("DEBUG: Task '%s' has status_prop '%s' (type=%s) with value '%s' (done_values=%s, matches=%s)", 
                                    name_val, status_prop, prop_type, status_value, done_values, done_val)
                        page_to_task._status_logged = True
                else:
                    # DEBUG: Log if status_prop exists but no value
                    if not hasattr(page_to_task, "_status_empty_logged"):
                        logger.warning("DEBUG: status_prop '%s' (type=%s) exists but has no value", 
                                    status_prop, prop_type)
                        page_to_task._status_empty_logged = True
            else:
                # DEBUG: Log if status_prop not found
                if status_prop and not hasattr(page_to_task, "_status_missing_logged"):
                    logger.warning("DEBUG: status_prop '%s' not found in task properties. Available: %s", 
                                status_prop, list(props.keys()))
                    page_to_task._status_missing_logged = True
            
            # Legacy checkbox support
            if not done_val and done_checkbox_prop:
                if done_checkbox_prop in props:
                    prop_data = props[done_checkbox_prop]
                    if prop_data.get("type") == "checkbox":
                        done_val = bool(prop_data.get("checkbox", False))
            
            url = page.get("url")
            return Task(
                id=page.get("id", ""),
                name=name_val or "(Untitled)",
                due_iso=due_iso,
                area=area,
                done=done_val,
                url=url,
            )

        logger.info(
            "Notion: overdue=%d today=%d upcoming=%d (before done filter)",
            len(overdue_pages.get("results", [])),
            len(today_pages.get("results", [])),
            len(upcoming_pages.get("results", [])),
        )

        overdue_tasks = [page_to_task(p) for p in overdue_pages.get("results", [])]
        today_tasks = [page_to_task(p) for p in today_pages.get("results", [])]
        upcoming_tasks = [page_to_task(p) for p in upcoming_pages.get("results", [])]

        # Post-filter: EXCLUDE any items with done=True (explicit check)
        overdue_before = len(overdue_tasks)
        today_before = len(today_tasks)
        upcoming_before = len(upcoming_tasks)
        
        overdue_tasks = [t for t in overdue_tasks if t.done is not True]
        today_tasks = [t for t in today_tasks if t.done is not True]
        upcoming_tasks = [t for t in upcoming_tasks if t.done is not True]
        
        overdue_filtered = overdue_before - len(overdue_tasks)
        today_filtered = today_before - len(today_tasks)
        upcoming_filtered = upcoming_before - len(upcoming_tasks)
        
        if overdue_filtered > 0 or today_filtered > 0 or upcoming_filtered > 0:
            logger.warning(
                "Notion: Filtered out done tasks (overdue: %d, today: %d, upcoming: %d)",
                overdue_filtered, today_filtered, upcoming_filtered
            )
        
        # Log sample tasks to verify area extraction
        if today_tasks:
            sample = today_tasks[0]
            logger.info("Sample today task: name='%s', area=%s, done=%s", sample.name, sample.area, sample.done)
        
        logger.info(
            "Notion: overdue=%d today=%d upcoming=%d (after done filter)",
            len(overdue_tasks), len(today_tasks), len(upcoming_tasks)
        )

        return today_tasks, overdue_tasks, upcoming_tasks
    except Exception as exc:  # noqa: BLE001
        logger.error("Notion fetch failed: %s", exc)
        return [], [], []


