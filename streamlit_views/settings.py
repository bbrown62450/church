#!/usr/bin/env python3
"""Settings page: church profile, contacts, hymn library, members, invites.

Every state-changing action goes through a helper that RE-CHECKS the caller's
role server-side (spec §2 active-church guard, §5 roles) and raises
NotAuthorizedError when the caller lacks permission — hiding UI is not enough.
Streamlit rendering is a thin shell over these tested helpers.
"""
import logging

import streamlit as st

from db import session_scope
from db.models import Church
from tenancy import is_admin
from repos.memberships import (
    get_role, set_role, remove_membership, list_members, LastAdminError,
)
from repos.churches import (
    soft_delete_church,
    get_church_prompts, set_church_prompts,
    get_church_translation, set_church_translation,
)
from repos.invites import create_invite, list_invites, revoke_invite
import email_contacts
from repos import hymns as hymns_repo
import liturgy_prompts
from scripture_fetcher import available_translations, translation_label, DEFAULT_TRANSLATION

logger = logging.getLogger(__name__)


class NotAuthorizedError(Exception):
    """Raised when a caller attempts an action their role does not permit."""


def _require_admin(user_id, church_id):
    role = get_role(user_id, church_id)
    if not is_admin(role):
        raise NotAuthorizedError("You must be an admin to do that.")
    return role


def _require_member(user_id, church_id):
    role = get_role(user_id, church_id)
    if role is None:
        raise NotAuthorizedError("You are not a member of this church.")
    return role


def _require_owner(user_id, church_id):
    role = get_role(user_id, church_id)
    if role != "owner":
        raise NotAuthorizedError("Only the owner can do that.")
    return role


# --------------------------------------------------------------------------- #
# Action helpers (no Streamlit; unit-tested)
# --------------------------------------------------------------------------- #
def submit_profile_update(user_id, church_id, *, name, timezone):
    _require_admin(user_id, church_id)
    name = (name or "").strip()
    timezone = (timezone or "").strip()
    if not name:
        raise ValueError("Church name is required.")
    if not timezone:
        raise ValueError("Timezone is required.")
    with session_scope() as s:
        church = s.get(Church, church_id)
        if church is None or church.deleted_at is not None:
            raise ValueError("Church not found.")
        church.name = name
        church.timezone = timezone


def submit_add_contact(user_id, church_id, *, name, email):
    _require_admin(user_id, church_id)
    email = (email or "").strip()
    if not email:
        raise ValueError("Email is required.")
    return email_contacts.add_contact(church_id, name=(name or "").strip(), email=email)


def submit_delete_contact(user_id, church_id, contact_id):
    _require_admin(user_id, church_id)
    email_contacts.delete_contact(contact_id, church_id)


def submit_add_hymn(user_id, church_id, *, title, number=None,
                    scripture_refs="", theme="", hymnary_link=""):
    _require_member(user_id, church_id)
    if not (title or "").strip():
        raise ValueError("Hymn title is required.")
    return hymns_repo.add_hymn(
        church_id, title=title.strip(), number=number,
        scripture_refs=scripture_refs, theme=theme, hymnary_link=hymnary_link)


def submit_update_hymn(user_id, church_id, hymn_id, **fields):
    _require_member(user_id, church_id)
    return hymns_repo.update_hymn(hymn_id, church_id, **fields)


def submit_delete_hymn(user_id, church_id, hymn_id):
    _require_member(user_id, church_id)
    hymns_repo.delete_hymn(hymn_id, church_id)


def apply_role_change(actor_user_id, church_id, target_user_id, new_role):
    _require_admin(actor_user_id, church_id)
    set_role(target_user_id, church_id, new_role)  # may raise LastAdminError on demotion


def apply_remove_member(actor_user_id, church_id, target_user_id):
    _require_admin(actor_user_id, church_id)
    remove_membership(target_user_id, church_id)  # surfaces LastAdminError to the UI


def do_create_invite(actor_user_id, church_id, *, role="member", email=None):
    _require_admin(actor_user_id, church_id)
    return create_invite(church_id=church_id, created_by=actor_user_id, role=role, email=email)


def do_revoke_invite(actor_user_id, church_id, invite_id):
    _require_admin(actor_user_id, church_id)
    revoke_invite(invite_id, church_id)


def transfer_ownership(actor_user_id, church_id, new_owner_user_id):
    _require_owner(actor_user_id, church_id)
    set_role(new_owner_user_id, church_id, "owner")
    set_role(actor_user_id, church_id, "admin")


def delete_this_church(actor_user_id, church_id):
    _require_owner(actor_user_id, church_id)
    soft_delete_church(church_id)  # soft delete; also revokes pending invites


def submit_prompts(actor_user_id, church_id, prompts: dict):
    """Save per-church liturgy prompt overrides (admin only). A field equal to the
    default (or blank) is not stored, so it stays on the shared default."""
    _require_admin(actor_user_id, church_id)
    defaults = liturgy_prompts.default_prompts()
    cleaned = {
        k: (v or "").strip()
        for k, v in (prompts or {}).items()
        if k in liturgy_prompts.PROMPT_KEYS
        and (v or "").strip()
        and (v or "").strip() != defaults.get(k, "").strip()
    }
    set_church_prompts(church_id, cleaned)


def reset_prompts(actor_user_id, church_id):
    """Clear all overrides -> back to the shared defaults (admin only)."""
    _require_admin(actor_user_id, church_id)
    set_church_prompts(church_id, {})


def submit_translation(actor_user_id, church_id, translation_id: str):
    """Set the church's default Bible translation (admin only)."""
    _require_admin(actor_user_id, church_id)
    valid = {tid for tid, _ in available_translations()}
    if translation_id not in valid:
        raise ValueError("Unknown or unavailable translation.")
    set_church_translation(church_id, translation_id)


# --------------------------------------------------------------------------- #
# Render (Streamlit shell)
# --------------------------------------------------------------------------- #
def render_settings_page(user, active):
    user_id = user["user_id"]
    church_id = active["church_id"]
    role = active["role"]
    admin = is_admin(role)

    with session_scope() as s:
        church = s.get(Church, church_id)
        current_tz = church.timezone if church else ""

    st.title("Settings")
    st.caption(f"{active['name']} — you are **{role}**.")

    (tab_profile, tab_contacts, tab_hymns, tab_prompts,
     tab_members, tab_invites, tab_danger) = st.tabs(
        ["Church profile", "Contacts", "Hymns", "Liturgy prompts",
         "Members", "Invites", "Danger zone"])

    with tab_profile:
        if not admin:
            st.info("Only admins can edit the church profile.")
        with st.form("church_profile"):
            name = st.text_input("Church name", value=active["name"])
            timezone = st.text_input("Timezone", value=current_tz)
            trans_opts = available_translations()
            trans_ids = [t[0] for t in trans_opts]
            trans_labels = {t[0]: t[1] for t in trans_opts}
            cur_trans = get_church_translation(church_id) or DEFAULT_TRANSLATION
            translation = st.selectbox(
                "Default Bible translation",
                trans_ids,
                index=trans_ids.index(cur_trans) if cur_trans in trans_ids else 0,
                format_func=lambda tid: trans_labels.get(tid, tid),
                help="Default for on-screen passage text; anyone can switch it per session.",
            )
            if st.form_submit_button("Save profile", disabled=not admin):
                try:
                    submit_profile_update(user_id, church_id, name=name, timezone=timezone)
                    submit_translation(user_id, church_id, translation)
                    st.success("Profile updated.")
                    st.rerun()
                except (NotAuthorizedError, ValueError) as e:
                    st.error(str(e))

    with tab_prompts:
        st.caption(
            "These are the instructions the AI follows when it writes your liturgy. "
            "Edit any of them to shape the voice; leave a box on its default to use the "
            "shared wording. " + liturgy_prompts.PLACEHOLDER_HELP
        )
        if not admin:
            st.info("Only admins can edit the prompts (you can read them below).")
        overrides = get_church_prompts(church_id)
        defaults = liturgy_prompts.default_prompts()

        def _prompt_box(key, label):
            customized = " • customized" if overrides.get(key) else ""
            return st.text_area(
                f"{label}{customized}",
                value=overrides.get(key, defaults[key]),
                key=f"prompt_{key}",
                height=200 if key in ("system", "prayers_of_the_people") else 110,
                disabled=not admin,
            )

        with st.form("liturgy_prompts_form"):
            edited = {"system": _prompt_box("system", "Overall voice (system prompt)")}
            for section in liturgy_prompts.SECTION_ORDER:
                edited[section] = _prompt_box(section, liturgy_prompts.SECTION_LABELS[section])
            col_save, col_reset = st.columns(2)
            save = col_save.form_submit_button("Save prompts", disabled=not admin)
            reset = col_reset.form_submit_button("Reset all to defaults", disabled=not admin)
            if save:
                try:
                    submit_prompts(user_id, church_id, edited)
                    st.success("Prompts saved.")
                    st.rerun()
                except NotAuthorizedError as e:
                    st.error(str(e))
            elif reset:
                try:
                    reset_prompts(user_id, church_id)
                    st.success("Prompts reset to defaults.")
                    st.rerun()
                except NotAuthorizedError as e:
                    st.error(str(e))

    with tab_contacts:
        contacts = email_contacts.list_contacts(church_id)
        for c in contacts:
            col_a, col_b = st.columns([4, 1])
            col_a.write(f"**{c['name']}** — {c['email']}")
            if admin and col_b.button("Delete", key=f"del_contact_{c['id']}"):
                try:
                    submit_delete_contact(user_id, church_id, c["id"])
                    st.rerun()
                except NotAuthorizedError as e:
                    st.error(str(e))
        if admin:
            with st.form("add_contact"):
                cname = st.text_input("Name", key="new_contact_name")
                cemail = st.text_input("Email", key="new_contact_email")
                if st.form_submit_button("Add contact"):
                    try:
                        submit_add_contact(user_id, church_id, name=cname, email=cemail)
                        st.success("Contact added.")
                        st.rerun()
                    except (NotAuthorizedError, ValueError) as e:
                        st.error(str(e))
        else:
            st.info("Only admins can add or remove contacts.")

    with tab_hymns:
        st.caption("Members may edit this church's hymnal.")
        hymns = hymns_repo.list_hymns(church_id)
        st.write(f"{len(hymns)} hymns.")
        with st.form("add_hymn"):
            htitle = st.text_input("Title", key="new_hymn_title")
            hnum = st.text_input("Number", key="new_hymn_number")
            hrefs = st.text_input("Scripture references", key="new_hymn_refs")
            if st.form_submit_button("Add hymn"):
                try:
                    submit_add_hymn(
                        user_id, church_id, title=htitle,
                        number=int(hnum) if hnum.strip().isdigit() else None,
                        scripture_refs=hrefs)
                    st.success("Hymn added.")
                    st.rerun()
                except (NotAuthorizedError, ValueError) as e:
                    st.error(str(e))
        for h in hymns[:50]:
            col_a, col_b = st.columns([4, 1])
            col_a.write(f"#{h.get('Hymn Number') or '—'} — {h.get('Hymn Title')}")
            if col_b.button("Delete", key=f"del_hymn_{h['id']}"):
                try:
                    submit_delete_hymn(user_id, church_id, h["id"])
                    st.rerun()
                except NotAuthorizedError as e:
                    st.error(str(e))

    with tab_members:
        if not admin:
            st.info("Only admins can manage members.")
        role_options = ["member", "admin", "owner"]
        for m in list_members(church_id):
            cols = st.columns([3, 2, 1])
            cols[0].write(f"**{m['name'] or m['email']}** ({m['email']}) — {m['role']}")
            if admin and m["user_id"] != user_id:
                new_role = cols[1].selectbox(
                    "Role", role_options, index=role_options.index(m["role"]),
                    key=f"role_{m['user_id']}", label_visibility="collapsed")
                if new_role != m["role"] and cols[1].button("Update", key=f"chg_{m['user_id']}"):
                    try:
                        apply_role_change(user_id, church_id, m["user_id"], new_role)
                        st.rerun()
                    except (NotAuthorizedError, LastAdminError) as e:
                        st.error(str(e))
                if cols[2].button("Remove", key=f"rm_{m['user_id']}"):
                    try:
                        apply_remove_member(user_id, church_id, m["user_id"])
                        st.rerun()
                    except (NotAuthorizedError, LastAdminError) as e:
                        st.error(str(e))

    with tab_invites:
        if not admin:
            st.info("Only admins can manage invites.")
        else:
            with st.form("create_invite"):
                inv_email = st.text_input("Bind to email (optional)")
                inv_role = st.selectbox("Role", ["member", "admin"])
                if st.form_submit_button("Create invite"):
                    try:
                        code = do_create_invite(
                            user_id, church_id, role=inv_role,
                            email=(inv_email.strip() or None))
                        st.success(f"Invite code: `{code}`")
                    except NotAuthorizedError as e:
                        st.error(str(e))
            for inv in list_invites(church_id):
                cols = st.columns([3, 1])
                cols[0].write(f"`{inv['code']}` — {inv.get('email') or 'any'} — {inv['role']}")
                if cols[1].button("Revoke", key=f"revoke_{inv['id']}"):
                    try:
                        do_revoke_invite(user_id, church_id, inv["id"])
                        st.rerun()
                    except NotAuthorizedError as e:
                        st.error(str(e))

    with tab_danger:
        if role != "owner":
            st.info("Only the owner can transfer ownership or delete the church.")
        else:
            st.subheader("Transfer ownership")
            others = [m for m in list_members(church_id) if m["user_id"] != user_id]
            if others:
                labels = {f"{m['name'] or m['email']} ({m['email']})": m["user_id"] for m in others}
                pick = st.selectbox("New owner", list(labels.keys()), key="transfer_pick")
                if st.button("Transfer ownership"):
                    try:
                        transfer_ownership(user_id, church_id, labels[pick])
                        st.success("Ownership transferred. You are now an admin.")
                        st.rerun()
                    except NotAuthorizedError as e:
                        st.error(str(e))
            else:
                st.caption("Invite another member first to transfer ownership.")
            st.divider()
            st.subheader("Delete this church")
            confirm = st.text_input("Type the church name to confirm", key="delete_confirm")
            if st.button("Delete church", type="primary"):
                if confirm.strip() == active["name"]:
                    try:
                        delete_this_church(user_id, church_id)
                        st.session_state.pop("active_church_id", None)
                        st.success("Church deleted.")
                        st.rerun()
                    except NotAuthorizedError as e:
                        st.error(str(e))
                else:
                    st.error("Church name did not match.")
