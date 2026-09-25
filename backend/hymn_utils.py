"""Shared helpers for reading hymn properties.

Supports two shapes:
  * Nested Notion page shape: {"properties": {<name>: {"type": ..., ...}}}
  * Flat dict shape produced by repos.hymns.list_hymns:
    {<Notion property name>: <plain value>}
"""
from typing import Any, Dict


def get_property_value(hymn: Dict[str, Any], prop_name: str) -> Any:
    """Get the value of a property from a hymn object (nested or flat)."""
    # Flat shape: the Notion property names are top-level keys mapping directly
    # to plain values. Detect it by the absence of a Notion "properties" envelope.
    if "properties" not in hymn:
        return hymn.get(prop_name)

    props = hymn.get("properties", {})
    prop_data = props.get(prop_name, {})
    prop_type = prop_data.get("type")

    if prop_type == "title":
        return "".join([t.get("plain_text", "") for t in prop_data.get("title", [])])
    elif prop_type == "rich_text":
        text = "".join([t.get("plain_text", "") for t in prop_data.get("rich_text", [])])
        return text if text else None
    elif prop_type == "number":
        return prop_data.get("number")
    elif prop_type == "url":
        return prop_data.get("url")
    elif prop_type == "date":
        date_obj = prop_data.get("date")
        return date_obj.get("start") if date_obj else None
    elif prop_type == "multi_select":
        return [opt.get("name") for opt in prop_data.get("multi_select", []) if opt.get("name")]
    return None
