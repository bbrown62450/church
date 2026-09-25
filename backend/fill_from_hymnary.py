#!/usr/bin/env python3
"""
Script to fill in missing fields in Notion hymns database using data from hymnary.org.
"""

import os
import sys
import re
import time
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from notion_hymns import NotionHymnsDB
import httpx
from bs4 import BeautifulSoup
from notion_client import Client
from notion_client.errors import APIResponseError

load_dotenv()


class HymnaryScraper:
    """Scraper to extract hymn data from hymnary.org pages using browser automation."""
    
    def __init__(self, use_browser: bool = True):
        self.use_browser = use_browser
        if use_browser:
            try:
                from playwright.sync_api import sync_playwright
                self.playwright = sync_playwright().start()
                self.browser = self.playwright.chromium.launch(headless=True)
                self.context = self.browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                self.page = self.context.new_page()
            except ImportError:
                print("Warning: Playwright not installed, falling back to HTTP requests")
                self.use_browser = False
                self.session = httpx.Client(timeout=30.0, follow_redirects=True)
                self.session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                })
        else:
            self.session = httpx.Client(timeout=30.0, follow_redirects=True)
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
    
    def get_hymn_data(self, hymnary_url: str) -> Dict[str, Any]:
        """
        Extract hymn data from a hymnary.org page.
        
        Args:
            hymnary_url: URL to the hymn page on hymnary.org
            
        Returns:
            Dictionary with extracted data (text, tune, etc.)
        """
        data = {}
        
        try:
            if self.use_browser:
                try:
                    # Use browser automation to get fully rendered page
                    self.page.goto(hymnary_url, wait_until='domcontentloaded', timeout=15000)
                    # Scroll to bottom to ensure all content loads
                    self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    self.page.wait_for_timeout(2000)
                    # Scroll back to top
                    self.page.evaluate("window.scrollTo(0, 0)")
                    self.page.wait_for_timeout(1000)
                    html_content = self.page.content()
                    soup = BeautifulSoup(html_content, 'html.parser')
                except Exception as browser_error:
                    # Fall back to HTTP if browser fails
                    if not hasattr(self, 'session'):
                        self.session = httpx.Client(timeout=30.0, follow_redirects=True)
                        self.session.headers.update({
                            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                        })
                    response = self.session.get(hymnary_url)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
            else:
                response = self.session.get(hymnary_url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract hymn text/lyrics
            # Note: hymnary.org may not always show full text due to copyright
            # We'll try multiple strategies to find text
            
            # Strategy 1: Look for hymntext div with stanzas
            text_section = soup.find('div', class_='hymntext')
            if text_section:
                stanzas = text_section.find_all('div', class_='stanza')
                if stanzas:
                    lines = []
                    for stanza in stanzas:
                        verse_lines = []
                        for line in stanza.find_all('div', class_='line'):
                            text = line.get_text(strip=True)
                            if text:
                                verse_lines.append(text)
                        if verse_lines:
                            lines.append('\n'.join(verse_lines))
                    if lines:
                        data['text'] = '\n\n'.join(lines)
            
            # Strategy 2: Look for text in pre tags (sometimes used for lyrics)
            if not data.get('text'):
                pre_tags = soup.find_all('pre')
                for pre in pre_tags:
                    text = pre.get_text(strip=True)
                    if text and len(text) > 50:  # Likely to be hymn text if substantial
                        data['text'] = text
                        break
            
            # Strategy 3: Look for divs with text content (less reliable)
            if not data.get('text'):
                text_divs = soup.find_all('div', class_=lambda x: x and 'text' in str(x).lower())
                for div in text_divs:
                    # Skip if it's metadata, not actual lyrics
                    if 'metadata' in str(div.get('class', [])).lower():
                        continue
                    text = div.get_text(strip=True)
                    # Check if it looks like lyrics (has multiple lines, reasonable length)
                    lines = [l.strip() for l in text.split('\n') if l.strip()]
                    if len(lines) >= 4 and len(text) > 100:  # Likely lyrics
                        data['text'] = '\n\n'.join(lines)
                        break
            
            # Extract tune information (if available in a structured way)
            tune_info = soup.find('div', class_='tune')
            if tune_info:
                tune_name = tune_info.find('a')
                if tune_name:
                    data['tune'] = tune_name.get_text(strip=True)
            
            # Extract metadata from table structure (td with hy_infoLabel spans)
            # Look for spans with class hy_infoLabel (these are the field labels)
            for label_span in soup.find_all('span', class_='hy_infoLabel'):
                label = label_span.get_text(strip=True)
                label_lower = label.lower()
                
                # Get the parent td, then find the value (next td or content in same td)
                parent_td = label_span.find_parent('td')
                if not parent_td:
                    continue
                
                # Value could be in the next td (sibling) or after the span in same td
                value_td = parent_td.find_next_sibling('td')
                if value_td:
                    # For fields that need dates (Author, Composer, Arranger, Translator, Harmonizer),
                    # we need the full text including parenthetical dates.
                    # For Topic, we need full text to parse semicolon-separated values.
                    # For Scripture, links are preferred (individual references).
                    label_needs_full_text = (label_lower.startswith('author') or 
                                            label_lower.startswith('composer') or 
                                            label_lower.startswith('arranger') or 
                                            label_lower.startswith('translator') or
                                            label_lower.startswith('harmonizer') or
                                            label_lower.startswith('adapter') or
                                            label_lower.startswith('topic'))
                    links = value_td.find_all('a')
                    if links and not label_needs_full_text:
                        # For Scripture/Topic: extract link texts
                        values = [link.get_text(strip=True) for link in links if link.get_text(strip=True)]
                        value = ', '.join(values) if values else value_td.get_text(strip=True)
                    else:
                        # For Author/Composer/Arranger: get full text (includes parenthetical dates)
                        value = value_td.get_text(strip=True)
                else:
                    # Value might be in the same td after the span
                    value = parent_td.get_text(strip=True)
                    # Remove the label from value
                    value = value.replace(label, '', 1).strip()
                
                # Map labels to our data fields
                if label_lower == 'author' or (label_lower.startswith('author') and 'author' in label_lower):
                    # Author (lyricist) - extract name and date
                    if not data.get('lyricist'):
                        # Remove date/year from name - could be (5th cent.), (1889), (1902), etc.
                        name = re.sub(r'\s*\([^)]+\).*$', '', value).strip()
                        data['lyricist'] = name
                    # Extract date for lyrics date
                    # Extract everything in parentheses, then find all 4-digit years and use the latest
                    paren_match = re.search(r'\(([^)]+)\)', value)
                    if paren_match and not data.get('lyrics_date'):
                        inside_paren = paren_match.group(1)
                        year_matches = re.findall(r'\b(\d{4})\b', inside_paren)
                        if year_matches:
                            years = [int(y) for y in year_matches]
                            latest_year = max(years)  # Use the latest/revision date
                            data['lyrics_date'] = f"{latest_year}-01-01"
                    elif 'cent' in value.lower() and not data.get('lyrics_date'):
                        # Handle century notation like "5th cent."
                        # Note: Notion date fields require years >= 1000, so skip very old dates
                        cent_match = re.search(r'(\d+)\s*(?:th|st|nd|rd)?\s*cent', value, re.I)
                        if cent_match:
                            century = int(cent_match.group(1))
                            # Approximate: 5th cent = 401-500, so use middle year
                            year = (century - 1) * 100 + 50
                            # Notion requires years >= 1000, so skip very old dates
                            if year >= 1000:
                                data['lyrics_date'] = f"{year}-01-01"
                
                elif label_lower == 'translator' or label_lower.startswith('translator'):
                    # Translator - could also be used for lyricist if no author
                    if not data.get('lyricist'):
                        name = re.sub(r'\s*\([^)]+\).*$', '', value).strip()
                        data['lyricist'] = name
                    # Extract year for lyrics date
                    # Extract everything in parentheses, then find all 4-digit years and use the latest
                    paren_match = re.search(r'\(([^)]+)\)', value)
                    if paren_match and not data.get('lyrics_date'):
                        inside_paren = paren_match.group(1)
                        year_matches = re.findall(r'\b(\d{4})\b', inside_paren)
                        if year_matches:
                            years = [int(y) for y in year_matches]
                            latest_year = max(years)  # Use the latest/revision date
                            data['lyrics_date'] = f"{latest_year}-01-01"
                
                elif label_lower == 'composer' or label_lower.startswith('composer'):
                    # Composer - extract name and year for music date
                    if not data.get('composer'):
                        # Remove date/year from name
                        name = re.sub(r'\s*\([^)]+\).*$', '', value).strip()
                        data['composer'] = name
                    # Extract year for music date
                    # Extract everything in parentheses, then find all 4-digit years and use the latest
                    paren_match = re.search(r'\(([^)]+)\)', value)
                    if paren_match and not data.get('music_date'):
                        inside_paren = paren_match.group(1)
                        year_matches = re.findall(r'\b(\d{4})\b', inside_paren)
                        if year_matches:
                            years = [int(y) for y in year_matches]
                            latest_year = max(years)  # Use the latest/revision date
                            data['music_date'] = f"{latest_year}-01-01"
                
                elif label_lower == 'arranger' or label_lower.startswith('arranger'):
                    # Arranger - could be used for composer/music date
                    if not data.get('composer'):
                        name = re.sub(r'\s*\([^)]+\).*$', '', value).strip()
                        data['composer'] = name
                    # Extract year for music date
                    # Extract everything in parentheses, then find all 4-digit years and use the latest
                    paren_match = re.search(r'\(([^)]+)\)', value)
                    if paren_match and not data.get('music_date'):
                        inside_paren = paren_match.group(1)
                        year_matches = re.findall(r'\b(\d{4})\b', inside_paren)
                        if year_matches:
                            years = [int(y) for y in year_matches]
                            latest_year = max(years)  # Use the latest/revision date
                            data['music_date'] = f"{latest_year}-01-01"
                
                elif label_lower == 'harmonizer' or label_lower.startswith('harmonizer'):
                    # Harmonizer - could be used for composer/music date
                    if not data.get('composer'):
                        name = re.sub(r'\s*\([^)]+\).*$', '', value).strip()
                        data['composer'] = name
                    # Extract year for music date
                    # Extract everything in parentheses, then find all 4-digit years and use the latest
                    paren_match = re.search(r'\(([^)]+)\)', value)
                    if paren_match and not data.get('music_date'):
                        inside_paren = paren_match.group(1)
                        year_matches = re.findall(r'\b(\d{4})\b', inside_paren)
                        if year_matches:
                            years = [int(y) for y in year_matches]
                            latest_year = max(years)  # Use the latest/revision date
                            data['music_date'] = f"{latest_year}-01-01"
                
                elif label_lower == 'adapter' or label_lower.startswith('adapter'):
                    # Adapter - could be used for composer/music date
                    if not data.get('composer'):
                        name = re.sub(r'\s*\([^)]+\).*$', '', value).strip()
                        data['composer'] = name
                    # Extract year for music date
                    # Extract everything in parentheses, then find all 4-digit years and use the latest
                    paren_match = re.search(r'\(([^)]+)\)', value)
                    if paren_match and not data.get('music_date'):
                        inside_paren = paren_match.group(1)
                        year_matches = re.findall(r'\b(\d{4})\b', inside_paren)
                        if year_matches:
                            years = [int(y) for y in year_matches]
                            latest_year = max(years)  # Use the latest/revision date
                            data['music_date'] = f"{latest_year}-01-01"
                
                elif label_lower == 'meter' or label_lower.startswith('meter'):
                    if not data.get('meter'):
                        data['meter'] = value
                
                elif label_lower == 'scripture' or label_lower.startswith('scripture'):
                    if not data.get('scripture_references'):
                        # Scripture references are in links - extract link texts
                        links = value_td.find_all('a')
                        if links:
                            # Extract all scripture references from links (ignore "(X more...)" links)
                            refs = []
                            for link in links:
                                link_text = link.get_text(strip=True)
                                # Skip "(X more...)" links
                                if not re.match(r'^\(\d+\s+more\.\.\.\)$', link_text):
                                    refs.append(link_text)
                            if refs:
                                data['scripture_references'] = '; '.join(refs)
                        else:
                            # Fallback to text if no links
                            data['scripture_references'] = value
                
                elif label_lower == 'topic' or label_lower.startswith('topic'):
                    if not data.get('theme'):
                        # Topics can have "(X more...)" - extract all topics
                        topics = []
                        for part in re.split(r'[;,]', value):
                            part = part.strip()
                            # Remove "(X more...)" text
                            part = re.sub(r'\s*\(\d+\s+more\.\.\.\)', '', part).strip()
                            if part and part != '(7 more...)':
                                topics.append(part)
                        if topics:
                            data['theme'] = topics
                
                elif label_lower == 'name':
                    # Check if this is in Tune Information section
                    parent_text = parent_td.find_parent().get_text(strip=True).lower() if parent_td.find_parent() else ""
                    if 'tune' in parent_text:
                        if not data.get('tune_name'):
                            data['tune_name'] = value
                        if not data.get('tune'):
                            data['tune'] = value
            
            # Fallback: Look for tune name in links
            if not data.get('tune') and not data.get('tune_name'):
                tune_links = soup.find_all('a', href=re.compile(r'/tune/'))
                if tune_links:
                    tune_name = tune_links[0].get_text(strip=True)
                    if not data.get('tune_name'):
                        data['tune_name'] = tune_name
                    if not data.get('tune'):
                        data['tune'] = tune_name
            
            # Fallback: Look for composer/author in links
            composer_links = soup.find_all('a', href=re.compile(r'/person/'))
            for link in composer_links:
                link_text = link.get_text(strip=True)
                parent_text = link.parent.get_text(strip=True).lower() if link.parent else ""
                if 'composer' in parent_text and not data.get('composer'):
                    data['composer'] = link_text
                elif ('author' in parent_text or 'lyricist' in parent_text) and not data.get('lyricist'):
                    data['lyricist'] = link_text
            
            # Be respectful with rate limiting
            time.sleep(1)
            
        except Exception as e:
            print(f"  Warning: Could not scrape {hymnary_url}: {e}")
        
        return data
    
    def close(self):
        """Close the browser/session."""
        if self.use_browser and hasattr(self, 'browser'):
            self.browser.close()
            self.playwright.stop()
        elif hasattr(self, 'session'):
            self.session.close()


class HymnaryFiller:
    """Fill missing fields in Notion database using hymnary.org data."""
    
    def __init__(self, dry_run: bool = True):
        self.db = NotionHymnsDB()
        self.scraper = HymnaryScraper(use_browser=True)
        self.dry_run = dry_run
        self.stats = {
            'processed': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
    
    def get_property_value(self, hymn: Dict[str, Any], prop_name: str) -> Any:
        """Get the value of a property from a hymn object."""
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
        elif prop_type == "select":
            select_obj = prop_data.get("select")
            return select_obj.get("name") if select_obj else None
        elif prop_type == "multi_select":
            return [opt.get("name") for opt in prop_data.get("multi_select", [])]
        elif prop_type == "date":
            date_obj = prop_data.get("date")
            return date_obj.get("start") if date_obj else None
        elif prop_type == "url":
            return prop_data.get("url")
        
        return None
    
    def fill_hymn(self, hymn: Dict[str, Any], fields_to_fill: List[str] = None, show_details: bool = True) -> bool:
        """
        Fill missing fields for a single hymn.
        
        Args:
            hymn: Hymn page data from Notion
            fields_to_fill: List of field names to fill (None = fill all missing)
            
        Returns:
            True if updates were made, False otherwise
        """
        page_id = hymn['id']
        title = self.get_property_value(hymn, "Hymn Title")
        hymnary_url = self.get_property_value(hymn, "Hymnary.org Link")
        
        if not hymnary_url:
            if show_details:
                print(f"  Skipping '{title}' - no hymnary.org link")
            self.stats['skipped'] += 1
            return False
        
        if show_details:
            print(f"\nProcessing: {title}")
            print(f"  URL: {hymnary_url}")
        
        # Scrape data from hymnary.org
        scraped_data = self.scraper.get_hymn_data(hymnary_url)
        
        if not scraped_data:
            if show_details:
                print(f"  ✗ No data extracted from hymnary.org")
            else:
                print(f"  ✗ '{title}' - No data extracted from hymnary.org")
            self.stats['skipped'] += 1
            return False
        
        # Determine which fields to update
        updates = {}
        skip_reasons = []
        
        # Map scraped data to Notion properties
        field_mapping = {
            'text': 'Text',
            'tune': 'Tune',
            'tune_name': 'Tune Name',
            'composer': 'Composer',
            'lyricist': 'Lyricist',
            'meter': 'Meter',
            'scripture_references': 'Scripture References',
            'music_date': 'Music Date',
            'lyrics_date': 'Lyrics Date',
            'theme': 'Theme'
        }
        
        for scraped_key, notion_field in field_mapping.items():
            if scraped_key in scraped_data:
                current_value = self.get_property_value(hymn, notion_field)
                scraped_value = scraped_data[scraped_key]
                
                # Only update if field is missing or if fields_to_fill is specified
                should_update = False
                if fields_to_fill:
                    should_update = notion_field in fields_to_fill
                else:
                    should_update = not current_value
                
                if should_update:
                    if scraped_value and scraped_value != current_value:
                        updates[notion_field] = scraped_value
                        if show_details:
                            print(f"  ✓ Will update {notion_field}: {scraped_value[:50]}..." if len(str(scraped_value)) > 50 else f"  ✓ Will update {notion_field}: {scraped_value}")
                    elif current_value:
                        skip_reasons.append(f"{notion_field} already filled")
                elif current_value and not fields_to_fill:
                    skip_reasons.append(f"{notion_field} already has value")
            elif fields_to_fill and notion_field in fields_to_fill:
                skip_reasons.append(f"{notion_field} not found on hymnary.org")
        
        if not updates:
            if show_details:
                if skip_reasons:
                    print(f"  → Skipped: {', '.join(skip_reasons)}")
                else:
                    print(f"  → No updates needed (all fields already filled or no matching data)")
            else:
                # Show brief message for non-detailed entries every 10th skip
                if self.stats['skipped'] % 10 == 0 or self.stats['skipped'] <= 5:
                    reason = skip_reasons[0] if skip_reasons else "all fields already filled"
                    print(f"  → Skipped '{title}': {reason}")
            self.stats['skipped'] += 1
            return False
        
        # Apply updates
        if self.dry_run:
            if show_details:
                print(f"  [DRY RUN] Would update {len(updates)} field(s)")
            self.stats['updated'] += 1
            return True
        else:
            try:
                # Build update properties based on field type
                update_props = {}
                for field_name, value in updates.items():
                    if field_name in ['Text', 'Tune', 'Composer', 'Lyricist', 'Tune Name', 'Scripture References']:
                        update_props[field_name] = {
                            "rich_text": [{"text": {"content": str(value)}}]
                        }
                    elif field_name == 'Meter':
                        # Meter is a select field - value should be the option name
                        update_props[field_name] = {
                            "select": {"name": str(value)}
                        }
                    elif field_name in ['Music Date', 'Lyrics Date']:
                        # Date field - value should be in YYYY-MM-DD format
                        update_props[field_name] = {
                            "date": {"start": str(value)}
                        }
                    elif field_name == 'Theme':
                        # Theme is multi-select - value should be a list
                        if isinstance(value, list):
                            update_props[field_name] = {
                                "multi_select": [{"name": str(v)} for v in value]
                            }
                        else:
                            # Single theme as string
                            update_props[field_name] = {
                                "multi_select": [{"name": str(value)}]
                            }
                
                self.db.client.pages.update(
                    page_id=page_id,
                    properties=update_props
                )
                if show_details:
                    print(f"  ✓ Updated {len(updates)} field(s): {', '.join(updates.keys())}")
                else:
                    # Show brief updates for non-detailed entries
                    print(f"  ✓ Updated '{title}': {', '.join(updates.keys())}")
                self.stats['updated'] += 1
                return True
            except Exception as e:
                print(f"  ✗ Error updating '{title}': {e}")
                self.stats['errors'] += 1
                return False
    
    def fill_all(self, fields_to_fill: List[str] = None, limit: Optional[int] = None):
        """
        Fill missing fields for all hymns in the database.
        
        Args:
            fields_to_fill: List of specific fields to fill (None = fill all missing)
            limit: Maximum number of hymns to process (None = all)
        """
        print(f"\n{'='*60}")
        print(f"Filling missing fields from hymnary.org")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE UPDATE'}")
        if fields_to_fill:
            print(f"Fields to fill: {', '.join(fields_to_fill)}")
        print(f"{'='*60}\n")
        
        hymns = self.db.list_hymns()
        
        if limit:
            hymns = hymns[:limit]
        
        print(f"Processing {len(hymns)} hymns...\n")
        
        for idx, hymn in enumerate(hymns, 1):
            self.stats['processed'] += 1
            
            # Progress indicator every 25 hymns (since this is slower due to web scraping)
            if idx % 25 == 0:
                print(f"\n[Progress: {idx}/{len(hymns)} ({idx*100//len(hymns)}%)] Processed: {self.stats['processed']}, Updated: {self.stats['updated']}, Skipped: {self.stats['skipped']}, Errors: {self.stats['errors']}\n")
            
            self.fill_hymn(hymn, fields_to_fill, show_details=(idx <= 5))
        
        # Print summary
        print(f"\n{'='*60}")
        print("Summary:")
        print(f"  Processed: {self.stats['processed']}")
        print(f"  Updated: {self.stats['updated']}")
        print(f"  Skipped: {self.stats['skipped']}")
        print(f"  Errors: {self.stats['errors']}")
        print(f"{'='*60}")
        
        if self.dry_run:
            print("\nThis was a DRY RUN. No changes were made.")
            print("Run with --execute to apply changes.")
    
    def close(self):
        """Clean up resources."""
        self.scraper.close()


def main():
    """CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Fill missing fields in Notion hymns database using hymnary.org"
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually update the database (default is dry-run)'
    )
    parser.add_argument(
        '--fields',
        nargs='+',
        help='Specific fields to fill (e.g., Text Tune). Default: all missing fields'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of hymns to process (for testing)'
    )
    parser.add_argument(
        '--search',
        type=str,
        help='Only process hymns matching this title search'
    )
    
    args = parser.parse_args()
    
    filler = HymnaryFiller(dry_run=not args.execute)
    
    try:
        if args.search:
            hymns = filler.db.search_hymns(title=args.search)
            if args.limit:
                hymns = hymns[:args.limit]
            print(f"\nProcessing {len(hymns)} hymns matching '{args.search}'...\n")
            for idx, hymn in enumerate(hymns, 1):
                filler.stats['processed'] += 1
                
                # Progress indicator every 25 hymns
                if idx % 25 == 0:
                    print(f"\n[Progress: {idx}/{len(hymns)} ({idx*100//len(hymns)}%)] Processed: {filler.stats['processed']}, Updated: {filler.stats['updated']}, Skipped: {filler.stats['skipped']}, Errors: {filler.stats['errors']}\n")
                
                filler.fill_hymn(hymn, args.fields, show_details=(idx <= 5))
            
            print(f"\n{'='*60}")
            print("Summary:")
            print(f"  Processed: {filler.stats['processed']}")
            print(f"  Updated: {filler.stats['updated']}")
            print(f"  Skipped: {filler.stats['skipped']}")
            print(f"  Errors: {filler.stats['errors']}")
            print(f"{'='*60}")
        else:
            filler.fill_all(fields_to_fill=args.fields, limit=args.limit)
    finally:
        filler.close()


if __name__ == "__main__":
    main()

