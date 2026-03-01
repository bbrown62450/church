#!/usr/bin/env python3
"""
Streamlit UI: worship service planner with hymn suggestions by scripture,
OpenAI liturgy generation, and Word/PDF download.
"""

import html
import logging
import os
from datetime import date
import streamlit as st
from dotenv import load_dotenv

from notion_hymns import NotionHymnsDB
from hymn_utils import get_property_value
from worship_service import (
    hymns_by_scripture,
    hymn_display_info,
    generate_liturgy,
    build_docx,
    suggest_hymns_for_service,
)
from vanderbilt_lectionary import get_readings_for_date_string
from scripture_fetcher import get_passage_text
from hymn_usage import get_recently_used_identifiers, record_usage, is_hymn_recently_used
from service_archive import list_saved_services, save_service, update_service, get_service
from email_send import send_gmail

load_dotenv()

logger = logging.getLogger(__name__)
# Show logs in terminal when running: streamlit run app.py
# Set LOG_LEVEL=DEBUG in .env for verbose output (e.g. scripture fetch details)
if not logging.getLogger().handlers:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format="%(name)s %(levelname)s %(message)s")

# Default Benediction (shorthand; user can paste full Halverson or other text)
DEFAULT_BENEDICTION = "Halverson"

# New Testament books (for OT/NT classification of lectionary readings)
_NT_BOOKS = {
    "matthew", "mark", "luke", "john", "acts", "romans",
    "1 corinthians", "2 corinthians", "galatians", "ephesians", "philippians",
    "colossians", "1 thessalonians", "2 thessalonians", "1 timothy", "2 timothy",
    "titus", "philemon", "hebrews", "james", "1 peter", "2 peter",
    "1 john", "2 john", "3 john", "jude", "revelation",
}


def _expand_ref_options(refs: list) -> list:
    """Expand refs that contain ' or ' into separate options (e.g. gospel choices)."""
    out = []
    for ref in refs:
        if ref and " or " in ref:
            out.extend(p.strip() for p in ref.split(" or ") if p.strip())
        elif ref:
            out.append(ref)
    return out


def _is_nt_ref(ref: str) -> bool:
    """Return True if ref is from the New Testament."""
    s = ref.strip().lower()
    # Check longer names first (e.g. "1 john" before "john")
    for nt_book in sorted(_NT_BOOKS, key=len, reverse=True):
        if s == nt_book or s.startswith(nt_book + " "):
            return True
    return False


def _is_ot_ref(ref: str) -> bool:
    """Return True if ref is from the Old Testament (or Psalms)."""
    return not _is_nt_ref(ref)


st.set_page_config(
    page_title="Worship Service Builder",
    page_icon="✝️",
    layout="wide",
)

# Session state
if "liturgy" not in st.session_state:
    st.session_state.liturgy = None
if "service_date" not in st.session_state:
    st.session_state.service_date = ""
if "occasion" not in st.session_state:
    st.session_state.occasion = ""
if "docx_bytes" not in st.session_state:
    st.session_state.docx_bytes = None
if "docx_bytes_secretary" not in st.session_state:
    st.session_state.docx_bytes_secretary = None
if "docx_bytes_pastor" not in st.session_state:
    st.session_state.docx_bytes_pastor = None
if "lectionary_readings" not in st.session_state:
    st.session_state.lectionary_readings = None
if "scriptures_text" not in st.session_state:
    st.session_state.scriptures_text = ""
if "scripture_full_texts" not in st.session_state:
    st.session_state.scripture_full_texts = {}  # ref -> text
if "selected_ot_ref" not in st.session_state:
    st.session_state.selected_ot_ref = ""
if "selected_nt_ref" not in st.session_state:
    st.session_state.selected_nt_ref = ""
if "liturgy_benediction" not in st.session_state:
    st.session_state.liturgy_benediction = DEFAULT_BENEDICTION
if "last_lectionary_date" not in st.session_state:
    st.session_state.last_lectionary_date = None
if "load_service_id" not in st.session_state:
    st.session_state.load_service_id = None
if "editing_service_id" not in st.session_state:
    st.session_state.editing_service_id = None
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "custom_elements" not in st.session_state:
    st.session_state.custom_elements = []  # [{"label": "...", "text": "...", "insert_after": "..."}]

# Placement options for custom elements (insert_after keys)
CUSTOM_PLACEMENTS = [
    ("call_to_worship", "After Call to Worship"),
    ("opening_prayer", "After Opening Prayer"),
    ("first_hymn", "After First Hymn"),
    ("prayer_of_confession", "After Prayer of Confession"),
    ("assurance", "After Assurance of Pardon"),
    ("prayer_for_illumination", "After Prayer for Illumination"),
    ("ot_reading", "After Old Testament Reading"),
    ("nt_reading", "After New Testament Reading"),
    ("sermon", "After Sermon"),
    ("affirmation_of_faith", "After Affirmation of Faith"),
    ("second_hymn", "After Second Hymn"),
    ("communion", "After Communion"),
    ("prayers_of_the_people", "After Prayers of the People"),
    ("offertory_prayer", "After Offertory Prayer"),
    ("third_hymn", "After Third Hymn"),
    ("benediction", "Before Benediction"),
    ("end", "At the end (after Benediction)"),
]


def get_db():
    try:
        return NotionHymnsDB()
    except ValueError:
        return None


def main():
    # Optional password protection (set APP_PASSWORD in .env or Streamlit secrets)
    app_password = os.getenv("APP_PASSWORD", "").strip()
    if app_password and not st.session_state.get("authenticated"):
        st.title("Worship Service Builder")
        st.caption("Enter the app password to continue.")
        pw = st.text_input("Password", type="password", key="app_pw", placeholder="App password")
        if st.button("Log in", key="login_btn"):
            if pw == app_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password.")
        st.divider()
        st.caption("Set APP_PASSWORD in your environment to protect the app (e.g. email sending).")
        return

    # Restore from archive when Load was clicked
    if st.session_state.get("load_service_id"):
        loaded = get_service(st.session_state.load_service_id)
        st.session_state.load_service_id = None
        if loaded:
            try:
                st.session_state.service_date_picked = date.fromisoformat(loaded["service_date_iso"])
            except Exception:
                pass
            st.session_state.last_lectionary_date = loaded.get("service_date_iso")
            st.session_state.occasion = loaded.get("occasion", "")
            st.session_state.scriptures_text = "\n".join(loaded.get("scriptures") or [])
            st.session_state.liturgy = loaded.get("liturgy") or {}
            st.session_state.sermon_title = loaded.get("sermon_title", "")
            st.session_state.selected_ot_ref = loaded.get("selected_ot_ref", "")
            st.session_state.selected_nt_ref = loaded.get("selected_nt_ref", "")
            st.session_state.include_communion = loaded.get("include_communion", False)
            st.session_state.editing_service_id = loaded.get("id")
            lit = loaded.get("liturgy") or {}
            for section_key in ("call_to_worship", "opening_prayer", "prayer_of_confession", "assurance",
                               "prayer_for_illumination", "prayers_of_the_people", "offertory_prayer", "benediction"):
                st.session_state[f"liturgy_{section_key}"] = lit.get(section_key, "")
            hymns = loaded.get("hymns") or []
            for i, key in enumerate(["opening", "response", "closing"]):
                title = (hymns[i].get("title") or "").strip() if i < len(hymns) else ""
                st.session_state[key] = title.lower() if title else ""
            st.rerun()

    logger.info("Rendering main page (date=%s)", st.session_state.get("last_lectionary_date", "?"))
    st.title("Worship Service Builder")
    st.caption("Suggest hymns by scripture, generate liturgy with AI, export to Word.")

    db = get_db()
    if not db:
        st.warning(
            "Set **NOTION_API_KEY** and **NOTION_DATABASE_ID** in `.env` to use hymn search and suggestions."
        )
        use_notion = False
    else:
        use_notion = True

    # Top: date selector — drives occasion and lectionary
    service_date_picked = st.date_input(
        "Service date",
        value=date(2026, 2, 15),
        key="service_date_picked",
        help="Occasion and lectionary readings load automatically for this date.",
    )
    service_date_str = service_date_picked.strftime("%B %d, %Y")
    date_iso = service_date_picked.isoformat()

    # Auto-load lectionary when date changes — show loading in sidebar and Hymns section so nothing is clickable until done
    if date_iso != st.session_state.last_lectionary_date:
        logger.info("Date changed to %s, loading lectionary…", date_iso)
        with st.sidebar:
            st.header("Service details")
            st.info("Loading occasion and readings…")
        st.header("Hymns")
        try:
            with st.spinner("Loading occasion and readings…"):
                readings = get_readings_for_date_string(service_date_str)
        except Exception as e:
            logger.exception("Lectionary fetch failed")
            st.error(f"Could not load lectionary: {e}")
            readings = None
        logger.info("Lectionary loaded: %s", "yes" if readings else "no")
        st.session_state.last_lectionary_date = date_iso
        if readings:
            st.session_state.lectionary_readings = readings
            st.session_state.occasion = readings.get("liturgical_date") or ""
            st.session_state.scriptures_text = "\n".join(readings.get("scriptures", []))
            st.session_state.scripture_full_texts = {}
            st.session_state.selected_ot_ref = ""
            st.session_state.selected_nt_ref = ""
        else:
            st.session_state.lectionary_readings = None
            st.session_state.occasion = ""
            st.session_state.scriptures_text = ""
        st.rerun()
        return

    # Sidebar: occasion (from date) and scriptures (only after page has loaded / lectionary ready)
    with st.sidebar:
        if app_password:
            if st.button("Log out", key="logout_btn", help="Lock the app (requires password again)."):
                st.session_state.authenticated = False
                st.rerun()
            st.divider()
        st.header("Service details")
        st.caption("Filled from the service date above.")
        # Widget bound to key="occasion"; value comes from session state only (set by date/load/init)
        occasion = st.text_input(
            "Occasion / Sunday",
            key="occasion",
            help="Auto-filled from lectionary; you can edit if needed.",
        )
        if st.session_state.lectionary_readings:
            r = st.session_state.lectionary_readings
            st.caption(f"RCL: {r.get('calendar_date', '')} — {r.get('liturgical_date', '')}")
        st.divider()
        st.subheader("Scripture readings")
        scriptures_text = st.text_area(
            "One per line (e.g. Matthew 17:1–8)",
            height=120,
            placeholder="Filled from lectionary for the selected date.",
            key="scriptures_text",
        )
        scriptures = [s.strip() for s in scriptures_text.splitlines() if s.strip()]

        st.divider()
        st.subheader("Service archive")
        saved = st.session_state.get("_cached_saved_services")
        if saved is None:
            try:
                saved = list_saved_services()
                st.session_state["_cached_saved_services"] = saved
            except Exception as e:
                logger.exception("Failed to load service archive")
                st.error(f"Could not load archive: {e}. Click **Refresh archive** to retry.")
                st.session_state["_cached_saved_services"] = []
                saved = []
        if st.button("Refresh archive", key="refresh_archive", help="Reload services from Notion"):
            st.session_state.pop("_cached_saved_services", None)
            st.rerun()
        if not saved:
            st.caption("No saved services yet. Generate liturgy and click “Save this service to archive”.")
        else:
            for svc in saved[:20]:
                label = f"{svc.get('service_date', '')} — {svc.get('occasion', '')}"
                if st.button(label, key=f"load_{svc.get('id', '')}", help="Load this service into the form"):
                    st.session_state.load_service_id = svc["id"]
                    st.rerun()

    # Lectionary readings: show full text and let user select which two to use (OT / NT)
    if st.session_state.lectionary_readings:
        r = st.session_state.lectionary_readings
        st.header("Lectionary readings")
        labels_refs = [
            ("First reading (OT)", r.get("first_reading")),
            ("Psalm", r.get("psalm")),
            ("Second reading (NT)", r.get("second_reading")),
            ("Gospel", r.get("gospel")),
        ]
        labels_refs = [(label, ref) for label, ref in labels_refs if ref]
        if labels_refs and st.button("Load full text for all readings"):
            logger.info("Load full text clicked, fetching %d passages", len(labels_refs))
            with st.spinner("Fetching passage text…"):
                for _label, ref in labels_refs:
                    cached = st.session_state.scripture_full_texts.get(ref)
                    if ref and (cached is None or cached == "[Could not load text]"):
                        logger.info("Fetching passage: %s", ref)
                        text = get_passage_text(ref)
                        ok = bool(text and text != "[Could not load text]")
                        logger.info("Fetched %s: %s", ref, "ok" if ok else "failed")
                        st.session_state.scripture_full_texts[ref] = text or "[Could not load text]"
            logger.info("All passages fetched, rerunning")
            st.rerun()
        for label, ref in labels_refs:
            with st.expander(f"{label}: {ref}", expanded=False):
                if ref in st.session_state.scripture_full_texts:
                    st.text(st.session_state.scripture_full_texts[ref])
                else:
                    st.caption("Click “Load full text for all readings” to fetch text.")
        # Expand "X or Y" into separate options so user can select each gospel choice
        raw_refs = [ref for _l, ref in labels_refs]
        ref_options = _expand_ref_options(raw_refs)
        ot_options = [r for r in ref_options if _is_ot_ref(r)]
        nt_options = [r for r in ref_options if _is_nt_ref(r)]
        logger.info(
            "Ref options: raw=%s expanded=%s ot=%s nt=%s selected_ot=%s selected_nt=%s",
            raw_refs, ref_options, ot_options, nt_options,
            st.session_state.get("selected_ot_ref"), st.session_state.get("selected_nt_ref"),
        )
        if ref_options:
            def _ref_index(options: list, ref_key: str) -> int:
                sel = st.session_state.get(ref_key) or ""
                if sel in options:
                    return options.index(sel) + 1
                return 0
            col_ot, col_nt = st.columns(2)
            with col_ot:
                ot_choice = st.selectbox(
                    "Use as Old Testament reading",
                    options=[""] + ot_options,
                    format_func=lambda x: x or "— Select —",
                    key="select_ot",
                    index=min(_ref_index(ot_options, "selected_ot_ref"), len(ot_options)),
                )
                st.session_state.selected_ot_ref = ot_choice or ""
            with col_nt:
                nt_choice = st.selectbox(
                    "Use as New Testament reading",
                    options=[""] + nt_options,
                    format_func=lambda x: x or "— Select —",
                    key="select_nt",
                    index=min(_ref_index(nt_options, "selected_nt_ref"), len(nt_options)),
                )
                st.session_state.selected_nt_ref = nt_choice or ""
        st.divider()

    # Hymn suggestions by scripture (any of the readings + optional extra)
    hymn_options_opening = []
    hymn_options_response = []
    hymn_options_closing = []
    cached_all_hymns = st.session_state.get("_cached_all_hymns")

    if use_notion:
        with st.expander("Find hymns matching any of the scriptures", expanded=True):
            extra_scripture = st.text_input(
                "Additional scripture (optional)",
                placeholder="e.g. Matthew 17 or Psalm 99",
                key="extra_scripture",
            )
            refs_to_search = list(scriptures) if scriptures else []
            if extra_scripture and extra_scripture.strip():
                refs_to_search.append(extra_scripture.strip())
            if st.button("Find hymns matching any of the scriptures"):
                if not refs_to_search:
                    st.info("Enter scripture readings above, or add one in the field above.")
                else:
                    logger.info("Searching hymns for refs: %s", refs_to_search)
                    with st.spinner("Searching Notion…"):
                        seen_ids = set()
                        matched = []
                        for ref in refs_to_search:
                            for h in hymns_by_scripture(db, ref, limit=50, all_hymns=cached_all_hymns or None):
                                if h["id"] not in seen_ids:
                                    seen_ids.add(h["id"])
                                    matched.append(h)
                    if not matched:
                        logger.info("No hymns found for refs %s", refs_to_search)
                        st.info("No hymns in your database matching those references. Try shorter refs (e.g. 'Matthew 17').")
                    else:
                        logger.info("Found %d hymns for refs %s", len(matched), refs_to_search)
                        st.session_state["scripture_hymns"] = matched
                        st.session_state["scripture_refs_used"] = refs_to_search

            if "scripture_hymns" in st.session_state:
                refs_used = st.session_state.get("scripture_refs_used", [])
                st.caption("Matching: " + ", ".join(refs_used))
                # Resolve real audio URL from Hymnary only for first 15 to avoid run timeout; rest use constructed URL
                max_resolve = 15
                hymn_list = st.session_state["scripture_hymns"][:20]
                for i, h in enumerate(hymn_list):
                    resolve_audio = i < max_resolve
                    info = hymn_display_info(h, resolve_audio=resolve_audio)
                    num = info.get("number") or "—"
                    audio_url = info.get("audio_url") or ""
                    audio_id = f"audio_{h['id']}_{i}"
                    st.text(f"#{num} — {info['title']}")
                    if audio_url:
                        escaped_url = html.escape(audio_url)
                        safe_id = html.escape(audio_id)
                        st.html(
                            f'<div id="wrap-{safe_id}"><audio id="{safe_id}" controls src="{escaped_url}"></audio></div>'
                        )

    # Main: hymn selection (from Notion list or manual)
    st.header("Hymns")
    exclude_recent_hymns = st.checkbox(
        "Exclude hymns used in the last 12 weeks",
        value=False,
        help="When checked, hymns from recent services are hidden from the dropdowns.",
    )
    if use_notion:
        title_to_info = st.session_state.get("_hymn_title_to_info")
        cached_all_hymns = st.session_state.get("_cached_all_hymns")
        if title_to_info is None:
            try:
                with st.spinner("Loading hymn list from Notion…"):
                    cached_all_hymns = db.list_hymns()
                    title_to_info = {}
                    for h in cached_all_hymns:
                        t = get_property_value(h, "Hymn Title")
                        if t:
                            info = hymn_display_info(h)
                            key = t.strip().lower()
                            title_to_info[key] = info
                    st.session_state["_hymn_title_to_info"] = title_to_info
                    st.session_state["_cached_all_hymns"] = cached_all_hymns
                    logger.info("Cached %d hymns in session state", len(title_to_info))
            except Exception as e:
                logger.exception("Failed to load hymn list")
                st.error(f"Could not load hymns from Notion: {e}. Click **Refresh hymn list** to retry.")
                st.session_state["_hymn_title_to_info"] = {}
                st.session_state["_cached_all_hymns"] = []
                title_to_info = {}
                cached_all_hymns = []
        if st.button("Refresh hymn list", key="refresh_hymns", help="Reload all hymns from Notion"):
            st.session_state.pop("_hymn_title_to_info", None)
            st.session_state.pop("_cached_all_hymns", None)
            st.rerun()
        if exclude_recent_hymns:
            recent_used = get_recently_used_identifiers(weeks=12)
            titles_sorted = sorted(
                k for k in title_to_info
                if not is_hymn_recently_used(
                    title_to_info[k].get("number"),
                    title_to_info[k].get("title") or "",
                    recent_used,
                )
            )
            recent_count = len(title_to_info) - len(titles_sorted)
            if recent_count > 0:
                st.caption(f"Hymns used in the last 12 weeks are excluded ({recent_count} excluded).")
        else:
            titles_sorted = sorted(title_to_info.keys(), key=str.lower)
    else:
        title_to_info = {}
        titles_sorted = []

    def _hymn_label(x):
        if not x:
            return "— Select —"
        return (title_to_info.get(x) or {}).get("title") or x

    if use_notion and titles_sorted and st.button(
        "Suggest hymns (AI)",
        key="suggest_hymns_btn",
        help="Use AI to suggest opening (gathering), response (scripture-based), and closing (joyful) hymns.",
    ):
        progress_bar = st.progress(0, text="Starting…")

        def _on_progress(msg: str, pct: float) -> None:
            progress_bar.progress(min(1.0, pct), text=msg)

        try:
            suggestions = suggest_hymns_for_service(
                db=db,
                occasion=occasion,
                scriptures=scriptures,
                selected_nt_ref=st.session_state.get("selected_nt_ref") or None,
                scripture_full_texts=st.session_state.get("scripture_full_texts") or {},
                scripture_text_fetcher=get_passage_text,
                limit_per_slot=5,
                progress_callback=_on_progress,
                all_hymns=cached_all_hymns or None,
            )
            logger.info("AI suggestions returned: %s", {
                k: [s.get("title") for s in v] for k, v in suggestions.items()
            })

            def _find_key(suggested: dict) -> str:
                t = (suggested.get("title") or "").strip()
                if not t:
                    return ""
                k = t.lower()
                if k in title_to_info:
                    return k
                for key in title_to_info:
                    if (title_to_info[key].get("title") or "").strip().lower() == k:
                        return key
                logger.warning("Suggested title %r not found in hymn list", t)
                return ""

            applied = {}
            for slot in ("opening", "response", "closing"):
                slot_suggestions = suggestions.get(slot, [])
                if not slot_suggestions:
                    logger.warning("No suggestions for slot %r", slot)
                    continue
                found = _find_key(slot_suggestions[0])
                if found and found in title_to_info:
                    st.session_state[slot] = found
                    applied[slot] = title_to_info[found].get("title", found)
                    logger.info("Applied %s: %r -> key %r", slot, slot_suggestions[0].get("title"), found)
                else:
                    logger.warning("Could not match %s suggestion %r to hymn list", slot, slot_suggestions[0].get("title"))

            if applied:
                parts = [f"**{slot.title()}**: {title}" for slot, title in applied.items()]
                st.session_state["_suggestion_message"] = "AI suggestions applied: " + " | ".join(parts)
            else:
                st.session_state["_suggestion_message"] = "AI could not match any suggestions to your hymn list. Try different scriptures or check the logs."
            progress_bar.progress(1.0, text="Done!")
        except Exception as e:
            logger.exception("Suggest hymns failed")
            st.session_state["_suggestion_message"] = f"Could not suggest hymns: {e}"
        st.rerun()

    if "_suggestion_message" in st.session_state:
        msg = st.session_state.pop("_suggestion_message")
        if "Could not" in msg or "could not" in msg:
            st.warning(msg)
        else:
            st.success(msg)

    @st.fragment
    def hymn_selection_fragment():
        """Isolated fragment so changing a hymn only reruns this block (less full-page fade)."""
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("Opening")
            st.caption("Gathering / call to worship")
            if titles_sorted:
                st.selectbox(
                    "Opening hymn",
                    options=[""] + titles_sorted,
                    format_func=_hymn_label,
                    key="opening",
                )
            else:
                st.text_input("Opening hymn (title)", key="open_man")
        with col2:
            st.subheader("After sermon")
            st.caption("Response to scripture (NT reading)")
            if titles_sorted:
                st.selectbox(
                    "Response hymn",
                    options=[""] + titles_sorted,
                    format_func=_hymn_label,
                    key="response",
                )
            else:
                st.text_input("Response hymn (title)", key="resp_man")
        with col3:
            st.subheader("Closing")
            st.caption("Joyful / sending")
            if titles_sorted:
                st.selectbox(
                    "Closing hymn",
                    options=[""] + titles_sorted,
                    format_func=_hymn_label,
                    key="closing",
                )
            else:
                st.text_input("Closing hymn (title)", key="close_man")

    hymn_selection_fragment()

    # Build hymns_ordered from session state so full runs (e.g. Generate, Download) use latest
    hymn_options_opening = []
    hymn_options_response = []
    hymn_options_closing = []
    if titles_sorted:
        opening_choice = st.session_state.get("opening", "")
        if opening_choice:
            hymn_options_opening = [title_to_info[opening_choice]]
        response_choice = st.session_state.get("response", "")
        if response_choice:
            hymn_options_response = [title_to_info[response_choice]]
        closing_choice = st.session_state.get("closing", "")
        if closing_choice:
            hymn_options_closing = [title_to_info[closing_choice]]
    else:
        open_man = st.session_state.get("open_man", "")
        if open_man:
            hymn_options_opening = [{"title": open_man, "number": None, "link": None}]
        resp_man = st.session_state.get("resp_man", "")
        if resp_man:
            hymn_options_response = [{"title": resp_man, "number": None, "link": None}]
        close_man = st.session_state.get("close_man", "")
        if close_man:
            hymn_options_closing = [{"title": close_man, "number": None, "link": None}]

    hymns_ordered = hymn_options_opening + hymn_options_response + hymn_options_closing
    hymns_ordered = [h for h in hymns_ordered if h.get("title")]

    # Sermon title (for Word doc)
    st.text_input("Sermon title (for bulletin)", key="sermon_title", placeholder="[Sermon title]")

    # Optional custom text for each liturgy element (used instead of generating if provided)
    LITURGY_FIELDS = [
        ("call_to_worship", "Call to Worship"),
        ("opening_prayer", "Opening Prayer"),
        ("prayer_of_confession", "Prayer of Confession"),
        ("assurance", "Assurance of Pardon"),
        ("prayer_for_illumination", "Prayer for Illumination"),
        ("prayers_of_the_people", "Prayers of the People"),
        ("offertory_prayer", "Offertory Prayer"),
        ("benediction", "Benediction (default: Halverson)"),
    ]
    with st.expander("Your text (optional — leave blank to generate)"):
        for section_key, label in LITURGY_FIELDS:
            skey = f"liturgy_{section_key}"
            st.text_area(
                label,
                key=skey,
                height=80 if section_key != "prayers_of_the_people" else 140,
                placeholder="Leave blank to generate with AI",
            )

    # Liturgy sections to generate
    st.header("Liturgy to generate")
    sections = []
    if st.checkbox("Call to Worship", value=True):
        sections.append("call_to_worship")
    if st.checkbox("Opening Prayer", value=True):
        sections.append("opening_prayer")
    if st.checkbox("Prayer of Confession", value=True):
        sections.append("prayer_of_confession")
    if st.checkbox("Assurance of Pardon", value=True):
        sections.append("assurance")
    if st.checkbox("Prayer for Illumination", value=True):
        sections.append("prayer_for_illumination")
    if st.checkbox("Prayers of the People", value=False):
        sections.append("prayers_of_the_people")
    if st.checkbox("Offertory Prayer", value=True):
        sections.append("offertory_prayer")
    if st.checkbox("Benediction", value=True):
        sections.append("benediction")

    # Custom elements (e.g. Children's Moment, Special Music)
    with st.expander("Add custom element (e.g. Children's Moment, anthem)"):
        st.caption("Add a custom section with a label and text. It will appear in the Word doc at the chosen position.")
        new_label = st.text_input("Label", key="custom_label", placeholder="e.g. Children's Moment")
        new_text = st.text_area("Text", key="custom_text", height=80, placeholder="Content for the bulletin or order of service")
        new_place = st.selectbox(
            "Place after",
            options=[p[0] for p in CUSTOM_PLACEMENTS],
            format_func=lambda k: next(l for pk, l in CUSTOM_PLACEMENTS if pk == k),
            key="custom_place",
        )
        if st.button("Add custom element", key="add_custom"):
            if new_label and new_label.strip():
                st.session_state.custom_elements.append({
                    "label": new_label.strip(),
                    "text": (new_text or "").strip(),
                    "insert_after": new_place,
                })
                st.rerun()
        for i, ce in enumerate(st.session_state.custom_elements):
            with st.container():
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.caption(f"**{ce['label']}** — placed after {next(l for pk, l in CUSTOM_PLACEMENTS if pk == ce['insert_after'])}")
                with col_b:
                    if st.button("Remove", key=f"rm_custom_{i}"):
                        st.session_state.custom_elements.pop(i)
                        st.rerun()

    if st.button("Generate liturgy", type="primary"):
        st.session_state.editing_service_id = None
        if not os.getenv("OPENAI_API_KEY"):
            st.error("Set **OPENAI_API_KEY** in `.env` to generate liturgy.")
        else:
            user_overrides = {
                section_key: (st.session_state.get(f"liturgy_{section_key}", "") or "").strip()
                for section_key, _ in LITURGY_FIELDS
            }
            user_overrides = {k: v for k, v in user_overrides.items() if v}
            with st.spinner("Writing liturgy…"):
                liturgy = generate_liturgy(
                    occasion=occasion,
                    scriptures=scriptures,
                    hymns=hymns_ordered,
                    sections=sections,
                    user_overrides=user_overrides or None,
                )
            st.session_state.liturgy = liturgy
            st.success("Liturgy generated. Review below and download Word.")

    # Preview
    if st.session_state.liturgy:
        st.header("Preview")
        for key, label in [
            ("call_to_worship", "Call to Worship"),
            ("opening_prayer", "Opening Prayer"),
            ("prayer_of_confession", "Prayer of Confession"),
            ("assurance", "Assurance of Pardon"),
            ("prayer_for_illumination", "Prayer for Illumination"),
            ("prayers_of_the_people", "Prayers of the People"),
            ("offertory_prayer", "Offertory Prayer"),
            ("benediction", "Benediction"),
        ]:
            text = st.session_state.liturgy.get(key)
            if text:
                st.subheader(label)
                if key == "assurance":
                    text = text.rstrip() + "\n\nPeople: Thanks be to God! Amen."
                st.text(text)
                st.divider()

    # Communion: first Sunday of month (default when that's the selected date)
    is_first_sunday = service_date_picked.day <= 7 and service_date_picked.weekday() == 6
    if "include_communion" not in st.session_state:
        st.session_state.include_communion = is_first_sunday
    include_communion = st.checkbox(
        "Include communion liturgy (The Sacrament of the Lord's Supper)",
        key="include_communion",
        help="Checked by default on the first Sunday of the month.",
    )

    # Prepare Word documents (show whenever liturgy is generated)
    if st.session_state.liturgy:
        st.subheader("Prepare Word documents")
        st.caption("Prepare the secretary or pastor copy, then download or email from the section below.")
        col_sec, col_pastor = st.columns(2)
        with col_sec:
            if st.button("Prepare for secretary", key="prep_sec"):
                buf = build_docx(
                    occasion=occasion,
                    date=service_date_str,
                    scriptures=scriptures,
                    hymns=hymns_ordered,
                    liturgy=st.session_state.liturgy,
                    include_placeholders=True,
                    sermon_title=st.session_state.get("sermon_title") or "",
                    selected_ot_ref=st.session_state.get("selected_ot_ref") or None,
                    selected_nt_ref=st.session_state.get("selected_nt_ref") or None,
                    scripture_full_texts=st.session_state.get("scripture_full_texts") or None,
                    include_sermon=False,
                    include_prayers_of_the_people=False,
                    include_communion=include_communion,
                    custom_elements=st.session_state.custom_elements,
                )
                st.session_state.docx_bytes_secretary = buf.getvalue()
                if hymns_ordered and record_usage(service_date_str, hymns_ordered):
                    pass
                st.success("Secretary document ready. Download below.")
                st.rerun()
        with col_pastor:
            if st.button("Prepare for pastor", key="prep_pastor"):
                buf = build_docx(
                    occasion=occasion,
                    date=service_date_str,
                    scriptures=scriptures,
                    hymns=hymns_ordered,
                    liturgy=st.session_state.liturgy,
                    include_placeholders=True,
                    sermon_title=st.session_state.get("sermon_title") or "",
                    selected_ot_ref=st.session_state.get("selected_ot_ref") or None,
                    selected_nt_ref=st.session_state.get("selected_nt_ref") or None,
                    scripture_full_texts=st.session_state.get("scripture_full_texts") or None,
                    include_sermon=True,
                    include_prayers_of_the_people=True,
                    include_communion=include_communion,
                    custom_elements=st.session_state.custom_elements,
                )
                st.session_state.docx_bytes_pastor = buf.getvalue()
                if hymns_ordered and record_usage(service_date_str, hymns_ordered):
                    pass
                st.success("Pastor document ready. Download below.")
                st.rerun()
        if st.button("Save this service to archive", key="save_archive"):
            editing_id = st.session_state.get("editing_service_id")
            save_kw = dict(
                service_date=service_date_str,
                service_date_iso=service_date_picked.isoformat(),
                occasion=occasion,
                scriptures=scriptures,
                hymns=hymns_ordered,
                liturgy=st.session_state.liturgy,
                sermon_title=st.session_state.get("sermon_title") or "",
                selected_ot_ref=st.session_state.get("selected_ot_ref") or "",
                selected_nt_ref=st.session_state.get("selected_nt_ref") or "",
                include_communion=st.session_state.get("include_communion", False),
            )
            try:
                if editing_id:
                    updated = update_service(editing_id, **save_kw)
                    if updated:
                        st.success("Service updated in archive.")
                    else:
                        st.session_state.editing_service_id = None
                        save_service(**save_kw)
                        st.success("Service saved to archive.")
                else:
                    save_service(**save_kw)
                    st.success("Service saved to archive.")
                st.session_state.pop("_cached_saved_services", None)
                st.rerun()
            except Exception as e:
                st.error(f"Archive save failed: {e}")

    # Download prepared documents (show whenever we have them, even after rerun when hymns may be filtered out)
    if st.session_state.docx_bytes_secretary or st.session_state.docx_bytes_pastor:
        st.subheader("Download prepared documents")
        safe_date = service_date_str.replace(", ", "_").replace(" ", "_")
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.docx_bytes_secretary:
                st.download_button(
                    label="Download .docx (for secretary)",
                    data=st.session_state.docx_bytes_secretary,
                    file_name=f"worship_{safe_date}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="dl_secretary",
                )
        with col2:
            if st.session_state.docx_bytes_pastor:
                st.download_button(
                    label="Download .docx (for pastor)",
                    data=st.session_state.docx_bytes_pastor,
                    file_name=f"worship_pastor_{safe_date}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="dl_pastor",
                )
        st.caption("Secretary copy: liturgy only (no sermon, no Prayers of the People). Pastor copy: full order including sermon and Prayers of the People.")

        # Email secretary (when secretary doc is ready)
        if st.session_state.docx_bytes_secretary:
            with st.expander("Email to secretary", expanded=True):
                st.caption("Send the secretary .docx and a friendly message via Gmail.")
                secretary_email = st.text_input(
                    "Secretary email",
                    key="secretary_email",
                    placeholder="secretary@church.org",
                    help="Recipient address.",
                )
                email_message = st.text_area(
                    "Message",
                    key="email_message",
                    height=100,
                    placeholder="Hi! Here’s the worship bulletin for this Sunday. Let me know if you need any changes.",
                    help="This will appear in the email body.",
                )
                if st.button("Send email to secretary", key="send_email_sec"):
                    if not (secretary_email and secretary_email.strip()):
                        st.error("Please enter the secretary’s email.")
                    else:
                        subject = f"Worship service — {service_date_str}"
                        body = (email_message or "Hi! Here’s the worship bulletin for this Sunday.").strip()
                        err = send_gmail(
                            secretary_email.strip(),
                            subject,
                            body,
                            attachment_bytes=st.session_state.docx_bytes_secretary,
                            attachment_filename=f"worship_{safe_date}.docx",
                        )
                        if err:
                            st.error(f"Email failed: {err}")
                        else:
                            st.success("Email sent.")


if __name__ == "__main__":
    main()
