# Worship Service Builder

Plan worship services with a Notion hymn database: pick a date, load the lectionary, suggest hymns by scripture, generate liturgy with AI (PC(USA)-friendly), and export to Word. Includes communion liturgy, service archive, and optional “exclude hymns used in last 12 weeks.”

## Pushing to GitHub (without exposing secrets)

1. **Never commit `.env`.** It’s in `.gitignore`. All secrets stay in `.env` on your machine (or in your host’s “Secrets”).
2. **Use `.env.example` as a template.** It lists variable names with no values. Others (or you on a new machine) run:
   ```bash
   cp .env.example .env
   # Edit .env and add your real keys (not committed)
   ```
3. **Create the repo and push** (replace `church` with your repo name if different):
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Worship Service Builder"
   git branch -M main
   git remote add origin https://github.com/bbrown62450/church.git
   git push -u origin main
   ```
   If the repo already exists on GitHub, clone it first or add `origin` and push.

## Setup (local)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create a Notion Integration:**
   - Go to https://www.notion.so/my-integrations
   - Click "New integration"
   - Give it a name (e.g., "Hymns Script")
   - Copy the "Internal Integration Token" (this is your API key)

3. **Connect the integration to your database:**
   - Open your hymns database in Notion
   - Click the "..." menu in the top right
   - Select "Connections" → "Add connections"
   - Select your integration

4. **Get your Database ID:**
   - Open your database in Notion
   - Look at the URL: `https://www.notion.so/{workspace}/{database_id}?v=...`
   - Copy the `database_id` (it's a 32-character string, usually with hyphens)

5. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API key and database ID
   ```

   Or export them in your shell:
   ```bash
   export NOTION_API_KEY="secret_your_api_key_here"
   export NOTION_DATABASE_ID="your_database_id_here"
   ```

## Usage

### List all hymns
```bash
python notion_hymns.py --list
```

### List all hymns (formatted)
```bash
python notion_hymns.py --list --format
```

### Search hymns by title
```bash
python notion_hymns.py --search "Amazing Grace"
```

### Get a specific hymn by page ID
```bash
python notion_hymns.py --get "page-id-here"
```

### Create a new hymn (interactive)
```bash
python notion_hymns.py --create
```

### Worship Service Builder (UI)

Generate a full worship service with AI-written liturgy and export to Word:

1. **Environment:** Add `OPENAI_API_KEY` to your `.env` (and keep `NOTION_API_KEY` / `NOTION_DATABASE_ID` for hymn data). The app uses `gpt-3.5-turbo` by default; if your project has access to another model (e.g. `gpt-4o-mini`), set `OPENAI_MODEL` in `.env`.
2. **Run the app:**
   ```bash
   streamlit run app.py
   ```
   (Or `python3 -m streamlit run app.py` if `streamlit` isn’t on your PATH.)
3. **In the UI:**
   - Set **Occasion** and **Date** in the sidebar (e.g. *February 15, 2026*).
   - Click **Look up Vanderbilt lectionary** to load that Sunday’s Revised Common Lectionary readings (First reading, Psalm, Second reading, Gospel). The occasion will update to the liturgical name (e.g. Transfiguration Sunday), and the scripture box will fill; you can edit as needed.
   - Or enter **Scripture readings** manually (one per line).
   - Use **“Suggest hymns by scripture”** to find hymns in your Notion database that match the first reading.
   - Choose **Opening**, **Response**, and **Closing** hymns from your database.
   - Check which **Liturgy** sections to generate (Call to Worship, Prayer of Confession, Assurance, Prayers of the People, Benediction).
   - Click **Generate liturgy** (uses OpenAI), then **Download Word document**.

The Word file includes the order of service, hymn numbers and Hymnary.org links, and the generated prayers and blessings. You can edit in Word and use “Save as PDF” if you need a PDF.

### Select hymns for a Sunday (CLI)

```bash
python select_sunday_hymns.py              # Transfiguration Sunday (traditional)
python select_sunday_hymns.py --list-all     # List all hymn titles in Notion
```

## Using as a Python Module

You can also import and use the `NotionHymnsDB` class in your own scripts:

```python
from notion_hymns import NotionHymnsDB
import os

# Initialize the client
db = NotionHymnsDB()

# List all hymns
hymns = db.list_hymns()
for hymn in hymns:
    print(db.format_hymn(hymn))

# Search for hymns
results = db.search_hymns(title="Grace")

# Create a new hymn
new_hymn = db.create_hymn({
    "Title": {
        "title": [{"text": {"content": "Amazing Grace"}}]
    },
    # Add other properties based on your database schema
})

# Update a hymn
db.update_hymn(page_id, {
    "Title": {
        "title": [{"text": {"content": "Updated Title"}}]
    }
})
```

## Database Schema

The script assumes your Notion database has at least a "Title" property. You may need to adjust property names and types in the script to match your specific database schema.

Common property types:
- **Title**: `{"title": [{"text": {"content": "..."}}]}`
- **Rich Text**: `{"rich_text": [{"text": {"content": "..."}}]}`
- **Number**: `{"number": 123}`
- **Select**: `{"select": {"name": "option"}}`
- **Multi-select**: `{"multi_select": [{"name": "option1"}, {"name": "option2"}]}`
- **Date**: `{"date": {"start": "2024-01-01"}}`

## Hosting online (Streamlit Community Cloud)

You can run the app on [Streamlit Community Cloud](https://share.streamlit.io/) so it’s available in the browser.

1. **Push your repo to GitHub** (see above; no `.env` in the repo).
2. **Go to [share.streamlit.io](https://share.streamlit.io/)**, sign in with GitHub, and “New app” from the `church` repo.
3. **Set secrets in the Cloud dashboard:**  
   App → Settings → Secrets. Add the same variables you have in `.env`:
   ```toml
   NOTION_API_KEY = "your_notion_key"
   NOTION_DATABASE_ID = "your_db_id"
   OPENAI_API_KEY = "your_openai_key"
   OPENAI_MODEL = "gpt-3.5-turbo"
   ```
   The app reads these via `os.getenv()`; Streamlit injects them as environment variables. No code changes needed for secrets.

4. **Archive and hymn usage online:**  
   To keep **saved services** and **hymns used in the last 12 weeks** when running online, create two Notion databases and set:
   ```toml
   NOTION_ARCHIVE_DATABASE_ID = "your_archive_database_id"
   NOTION_USAGE_DATABASE_ID = "your_usage_database_id"
   ```
   **Archive DB** — properties: Name (title; Notion default), Service date (date), Occasion (rich text), Scriptures (rich text), Hymns (rich text), Liturgy (rich text), Sermon title (rich text), Selected OT (rich text), Selected NT (rich text), Include communion (checkbox), Saved at (date). **Usage DB** — Title (title), Date (date), Hymn number (number), Hymn title (rich text). Connect your integration to both. If unset, the app uses local `data/` JSON (no persistence on Streamlit Cloud).

## Notes

- Make sure your Notion integration has the correct permissions (read/write as needed)
- The script handles pagination automatically when listing hymns
- Property names are case-sensitive and must match exactly with your Notion database

