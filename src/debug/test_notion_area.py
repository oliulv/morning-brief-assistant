#!/usr/bin/env python3
"""
Test script for Notion Area relation extraction - debug why areas aren't showing up.
"""

from __future__ import annotations

import json
import logging
import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("test-notion-area")


def main():
    api_key = os.getenv("NOTION_API_KEY")
    database_id = os.getenv("NOTION_TASK_DATABASE_ID")
    
    if not api_key or not database_id:
        print("ERROR: Set NOTION_API_KEY and NOTION_TASK_DATABASE_ID")
        return
    
    client = Client(auth=api_key)
    
    print("=" * 80)
    print("NOTION AREA TEST - Debugging Area Relation Extraction")
    print("=" * 80)
    print(f"\nDatabase ID: {database_id}")
    
    # Fetch a few tasks
    print("\n" + "=" * 80)
    print("Fetching tasks...")
    print("=" * 80)
    
    try:
        # Try SDK method first, fallback to HTTP (same pattern as main code)
        import requests
        notion_headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        
        try:
            # Some SDK versions use query, others use query_database
            if hasattr(client.databases, "query"):
                result = client.databases.query(database_id=database_id, page_size=5)
            elif hasattr(client.databases, "query_database"):
                result = client.databases.query_database(database_id=database_id, page_size=5)
            else:
                raise AttributeError("No query method found")
        except (AttributeError, TypeError):
            # Fallback to direct HTTP
            url = f"https://api.notion.com/v1/databases/{database_id}/query"
            resp = requests.post(url, headers=notion_headers, json={"page_size": 5}, timeout=30)
            resp.raise_for_status()
            result = resp.json()
        tasks = result.get("results", [])
        print(f"\nFound {len(tasks)} tasks\n")
        
        for i, task in enumerate(tasks, 1):
            props = task.get("properties", {})
            name_prop = None
            for pname, pdata in props.items():
                if pdata.get("type") == "title":
                    name_prop = pname
                    break
            
            # Safely extract task name
            if name_prop:
                title_arr = props.get(name_prop, {}).get("title", [])
                task_name = title_arr[0].get("plain_text", "Unknown") if title_arr else "Unknown"
            else:
                task_name = "Unknown"
            
            print(f"\n[{i}] Task: {task_name}")
            print(f"    Task ID: {task.get('id')}")
            
            # Check Area property
            area_prop = None
            for pname, pdata in props.items():
                if pdata.get("type") == "relation" and pname.lower() == "area":
                    area_prop = pname
                    break
            
            if not area_prop:
                print("    ❌ No 'Area' relation property found!")
                print(f"    Available properties: {list(props.keys())}")
                print(f"    Relation properties: {[k for k, v in props.items() if v.get('type') == 'relation']}")
            else:
                area_data = props[area_prop]
                relation_arr = area_data.get("relation", [])
                print(f"    ✅ Found Area property: '{area_prop}'")
                print(f"    Relation array length: {len(relation_arr)}")
                print(f"    Raw Area property data: {json.dumps(area_data, indent=6)[:500]}")
                
                if relation_arr:
                    print(f"    ✅ Task HAS Area relation!")
                    related_page_id = relation_arr[0].get("id")
                    print(f"    Related page ID: {related_page_id}")
                    
                    # Fetch the related page
                    try:
                        related_page = client.pages.retrieve(page_id=related_page_id)
                        related_props = related_page.get("properties", {})
                        print(f"    ✅ Successfully fetched related page")
                        
                        # Find title property
                        title_prop = None
                        for rp_name, rp_data in related_props.items():
                            if rp_data.get("type") == "title":
                                title_prop = rp_name
                                break
                        
                        if title_prop:
                            title_arr = related_props[title_prop].get("title", [])
                            area_name = title_arr[0].get("plain_text", "") if title_arr else ""
                            print(f"    ✅ Area name: '{area_name}'")
                        else:
                            print(f"    ❌ No title property found in related page")
                            print(f"    Related page properties: {list(related_props.keys())}")
                    except Exception as e:
                        print(f"    ❌ Failed to fetch related page: {e}")
                else:
                    print(f"    ⚠️  Task has Area property but relation array is EMPTY")
                    print(f"    This means the task doesn't have an Area assigned in Notion")
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

