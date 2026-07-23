#!/usr/bin/env python3
"""
Streamlit UI: worship service planner with hymn suggestions by scripture,
OpenAI liturgy generation, and Word/PDF download. Multi-church: each user signs
in with Google and works within a church they belong to.
"""

import logging
import os
from datetime import date
import streamlit as st
from dotenv import load_dotenv

from worship_service import (
    generate_liturgy,
    build_docx,
    hymns_by_scripture,
    hymn_display_info,
    suggest_hymns_for_service,
)
from vanderbilt_lectionary import get_readings_for_date_string
from scripture_fetcher import (
    get_passage_text,
    available_translations,
    translation_label,
    DEFAULT_TRANSLATION,
)
from hymn_usage import get_recently_used_identifiers, record_usage, is_hymn_recently_used
from service_archive import list_saved_services, save_service, update_service, get_service
from email_contacts import list_contacts
from repos.hymns import list_hymns
from repos.churches import (
    list_user_churches, create_church, get_church_prompts, get_church_translation,
)
from repos.invites import accept_invite
import google_oauth

from db import init_db
from auth import require_login, do_logout
from tenancy import require_active_church
from ui_helpers import (
    capture_query_params,
    clear_oauth_query_params,
    build_title_to_info,
    pick_invite_code,
    coerce_selectbox_value,
)
import views.settings as settings_page

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
if "lectionary_readings_list" not in st.session_state:
    st.session_state.lectionary_readings_list = []
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


@st.cache_resource
def _init_db_once():
    """Create the schema once per process (cached resource)."""
    init_db()
    return True


def _handle_gmail_callback(user):
    """Process the manual gmail.send OAuth redirect (?code=&state=). Only reached
    when should_handle_gmail_callback() is True AND the user is logged in."""
    qp = st.query_params
    code = qp.get("code")
    returned_state = qp.get("state")
    # CSRF: state must be present, single-use, and bound to THIS user (spec §4.3).
    state_user = google_oauth.consume_state(returned_state) if returned_state else None
    if state_user is None or str(state_user) != str(user["user_id"]):
        st.session_state.oauth_error = "Sign-in expired or was invalid. Please try again."
        clear_oauth_query_params(qp)
        st.rerun()
        return
    try:
        # Refuses unless the Google-returned email == the logged-in user (spec §4.4).
        google_oauth.exchange_code(code, user["user_id"])
    except Exception as e:  # noqa: BLE001 - surface the reason to the user
        st.session_state.oauth_error = str(e)
    clear_oauth_query_params(qp)
    st.rerun()


def _render_gmail_sidebar(user_id, user_email):
    """Sidebar controls for connecting / disconnecting the caller's own Gmail."""
    with st.sidebar:
        st.divider()
        st.subheader("✉️ Gmail")
        if st.session_state.get("oauth_error"):
            st.error(st.session_state.pop("oauth_error"))
        if not google_oauth.is_configured():
            st.caption("Per-user Gmail sending isn't configured on this deployment.")
            return
        if google_oauth.is_connected(user_id):
            st.success(f"Connected: {user_email}")
            if st.button("Disconnect", key="gmail_disconnect"):
                google_oauth.disconnect(user_id)
                st.rerun()
        else:
            st.caption("Connect Google to send worship emails from your own Gmail.")
            st.link_button(
                "Connect your Gmail",
                google_oauth.build_auth_url(google_oauth.create_state(user_id)),
            )


CHURCH_SCOPED_SESSION_KEYS = (
    "_cached_all_hymns", "_hymn_title_to_info", "_cached_saved_services",
    "scripture_hymns", "scripture_refs_used", "opening", "response", "closing",
    "open_man", "resp_man", "close_man", "editing_service_id", "load_service_id",
    "liturgy", "liturgy_call_to_worship", "liturgy_opening_prayer",
    "liturgy_prayer_of_confession", "liturgy_assurance",
    "liturgy_prayer_for_illumination", "liturgy_prayers_of_the_people",
    "liturgy_offertory_prayer", "liturgy_benediction", "include_communion",
    "custom_elements", "selected_ot_ref", "selected_nt_ref", "bible_translation",
)


def _reset_church_scoped_state():
    for k in CHURCH_SCOPED_SESSION_KEYS:
        st.session_state.pop(k, None)


def render_church_switcher(user, active):
    """Sidebar switcher for users in >1 church. Switching resets all church-scoped
    state so a stale previous-church read is impossible (spec §5)."""
    churches = list_user_churches(user["user_id"])
    if len(churches) <= 1:
        return
    with st.sidebar:
        labels = {c["name"]: c["id"] for c in churches}
        current_name = active["name"]
        picked = st.selectbox(
            "Church", list(labels.keys()),
            index=list(labels.keys()).index(current_name) if current_name in labels else 0,
            key="church_switcher",
        )
        if labels[picked] != active["church_id"]:
            _reset_church_scoped_state()
            st.session_state["active_church_id"] = str(labels[picked])
            st.rerun()


def safe_hymn_selectbox(label, options, key, format_func):
    """A hymn selectbox that first coerces a stale stored value to '' (guarding
    against StreamlitAPIException when the church's options changed), then renders."""
    current = st.session_state.get(key, "")
    coerced = coerce_selectbox_value(current, options)
    if coerced != current:
        st.session_state[key] = coerced
    return st.selectbox(label, options=options, key=key, format_func=format_func)


def render_onboarding(user):
    """Signed-in user with no membership: create a church or join by invite."""
    user_id = user["user_id"]
    st.title("Welcome to Worship Service Builder")
    st.caption(f"Signed in as {user['email']}. You don't belong to a church yet.")

    pending_code = st.session_state.get("pending_invite_code")
    if pending_code:
        st.info("You opened an invite link. Review and accept it below.")

    tab_join, tab_create = st.tabs(["Join a church", "Create a church"])

    with tab_join:
        typed = st.text_input("Invite code", value=pending_code or "", key="onboard_invite_code")
        if st.button("Join church", key="onboard_join"):
            code = pick_invite_code(pending_code, typed)
            if not code:
                st.error("Enter an invite code, or open your invite link again.")
            else:
                try:
                    ok, msg = accept_invite(code, user_id)
                except Exception as e:  # noqa: BLE001
                    ok, msg = False, str(e)
                if ok:
                    st.session_state.pop("pending_invite_code", None)
                    st.query_params.clear()  # onboarding is terminal; safe to clear here
                    st.success(msg or "Joined. Loading your church…")
                    st.rerun()
                else:
                    st.error(msg or "That invite code is not valid.")

    with tab_create:
        with st.form("onboard_create_church"):
            name = st.text_input("Church name", key="onboard_church_name")
            timezone = st.text_input("Timezone", value="America/New_York",
                                     key="onboard_church_tz",
                                     help="e.g. America/New_York — drives first-Sunday and the 12-week window.")
            if st.form_submit_button("Create church"):
                if not name.strip():
                    st.error("Church name is required.")
                elif not timezone.strip():
                    st.error("Timezone is required.")
                else:
                    try:
                        cid = create_church(name=name.strip(),
                                            timezone=timezone.strip(),
                                            owner_user_id=user_id)
                        st.session_state["active_church_id"] = str(cid)
                        st.success("Church created. Loading…")
                        st.rerun()
                    except Exception as e:  # noqa: BLE001
                        st.error(f"Could not create church: {e}")


def main():
    # 1) FIRST LINE: capture untrusted ?invite=/?church= before any gate/OAuth.
    capture_query_params(st.query_params, st.session_state)

    # 2) Ensure the schema exists (cached, once per process).
    _init_db_once()

    # 3) Identity via Streamlit-native Google OIDC. Stops on the login screen if
    #    not signed in; returns {"user_id","email","name","picture"}.
    user = require_login()

    # 4) Manual gmail.send OAuth callback — only OUR flow, only while logged in.
    if google_oauth.should_handle_gmail_callback(st.query_params, True):
        _handle_gmail_callback(user)

    # 5) Server-verified active church (role re-derived per request).
    active = require_active_church(user["user_id"])
    if active is None:
        render_onboarding(user)
        return

    render_church_switcher(user, active)
    _render_gmail_sidebar(user["user_id"], user["email"])
    with st.sidebar:
        st.divider()
        st.caption(f"Signed in as {user['email']} · {active['name']}")
        if st.button("Log out", key="logout_btn"):
            do_logout()

    def _service_builder_page():
        render_service_builder(user, active)

    def _settings_page():
        settings_page.render_settings_page(user, active)

    nav = st.navigation([
        st.Page(_service_builder_page, title="Service Builder", icon="✝️", default=True),
        st.Page(_settings_page, title="Settings", icon="⚙️"),
    ])
    nav.run()


def render_service_builder(user, active):
    church_id = active["church_id"]
    user_id = user["user_id"]

    # Active Bible translation for on-screen passage text (per-church default,
    # overridable per session via the picker in the Readings section).
    if "bible_translation" not in st.session_state:
        st.session_state["bible_translation"] = (
            get_church_translation(church_id) or DEFAULT_TRANSLATION
        )
    _avail_ids = [t[0] for t in available_translations()]
    if st.session_state["bible_translation"] not in _avail_ids:
        st.session_state["bible_translation"] = DEFAULT_TRANSLATION

    # Restore from archive when Load was clicked
    if st.session_state.get("load_service_id"):
        loaded = get_service(st.session_state.load_service_id, church_id)
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

    # Service date + occasion + scriptures: top of the main screen.
    # (col_occasion/col_scripts are filled AFTER the lectionary block below,
    # because that block writes st.session_state.occasion/scriptures_text and
    # Streamlit forbids writing a widget's session value once the widget is
    # instantiated.)
    col_date, col_occasion, col_scripts = st.columns([1, 2, 2])
    with col_date:
        service_date_picked = st.date_input(
            "Service date",
            value=date.today(),
            key="service_date_picked",
            help="Occasion and lectionary readings load automatically for this date.",
        )

    service_date_str = service_date_picked.strftime("%B %d, %Y")
    date_iso = service_date_picked.isoformat()

    # Auto-load lectionary when date changes
    if date_iso != st.session_state.last_lectionary_date:
        logger.info(
            "Date changed: date_iso=%s, last_lectionary_date=%s, service_date_str=%s",
            date_iso, st.session_state.last_lectionary_date, service_date_str,
        )
        st.info("Loading occasion and readings…")
        try:
            with st.spinner("Loading occasion and readings…"):
                readings_list = get_readings_for_date_string(service_date_str)
        except Exception as e:
            logger.exception("Lectionary fetch failed")
            st.error(f"Could not load lectionary: {e}")
            readings_list = []
        logger.info("Lectionary result: %d reading set(s)", len(readings_list))
        st.session_state.last_lectionary_date = date_iso
        st.session_state.lectionary_readings_list = readings_list
        if readings_list:
            # Default to the last set (Passion for Palm Sunday, or the only set otherwise)
            readings = readings_list[-1]
            st.session_state.lectionary_readings = readings
            liturgical_date = (readings.get("liturgical_date") or "").strip()
            st.session_state.occasion = liturgical_date
            logger.info("Set session_state.occasion=%r (from liturgical_date)", liturgical_date)
            st.session_state.scriptures_text = "\n".join(readings.get("scriptures", []))
            st.session_state.scripture_full_texts = {}
            st.session_state.selected_ot_ref = ""
            st.session_state.selected_nt_ref = ""
        else:
            st.session_state.lectionary_readings = None
            st.session_state.lectionary_readings_list = []
            st.session_state.occasion = ""
            st.session_state.scriptures_text = ""
            logger.info("No readings; set session_state.occasion=''")
        logger.info("About to st.rerun(); session_state.occasion=%r", st.session_state.get("occasion"))
        st.rerun()
        return

    # Occasion: fills the top-row column next to the date (see note above).
    logger.info(
        "Rendering occasion: last_lectionary_date=%s, occasion=%r, lectionary_readings=%s",
        st.session_state.last_lectionary_date,
        st.session_state.get("occasion"),
        "present" if st.session_state.get("lectionary_readings") else "None",
    )
    with col_occasion:
        # When multiple reading sets exist (e.g. Palm Sunday: Palms + Passion), let user switch.
        readings_list = st.session_state.get("lectionary_readings_list") or []
        if len(readings_list) > 1:
            liturgy_names = [rd["liturgical_date"] for rd in readings_list]
            current = st.session_state.lectionary_readings
            current_idx = liturgy_names.index(current["liturgical_date"]) if current and current["liturgical_date"] in liturgy_names else len(liturgy_names) - 1

            def _on_liturgy_change():
                idx = liturgy_names.index(st.session_state.liturgy_selector)
                rd = readings_list[idx]
                st.session_state.lectionary_readings = rd
                st.session_state.occasion = rd["liturgical_date"]
                st.session_state.scriptures_text = "\n".join(rd.get("scriptures", []))
                st.session_state.scripture_full_texts = {}
                st.session_state.selected_ot_ref = ""
                st.session_state.selected_nt_ref = ""

            st.radio(
                "Liturgy",
                options=liturgy_names,
                index=current_idx,
                key="liturgy_selector",
                on_change=_on_liturgy_change,
                help="This date has multiple liturgies in the RCL. Select which one to use.",
            )
        occasion = st.text_input(
            "Occasion / Sunday",
            value=st.session_state.get("occasion", ""),
            key="occasion",
            help="Auto-filled from lectionary; you can edit if needed.",
        )
        if st.session_state.lectionary_readings:
            r = st.session_state.lectionary_readings
            st.caption(f"RCL: {r.get('calendar_date', '')} — {r.get('liturgical_date', '')}")

    # Scripture readings: fills the third top-row column (deferred, see note above).
    with col_scripts:
        scriptures_text = st.text_area(
            "Scripture readings (one per line)",
            height=120,
            placeholder="Filled from lectionary for the selected date.",
            key="scriptures_text",
            help="e.g. Matthew 17:1–8 — auto-filled from the lectionary; edit as needed.",
        )
    scriptures = [s.strip() for s in scriptures_text.splitlines() if s.strip()]

    # Sidebar: the service archive
    with st.sidebar:
        st.subheader("Service archive")
        saved = st.session_state.get("_cached_saved_services")
        if saved is None:
            try:
                saved = list_saved_services(church_id)
                st.session_state["_cached_saved_services"] = saved
            except Exception as e:
                logger.exception("Failed to load service archive")
                st.error(f"Could not load archive: {e}. Click **Refresh archive** to retry.")
                st.session_state["_cached_saved_services"] = []
                saved = []
        if st.button("Refresh archive", key="refresh_archive", help="Reload services"):
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

    # Readings: show full text and let user select which two to use (OT / NT).
    # Sourced from the sidebar Scripture list, so user-entered references work
    # even without a lectionary, and edits flow through to the OT/NT pickers.
    if scriptures:
        st.header("Readings")
        if st.session_state.lectionary_readings:
            r = st.session_state.lectionary_readings
            st.caption(f"RCL: {r.get('calendar_date', '')} — {r.get('liturgical_date', '')}. Edit the Scripture list in the sidebar to use your own.")
        else:
            st.caption("Using the Scripture list from the sidebar. Edit it to add or change references.")

        # Translation picker (on-screen study text only — the bulletin lists references)
        trans_opts = available_translations()
        trans_ids = [t[0] for t in trans_opts]
        trans_labels = {t[0]: t[1] for t in trans_opts}
        cur_trans = st.session_state.get("bible_translation", DEFAULT_TRANSLATION)
        col_t, _ = st.columns([1, 2])
        with col_t:
            picked_trans = st.selectbox(
                "Bible translation",
                trans_ids,
                index=trans_ids.index(cur_trans) if cur_trans in trans_ids else 0,
                format_func=lambda tid: trans_labels.get(tid, tid),
                key="translation_picker",
                help="Used for the passage text shown below. This is study text only — "
                     "the bulletin lists the references, not the verse text.",
            )
        if picked_trans != st.session_state.get("bible_translation"):
            st.session_state["bible_translation"] = picked_trans
            st.session_state.scripture_full_texts = {}   # cached in the old translation
            st.rerun()
        translation = st.session_state["bible_translation"]
        st.caption(f"Passage text shown in **{translation_label(translation)}**.")

        if st.button("Load full text for all readings"):
            logger.info("Load full text clicked, fetching %d passages (%s)", len(scriptures), translation)
            with st.spinner("Fetching passage text…"):
                for ref in scriptures:
                    cached = st.session_state.scripture_full_texts.get(ref)
                    if ref and (cached is None or cached == "[Could not load text]"):
                        logger.info("Fetching passage: %s", ref)
                        text = get_passage_text(ref, translation=translation)
                        ok = bool(text and text != "[Could not load text]")
                        logger.info("Fetched %s: %s", ref, "ok" if ok else "failed")
                        st.session_state.scripture_full_texts[ref] = text or "[Could not load text]"
            logger.info("All passages fetched, rerunning")
            st.rerun()
        for ref in scriptures:
            with st.expander(ref, expanded=False):
                if ref in st.session_state.scripture_full_texts:
                    st.text(st.session_state.scripture_full_texts[ref])
                else:
                    st.caption("Click “Load full text for all readings” to fetch text.")
        # Expand "X or Y" into separate options so user can select each choice
        ref_options = _expand_ref_options(scriptures)
        ot_options = [r for r in ref_options if _is_ot_ref(r)]
        nt_options = [r for r in ref_options if _is_nt_ref(r)]
        logger.info(
            "Ref options: raw=%s expanded=%s ot=%s nt=%s selected_ot=%s selected_nt=%s",
            scriptures, ref_options, ot_options, nt_options,
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

    # Load this church's hymnal once per session (used by the scripture search,
    # AI suggestions, and the hymn pickers below).
    all_hymns = st.session_state.get("_cached_all_hymns")
    if all_hymns is None:
        try:
            with st.spinner("Loading this church's hymnal…"):
                all_hymns = list_hymns(church_id)
            st.session_state["_cached_all_hymns"] = all_hymns
        except Exception as e:  # noqa: BLE001
            logger.exception("Failed to load hymns")
            st.error(f"Could not load hymns: {e}. Click **Refresh hymn list** to retry.")
            all_hymns = []
            st.session_state["_cached_all_hymns"] = []

    # Hymn search by scripture (in-memory over this church's hymnal)
    if all_hymns:
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
                    with st.spinner("Searching hymnal…"):
                        seen_ids = set()
                        matched = []
                        for ref in refs_to_search:
                            for h in hymns_by_scripture(None, ref, limit=50, all_hymns=all_hymns):
                                if h["id"] not in seen_ids:
                                    seen_ids.add(h["id"])
                                    matched.append(h)
                    if not matched:
                        logger.info("No hymns found for refs %s", refs_to_search)
                        st.info("No hymns in your hymnal matching those references. Try shorter refs (e.g. 'Matthew 17').")
                    else:
                        logger.info("Found %d hymns for refs %s", len(matched), refs_to_search)
                        st.session_state["scripture_hymns"] = matched
                        st.session_state["scripture_refs_used"] = refs_to_search

            if "scripture_hymns" in st.session_state:
                refs_used = st.session_state.get("scripture_refs_used", [])
                st.caption("Matching: " + ", ".join(refs_used))
                hymn_list = st.session_state["scripture_hymns"][:20]
                for h in hymn_list:
                    info = hymn_display_info(h)
                    num = info.get("number") or "—"
                    hymn_link = info.get("link") or ""
                    if hymn_link:
                        # Link to the hymn's Hymnary page (where audio can be played
                        # in context) rather than hotlinking their media files.
                        st.markdown(f"[#{num} — {info['title']}]({hymn_link}) · [▶ listen]({hymn_link})")
                    else:
                        st.text(f"#{num} — {info['title']}")
                st.caption(
                    "Hymn information and links courtesy of [Hymnary.org](https://hymnary.org). "
                    "Individual hymns may carry their own copyright — see each hymn's page."
                )

    # Main: hymn selection (from this church's DB hymnal)
    st.header("Hymns")
    exclude_recent_hymns = st.checkbox(
        "Exclude hymns used in the last 12 weeks",
        value=False,
        help="When checked, hymns from recent services are hidden from the dropdowns.",
    )
    if st.button("Refresh hymn list", key="refresh_hymns"):
        st.session_state.pop("_cached_all_hymns", None)
        st.rerun()

    title_to_info = build_title_to_info(all_hymns)
    if not title_to_info:
        # Explicit empty-hymnal message — never a silent swap to free-text inputs.
        st.warning(
            "This church's hymnal is empty. Add hymns on the **Settings → Hymns** "
            "page to enable hymn selection."
        )

    if exclude_recent_hymns and title_to_info:
        recent_used = get_recently_used_identifiers(church_id, weeks=12)
        titles_sorted = sorted(
            k for k in title_to_info
            if not is_hymn_recently_used(
                title_to_info[k].get("number"), title_to_info[k].get("title") or "", recent_used)
        )
        excluded = len(title_to_info) - len(titles_sorted)
        if excluded > 0:
            st.caption(f"Hymns used in the last 12 weeks are excluded ({excluded} excluded).")
    else:
        titles_sorted = sorted(title_to_info.keys(), key=str.lower)

    def _hymn_label(x):
        if not x:
            return "— Select —"
        return (title_to_info.get(x) or {}).get("title") or x

    if titles_sorted and st.button(
        "Suggest hymns (AI)",
        key="suggest_hymns_btn",
        help="Use AI to suggest opening (gathering), response (scripture-based), and closing (joyful) hymns.",
    ):
        progress_bar = st.progress(0, text="Starting…")

        def _on_progress(msg: str, pct: float) -> None:
            progress_bar.progress(min(1.0, pct), text=msg)

        try:
            suggestions = suggest_hymns_for_service(
                db=None,
                occasion=occasion,
                scriptures=scriptures,
                selected_nt_ref=st.session_state.get("selected_nt_ref") or None,
                scripture_full_texts=st.session_state.get("scripture_full_texts") or {},
                scripture_text_fetcher=lambda ref: get_passage_text(
                    ref, translation=st.session_state.get("bible_translation", DEFAULT_TRANSLATION)
                ),
                limit_per_slot=5,
                progress_callback=_on_progress,
                all_hymns=all_hymns,
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
        except Exception as e:  # noqa: BLE001
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
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("Opening")
            st.caption("Gathering / call to worship")
            if titles_sorted:
                safe_hymn_selectbox("Opening hymn", [""] + titles_sorted, "opening", _hymn_label)
        with col2:
            st.subheader("After sermon")
            st.caption("Response to scripture (NT reading)")
            if titles_sorted:
                safe_hymn_selectbox("Response hymn", [""] + titles_sorted, "response", _hymn_label)
        with col3:
            st.subheader("Closing")
            st.caption("Joyful / sending")
            if titles_sorted:
                safe_hymn_selectbox("Closing hymn", [""] + titles_sorted, "closing", _hymn_label)

    hymn_selection_fragment()

    hymns_ordered = []
    for slot in ("opening", "response", "closing"):
        choice = st.session_state.get(slot, "")
        if choice and choice in title_to_info:
            hymns_ordered.append(title_to_info[choice])

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
                    prompt_overrides=get_church_prompts(church_id),
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
        st.caption("Prepare the bulletin copy or the pastor's copy, then download or email from the section below.")
        col_sec, col_pastor = st.columns(2)
        with col_sec:
            if st.button("Prepare bulletin copy", key="prep_sec", help="Liturgy only — for whoever assembles the bulletin."):
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
                    include_prayers_of_the_people=False,
                    include_communion=include_communion,
                    custom_elements=st.session_state.custom_elements,
                )
                st.session_state.docx_bytes_secretary = buf.getvalue()
                if hymns_ordered:
                    record_usage(church_id, service_date_str, hymns_ordered)
                st.success("Bulletin copy ready. Download below.")
                st.rerun()
        with col_pastor:
            if st.button("Prepare pastor's copy", key="prep_pastor", help="Full order of worship, including sermon and Prayers of the People."):
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
                if hymns_ordered:
                    record_usage(church_id, service_date_str, hymns_ordered)
                st.success("Pastor's copy ready. Download below.")
                st.rerun()
        editing_id = st.session_state.get("editing_service_id")
        # Clear editing_id if user switched to a different service date
        if editing_id:
            existing = get_service(editing_id, church_id)
            if existing and existing.get("service_date_iso") != date_iso:
                st.session_state.editing_service_id = None
                editing_id = None
        save_btn_label = "Save changes" if editing_id else "Save this service to archive"
        if st.button(save_btn_label, key="save_archive"):
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
                    updated = update_service(editing_id, church_id, **save_kw)
                    if updated:
                        st.success("Service updated in archive.")
                    else:
                        st.session_state.editing_service_id = None
                        out = save_service(church_id=church_id, created_by=user_id, **save_kw)
                        st.session_state.editing_service_id = out.get("id")
                        st.success("Service saved to archive.")
                else:
                    out = save_service(church_id=church_id, created_by=user_id, **save_kw)
                    st.session_state.editing_service_id = out.get("id")
                    st.success("Service saved to archive.")
                st.session_state.pop("_cached_saved_services", None)
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"Archive save failed: {e}")

    # Download prepared documents (show whenever we have them, even after rerun when hymns may be filtered out)
    if st.session_state.docx_bytes_secretary or st.session_state.docx_bytes_pastor:
        st.subheader("Download prepared documents")
        safe_date = service_date_str.replace(", ", "_").replace(" ", "_")
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.docx_bytes_secretary:
                st.download_button(
                    label="Download .docx (bulletin copy)",
                    data=st.session_state.docx_bytes_secretary,
                    file_name=f"worship_{safe_date}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="dl_secretary",
                )
        with col2:
            if st.session_state.docx_bytes_pastor:
                st.download_button(
                    label="Download .docx (pastor's copy)",
                    data=st.session_state.docx_bytes_pastor,
                    file_name=f"worship_pastor_{safe_date}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="dl_pastor",
                )
        st.caption("Bulletin copy: liturgy only (no sermon, no Prayers of the People) — for whoever assembles the bulletin. Pastor's copy: full order including sermon and Prayers of the People.")

        # Email the bulletin copy (when it is ready)
        if st.session_state.docx_bytes_secretary:
            with st.expander("Email bulletin copy", expanded=True):
                st.caption("Send the bulletin .docx and a friendly message via Gmail.")
                connected = google_oauth.is_configured() and google_oauth.is_connected(user_id)
                if google_oauth.is_configured():
                    if connected:
                        st.caption(f"Sending as **{user['email']}** (your connected Gmail).")
                    else:
                        st.warning("Connect your Gmail in the sidebar to send from your own account.")
                contacts = list_contacts(church_id)
                contact_options = [f"{c['name']} <{c['email']}>" for c in contacts]
                email_to_contact = {f"{c['name']} <{c['email']}>": c["email"] for c in contacts}
                selected_contacts = st.multiselect(
                    "Recipients", options=contact_options,
                    key="email_recipients", help="Select one or more saved contacts.")
                additional_emails = st.text_input(
                    "Additional emails (comma-separated)", key="secretary_email_extra",
                    placeholder="other@example.com")
                email_message = st.text_area("Message", key="email_message", height=100)
                if st.button("Send email", key="send_email_sec"):
                    recipient_emails = [email_to_contact[c] for c in selected_contacts]
                    if additional_emails and additional_emails.strip():
                        recipient_emails.extend(
                            e.strip() for e in additional_emails.split(",") if e.strip())
                    if not recipient_emails:
                        st.error("Please select at least one recipient or enter an email address.")
                    elif not connected:
                        st.error("Connect your Gmail in the sidebar first, then try again.")
                    else:
                        subject = f"Worship service — {service_date_str}"
                        body = (email_message or "Hi! Here’s the worship bulletin for this Sunday.").strip()
                        attachment_filename = f"worship_{safe_date}.docx"
                        err = google_oauth.send_email(
                            user_id, recipient_emails, subject, body,
                            attachment_bytes=st.session_state.docx_bytes_secretary,
                            attachment_filename=attachment_filename,
                        )
                        if err:
                            st.error(f"Email failed: {err}")
                        else:
                            st.success(f"Email sent to {len(recipient_emails)} recipient(s).")


if __name__ == "__main__":
    main()
