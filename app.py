#!/usr/bin/env python3
"""
Streamlit UI: worship service planner with hymn suggestions by scripture,
OpenAI liturgy generation, and Word/PDF download.
"""

import html
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
)
from vanderbilt_lectionary import get_readings_for_date_string
from scripture_fetcher import get_passage_text
from hymn_usage import get_recently_used_identifiers, record_usage, is_hymn_recently_used
from service_archive import list_saved_services, save_service, get_service

load_dotenv()

# Default Benediction (shorthand; user can paste full Halverson or other text)
DEFAULT_BENEDICTION = "Halverson"

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


def get_db():
    try:
        return NotionHymnsDB()
    except ValueError:
        return None


def main():
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
            lit = loaded.get("liturgy") or {}
            for section_key in ("call_to_worship", "opening_prayer", "prayer_of_confession", "assurance",
                               "prayer_for_illumination", "prayers_of_the_people", "offertory_prayer", "benediction"):
                st.session_state[f"liturgy_{section_key}"] = lit.get(section_key, "")
            hymns = loaded.get("hymns") or []
            for i, key in enumerate(["opening", "response", "closing"]):
                title = (hymns[i].get("title") or "").strip() if i < len(hymns) else ""
                st.session_state[key] = title.lower() if title else ""
            st.rerun()

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

    # Auto-load lectionary when date changes
    if date_iso != st.session_state.last_lectionary_date:
        with st.spinner("Loading occasion and readings…"):
            readings = get_readings_for_date_string(service_date_str)
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

    # Sidebar: occasion (from date) and scriptures
    with st.sidebar:
        st.header("Service details")
        st.caption("Filled from the service date above.")
        occasion = st.text_input(
            "Occasion / Sunday",
            value=st.session_state.occasion or "",
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
        saved = list_saved_services()
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
            with st.spinner("Fetching passage text…"):
                for _label, ref in labels_refs:
                    if ref and ref not in st.session_state.scripture_full_texts:
                        text = get_passage_text(ref)
                        st.session_state.scripture_full_texts[ref] = text or "[Could not load text]"
            st.rerun()
        for label, ref in labels_refs:
            with st.expander(f"{label}: {ref}", expanded=False):
                if ref in st.session_state.scripture_full_texts:
                    st.text(st.session_state.scripture_full_texts[ref])
                else:
                    st.caption("Click “Load full text for all readings” to fetch text.")
        ref_options = [ref for _l, ref in labels_refs]
        if ref_options:
            def _ref_index(ref_key: str) -> int:
                sel = st.session_state.get(ref_key) or ""
                if sel in ref_options:
                    return ref_options.index(sel) + 1
                return 0
            col_ot, col_nt = st.columns(2)
            with col_ot:
                ot_choice = st.selectbox(
                    "Use as Old Testament reading",
                    options=[""] + ref_options,
                    format_func=lambda x: x or "— Select —",
                    key="select_ot",
                    index=min(_ref_index("selected_ot_ref"), len(ref_options)),
                )
                st.session_state.selected_ot_ref = ot_choice or ""
            with col_nt:
                nt_choice = st.selectbox(
                    "Use as New Testament reading",
                    options=[""] + ref_options,
                    format_func=lambda x: x or "— Select —",
                    key="select_nt",
                    index=min(_ref_index("selected_nt_ref"), len(ref_options)),
                )
                st.session_state.selected_nt_ref = nt_choice or ""
        st.divider()

    # Hymn suggestions by scripture (any of the readings + optional extra)
    hymn_options_opening = []
    hymn_options_response = []
    hymn_options_closing = []

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
                    with st.spinner("Searching Notion…"):
                        seen_ids = set()
                        matched = []
                        for ref in refs_to_search:
                            for h in hymns_by_scripture(db, ref, limit=30):
                                if h["id"] not in seen_ids:
                                    seen_ids.add(h["id"])
                                    matched.append(h)
                    if not matched:
                        st.info("No hymns in your database matching those references. Try shorter refs (e.g. 'Matthew 17').")
                    else:
                        st.session_state["scripture_hymns"] = matched
                        st.session_state["scripture_refs_used"] = refs_to_search

            if "scripture_hymns" in st.session_state:
                refs_used = st.session_state.get("scripture_refs_used", [])
                st.caption("Matching: " + ", ".join(refs_used))
                for i, h in enumerate(st.session_state["scripture_hymns"][:20]):
                    info = hymn_display_info(h)
                    num = info.get("number") or "—"
                    st.text(f"#{num} — {info['title']}")
                    if info.get("audio_url"):
                        # Embed URL and unique id so each player has the correct src
                        audio_url = html.escape(info["audio_url"])
                        audio_id = f"audio_{h['id']}_{i}"
                        st.markdown(
                            f'<audio id="{html.escape(audio_id)}" controls src="{audio_url}"></audio>',
                            unsafe_allow_html=True,
                        )

    # Main: hymn selection (from Notion list or manual)
    st.header("Hymns")
    exclude_recent_hymns = st.checkbox(
        "Exclude hymns used in the last 12 weeks",
        value=False,
        help="When checked, hymns from recent services are hidden from the dropdowns.",
    )
    if use_notion:
        all_hymns = db.list_hymns()
        title_to_info = {}
        for h in all_hymns:
            t = get_property_value(h, "Hymn Title")
            if t:
                info = hymn_display_info(h)
                key = t.strip().lower()
                title_to_info[key] = info
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

    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Opening")
        if titles_sorted:
            opening_choice = st.selectbox(
                "Opening hymn",
                options=[""] + titles_sorted,
                format_func=_hymn_label,
                key="opening",
            )
            if opening_choice:
                hymn_options_opening = [title_to_info[opening_choice]]
        else:
            opening_manual = st.text_input("Opening hymn (title)", key="open_man")
            if opening_manual:
                hymn_options_opening = [{"title": opening_manual, "number": None, "link": None}]
    with col2:
        st.subheader("After sermon")
        if titles_sorted:
            response_choice = st.selectbox(
                "Response hymn",
                options=[""] + titles_sorted,
                format_func=_hymn_label,
                key="response",
            )
            if response_choice:
                hymn_options_response = [title_to_info[response_choice]]
        else:
            response_manual = st.text_input("Response hymn (title)", key="resp_man")
            if response_manual:
                hymn_options_response = [{"title": response_manual, "number": None, "link": None}]
    with col3:
        st.subheader("Closing")
        if titles_sorted:
            closing_choice = st.selectbox(
                "Closing hymn",
                options=[""] + titles_sorted,
                format_func=_hymn_label,
                key="closing",
            )
            if closing_choice:
                hymn_options_closing = [title_to_info[closing_choice]]
        else:
            closing_manual = st.text_input("Closing hymn (title)", key="close_man")
            if closing_manual:
                hymn_options_closing = [{"title": closing_manual, "number": None, "link": None}]

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

    if st.button("Generate liturgy", type="primary"):
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
                )
                st.session_state.docx_bytes_pastor = buf.getvalue()
                if hymns_ordered and record_usage(service_date_str, hymns_ordered):
                    pass
                st.success("Pastor document ready. Download below.")
                st.rerun()
        if st.button("Save this service to archive", key="save_archive"):
            save_service(
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
            st.success("Service saved to archive.")
            st.rerun()

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


if __name__ == "__main__":
    main()
