#!/usr/bin/env python3
"""
Script to interact with a Notion database of hymns.
Requires NOTION_API_KEY and NOTION_DATABASE_ID environment variables.
"""

import os
import sys
from typing import Optional, List, Dict, Any
from notion_client import Client
from notion_client.errors import APIResponseError
import httpx

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional


class NotionHymnsDB:
    """Client for interacting with a Notion database of hymns."""
    
    def __init__(self, api_key: Optional[str] = None, database_id: Optional[str] = None):
        """
        Initialize the Notion client.
        
        Args:
            api_key: Notion integration API key (or set NOTION_API_KEY env var)
            database_id: Notion database ID (or set NOTION_DATABASE_ID env var)
        """
        self.api_key = api_key or os.getenv('NOTION_API_KEY')
        self.database_id = database_id or os.getenv('NOTION_DATABASE_ID')
        
        if not self.api_key:
            raise ValueError("Notion API key is required. Set NOTION_API_KEY env var or pass as parameter.")
        if not self.database_id:
            raise ValueError("Notion database ID is required. Set NOTION_DATABASE_ID env var or pass as parameter.")
        
        self.client = Client(auth=self.api_key)
        # Use httpx directly for query operations since notion-client's request() has issues
        self.httpx_client = httpx.Client(
            base_url="https://api.notion.com/v1",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
        )
    
    def list_hymns(self, page_size: int = 100) -> List[Dict[str, Any]]:
        """
        List all hymns from the database.
        
        Args:
            page_size: Number of results per page (max 100)
            
        Returns:
            List of hymn entries from the database
        """
        try:
            results = []
            cursor = None
            
            while True:
                body = {
                    "page_size": page_size,
                }
                if cursor:
                    body["start_cursor"] = cursor
                
                # Use httpx directly since notion-client's request() doesn't work properly for queries
                response = self.httpx_client.post(
                    f"/databases/{self.database_id}/query",
                    json=body
                )
                response.raise_for_status()
                data = response.json()
                
                results.extend(data["results"])
                
                if not data.get("has_more"):
                    break
                cursor = data["next_cursor"]
            
            return results
        except Exception as e:
            print(f"Error querying database: {e}")
            sys.exit(1)
    
    def search_hymns(self, 
                     title: Optional[str] = None,
                     filter_property: Optional[str] = None,
                     filter_value: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search hymns by title or other property.
        
        Args:
            title: Search for hymns containing this title (case-insensitive)
            filter_property: Property name to filter by
            filter_value: Value to filter for
            
        Returns:
            List of matching hymn entries
        """
        try:
            filters = []
            
            if title:
                filters.append({
                    "property": "Hymn Title",
                    "title": {
                        "contains": title
                    }
                })
            
            if filter_property and filter_value:
                # Try to determine the property type and create appropriate filter
                filters.append({
                    "property": filter_property,
                    "rich_text": {
                        "contains": filter_value
                    }
                })
            
            if not filters:
                return self.list_hymns()
            
            filter_condition = {"and": filters} if len(filters) > 1 else filters[0]
            
            # Use httpx directly since notion-client's request() doesn't work properly for queries
            response = self.httpx_client.post(
                f"/databases/{self.database_id}/query",
                json={"filter": filter_condition}
            )
            response.raise_for_status()
            data = response.json()
            
            return data["results"]
        except Exception as e:
            print(f"Error searching database: {e}")
            sys.exit(1)
    
    def get_hymn(self, page_id: str) -> Dict[str, Any]:
        """
        Get a specific hymn by page ID.
        
        Args:
            page_id: The Notion page ID of the hymn
            
        Returns:
            Hymn page data
        """
        try:
            return self.client.pages.retrieve(page_id)
        except APIResponseError as e:
            print(f"Error retrieving page: {e}")
            sys.exit(1)
    
    def create_hymn(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new hymn entry in the database.
        
        Args:
            properties: Dictionary of properties matching your database schema
                       Example: {"Title": {"title": [{"text": {"content": "Amazing Grace"}}]}}
            
        Returns:
            The created hymn page
        """
        try:
            return self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
        except APIResponseError as e:
            print(f"Error creating hymn: {e}")
            sys.exit(1)
    
    def update_hymn(self, page_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing hymn entry.
        
        Args:
            page_id: The Notion page ID of the hymn to update
            properties: Dictionary of properties to update
            
        Returns:
            The updated hymn page
        """
        try:
            return self.client.pages.update(
                page_id=page_id,
                properties=properties
            )
        except APIResponseError as e:
            print(f"Error updating hymn: {e}")
            sys.exit(1)
    
    def format_hymn(self, hymn: Dict[str, Any]) -> str:
        """
        Format a hymn entry for display.
        
        Args:
            hymn: Hymn page data from Notion
            
        Returns:
            Formatted string representation
        """
        props = hymn.get("properties", {})
        lines = []
        
        for prop_name, prop_data in props.items():
            prop_type = prop_data.get("type")
            value = None
            
            if prop_type == "title":
                value = "".join([text.get("plain_text", "") for text in prop_data.get("title", [])])
            elif prop_type == "rich_text":
                value = "".join([text.get("plain_text", "") for text in prop_data.get("rich_text", [])])
            elif prop_type == "number":
                value = prop_data.get("number")
            elif prop_type == "select":
                value = prop_data.get("select", {}).get("name")
            elif prop_type == "multi_select":
                value = [opt.get("name") for opt in prop_data.get("multi_select", [])]
            elif prop_type == "date":
                date_obj = prop_data.get("date")
                value = date_obj.get("start") if date_obj else None
            
            if value is not None:
                lines.append(f"{prop_name}: {value}")
        
        return "\n".join(lines) if lines else str(hymn)


def main():
    """CLI interface for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Interact with a Notion database of hymns")
    parser.add_argument("--list", action="store_true", help="List all hymns")
    parser.add_argument("--search", type=str, help="Search hymns by title")
    parser.add_argument("--get", type=str, help="Get a specific hymn by page ID")
    parser.add_argument("--create", action="store_true", help="Create a new hymn (interactive)")
    parser.add_argument("--format", action="store_true", help="Format output nicely")
    
    args = parser.parse_args()
    
    try:
        db = NotionHymnsDB()
    except ValueError as e:
        print(f"Error: {e}")
        print("\nMake sure to set NOTION_API_KEY and NOTION_DATABASE_ID environment variables.")
        print("Or create a .env file with these values.")
        sys.exit(1)
    
    if args.list:
        hymns = db.list_hymns()
        print(f"\nFound {len(hymns)} hymns:\n")
        for hymn in hymns:
            if args.format:
                print(db.format_hymn(hymn))
                print("-" * 50)
            else:
                print(f"ID: {hymn['id']}")
                props = hymn.get("properties", {})
                title_prop = props.get("Hymn Title", {})
                if title_prop.get("type") == "title":
                    title = "".join([t.get("plain_text", "") for t in title_prop.get("title", [])])
                    print(f"Title: {title}")
                print()
    
    elif args.search:
        hymns = db.search_hymns(title=args.search)
        print(f"\nFound {len(hymns)} matching hymns:\n")
        for hymn in hymns:
            if args.format:
                print(db.format_hymn(hymn))
                print("-" * 50)
            else:
                props = hymn.get("properties", {})
                title_prop = props.get("Hymn Title", {})
                if title_prop.get("type") == "title":
                    title = "".join([t.get("plain_text", "") for t in title_prop.get("title", [])])
                    print(f"Title: {title} (ID: {hymn['id']})")
                print()
    
    elif args.get:
        hymn = db.get_hymn(args.get)
        if args.format:
            print(db.format_hymn(hymn))
        else:
            print(hymn)
    
    elif args.create:
        print("Creating a new hymn...")
        title = input("Enter hymn title: ")
        properties = {
            "Hymn Title": {
                "title": [{"text": {"content": title}}]
            }
        }
        # Add more properties based on your database schema
        # Example:
        # number = input("Enter hymn number (optional): ")
        # if number:
        #     properties["Number"] = {"number": int(number)}
        
        hymn = db.create_hymn(properties)
        print(f"\nCreated hymn: {hymn['id']}")
        if args.format:
            print(db.format_hymn(hymn))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

