import streamlit as st
import psycopg2
import psycopg2.errors

# ── Connection ────────────────────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(st.secrets["DB_URL"])

# ── Helpers ───────────────────────────────────────────────────────────────────
def fetch_events():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, description, event_date, location, created_at
        FROM events
        ORDER BY event_date ASC;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def fetch_clubs():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM clubs ORDER BY name;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def fetch_event_club_ids(event_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT club_id FROM event_clubs WHERE event_id = %s;", (event_id,))
    ids = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return ids

def insert_event(title, description, event_date, location, club_ids):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO events (title, description, event_date, location)
           VALUES (%s, %s, %s, %s) RETURNING id;""",
        (title.strip(), description.strip(), event_date, location.strip())
    )
    event_id = cur.fetchone()[0]
    for club_id in club_ids:
        cur.execute(
            "INSERT INTO event_clubs (event_id, club_id) VALUES (%s, %s);",
            (event_id, club_id)
        )
    conn.commit()
    cur.close()
    conn.close()

def update_event(event_id, title, description, event_date, location, club_ids):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """UPDATE events
           SET title=%s, description=%s, event_date=%s, location=%s
           WHERE id=%s;""",
        (title.strip(), description.strip(), event_date, location.strip(), event_id)
    )
    cur.execute("DELETE FROM event_clubs WHERE event_id=%s;", (event_id,))
    for club_id in club_ids:
        cur.execute(
            "INSERT INTO event_clubs (event_id, club_id) VALUES (%s, %s);",
            (event_id, club_id)
        )
    conn.commit()
    cur.close()
    conn.close()

def delete_event(event_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM events WHERE id=%s;", (event_id,))
    conn.commit()
    cur.close()
    conn.close()

def fetch_clubs_for_event(event_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.name FROM clubs c
        JOIN event_clubs ec ON c.id = ec.club_id
        WHERE ec.event_id = %s
        ORDER BY c.name;
    """, (event_id,))
    names = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return ", ".join(names) if names else "None"

# ── Session state defaults ────────────────────────────────────────────────────
if "edit_event_id" not in st.session_state:
    st.session_state.edit_event_id = None
if "delete_event_id" not in st.session_state:
    st.session_state.delete_event_id = None

# ── Page ──────────────────────────────────────────────────────────────────────
st.title("Manage Club Events")

# ── Add Event Form ────────────────────────────────────────────────────────────
st.subheader("Create New Event")

clubs = fetch_clubs()
club_map = {name: cid for cid, name in clubs}  # {"Club Name": id}

with st.form("add_event_form", clear_on_submit=True):
    title = st.text_input("Event Title *")
    description = st.text_area("Description")
    col1, col2 = st.columns(2)
    with col1:
        event_date = st.date_input("Event Date *")
        event_time = st.time_input("Event Time *")
    with col2:
        location = st.text_input("Location")
    selected_clubs = st.multiselect(
        "Associate with Clubs (select one or more) *",
        options=list(club_map.keys())
    )
    submitted = st.form_submit_button("Create Event")

    if submitted:
        errors = []
        if not title.strip():
            errors.append("Event title is required.")
        if not selected_clubs:
            errors.append("Please select at least one club.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            try:
                from datetime import datetime
                event_datetime = datetime.combine(event_date, event_time)
                club_ids = [club_map[name] for name in selected_clubs]
                insert_event(title, description, event_datetime, location, club_ids)
                st.success(f"Event '{title.strip()}' created successfully!")
                st.rerun()
            except Exception as ex:
                st.error(f"Unexpected error: {ex}")

st.divider()

# ── Edit Form ─────────────────────────────────────────────────────────────────
if st.session_state.edit_event_id is not None:
    events = fetch_events()
    target = next((r for r in events if r[0] == st.session_state.edit_event_id), None)

    if target:
        eid, etitle, edesc, edate, eloc, ecreated = target
        current_club_ids = fetch_event_club_ids(eid)
        current_club_names = [name for name, cid in club_map.items() if cid in current_club_ids]

        st.subheader(f"Editing: {etitle}")
        with st.form("edit_event_form"):
            edit_title = st.text_input("Event Title *", value=etitle)
            edit_desc = st.text_area("Description", value=edesc or "")
            col1, col2 = st.columns(2)
            with col1:
                edit_date = st.date_input("Event Date *", value=edate.date())
                edit_time = st.time_input("Event Time *", value=edate.time())
            with col2:
                edit_location = st.text_input("Location", value=eloc or "")
            edit_clubs = st.multiselect(
                "Associate with Clubs *",
                options=list(club_map.keys()),
                default=current_club_names
            )

            save_col, cancel_col = st.columns([1, 5])
            with save_col:
                save = st.form_submit_button("Save Changes")
            with cancel_col:
                cancel = st.form_submit_button("Cancel")

        if cancel:
            st.session_state.edit_event_id = None
            st.rerun()

        if save:
            errors = []
            if not edit_title.strip():
                errors.append("Event title is required.")
            if not edit_clubs:
                errors.append("Please select at least one club.")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                try:
                    from datetime import datetime
                    edit_datetime = datetime.combine(edit_date, edit_time)
                    club_ids = [club_map[name] for name in edit_clubs]
                    update_event(eid, edit_title, edit_desc, edit_datetime, edit_location, club_ids)
                    st.success("Event updated successfully!")
                    st.session_state.edit_event_id = None
                    st.rerun()
                except Exception as ex:
                    st.error(f"Unexpected error: {ex}")

    st.divider()

# ── Current Events Table ──────────────────────────────────────────────────────
st.subheader("Current Events")

events = fetch_events()

if not events:
    st.info("No events found. Create one above.")
else:
    h1, h2, h3, h4, h5, h6 = st.columns([3, 2, 2, 2, 1, 1])
    h1.markdown("**Title**")
    h2.markdown("**Date**")
    h3.markdown("**Location**")
    h4.markdown("**Clubs**")
    h5.markdown("**Edit**")
    h6.markdown("**Delete**")

    st.divider()

    for row in events:
        eid, etitle, edesc, edate, eloc, ecreated = row
        clubs_str = fetch_clubs_for_event(eid)

        c1, c2, c3, c4, c5, c6 = st.columns([3, 2, 2, 2, 1, 1])
        c1.write(etitle)
        c2.write(edate.strftime("%Y-%m-%d %H:%M") if edate else "")
        c3.write(eloc or "—")
        c4.write(clubs_str)

        if c5.button("Edit", key=f"edit_{eid}"):
            st.session_state.edit_event_id = eid
            st.session_state.delete_event_id = None
            st.rerun()

        if c6.button("Delete", key=f"delete_{eid}"):
            st.session_state.delete_event_id = eid
            st.session_state.edit_event_id = None
            st.rerun()

        if st.session_state.delete_event_id == eid:
            st.warning(f"Are you sure you want to delete **{etitle}**? This cannot be undone.")
            conf_col, cancel_col = st.columns([1, 5])
            if conf_col.button("Yes, Delete", key=f"confirm_{eid}"):
                delete_event(eid)
                st.session_state.delete_event_id = None
                st.success(f"'{etitle}' has been deleted.")
                st.rerun()
            if cancel_col.button("Cancel", key=f"cancel_del_{eid}"):
                st.session_state.delete_event_id = None
                st.rerun()
