# Manual Verification Checklist (deployed URL)

Run these on the **deployed** Streamlit Cloud URL after configuring `[auth]`,
`DATABASE_URL`, and the `GOOGLE_*` gmail.send client. These flows depend on real
redirects/cookies and cannot be fully covered by unit tests.

## 1. Gmail callback with `[auth]` CORS/XSRF enabled
- [ ] Enabling `[auth]` auto-enables Streamlit's CORS/XSRF protection. Confirm
      the manual gmail.send return to the **app root** with `?code=...&state=...`
      is delivered to app code (a top-level GET) and is **not** swallowed by
      Streamlit's internal `/oauth2callback` login handler.
- [ ] Click **Connect your Gmail**, complete Google consent, and confirm the
      refresh token is saved and a test bulletin sends from your own address.
- [ ] Confirm the sender is always the logged-in `st.user.email` (a spoofed
      `?gmail=` param has no effect) and that a missing/invalid OAuth `state`
      is rejected on callback.

## 2. Login round-trip
- [ ] Sign in with Google (`st.login`), reload, and confirm the 30-day cookie
      keeps you signed in.
- [ ] Sign out (`st.logout`) and confirm the app returns to the signed-out state.
- [ ] First-ever sign-in creates the user record; a user with no church sees the
      create-or-join empty state.

## 3. Invite link survives login
- [ ] Open an invite link (`?invite=CODE`) while signed out. After the Google
      login round-trip (and any gmail-connect round-trip), confirm the `?invite`
      param is preserved and the church is joined as `member`.
- [ ] Confirm an expired/revoked code fails cleanly, and accepting when already
      a member is a no-op.
