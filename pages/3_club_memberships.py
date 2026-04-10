import streamlit as st
import psycopg2
import psycopg2.errors

# ── Connection ────────────────────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(st.secrets["DB_URL"])

# ── Helpers ───────────────────────────────────────────────────────────────────
def fetch_students():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, first_name || ' ' || last_name AS full_name, email
        FROM students
        ORDER BY last_name, first_name;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows  # [(id, full_name, email), ...]

def fetch_clubs():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM clubs ORDER BY name;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows  # [(id, name), ...]

def fetch_memberships(club_filter_id=None):
    conn = get_connection()
    cur = conn.cursor()
    if club_filter_id:
        cur.execute("""
            SELECT cm.id,
                   s.first_name || ' ' || s.last_name AS student,
                   s.email,
                   c.name AS club,
                   cm.joined_at
            FROM club_members cm
            JOIN students s ON cm.student_id = s.id
            JOIN clubs c ON cm.club_id = c.id
            WHERE cm.club_id = %s
            ORDER BY c.name, s.last_name, s.first_name;
        """, (club_filter_id,))
    else:
        cur.execute("""
            SELECT cm.id,
                   s.first_name || ' ' || s.last_name AS student,
                   s.email,
                   c.name AS club,
                   cm.joined_at
            FROM club_members cm
            JOIN students s ON cm.student_id = s.id
            JOIN clubs c ON cm.club_id = c.id
            ORDER BY c.name, s.last_name, s.first_name;
        """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows  # [(cm_id, student, email, club, joined_at), ...]

def fetch_club_roster(club_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.first_name || ' ' || s.last_name AS student,
               s.email,
               cm.joined_at
        FROM club_members cm
        JOIN students s ON cm.student_id = s.id
        WHERE cm.club_id = %s
        ORDER BY s.last_name, s.first_name;
    """, (club_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows  # [(student, email, joined_at), ...]

def insert_membership(student_id, club_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO club_members (student_id, club_id) VALUES (%s, %s);",
        (student_id, club_id)
    )
    conn.commit()
    cur.close()
    conn.close()

def delete_membership(membership_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM club_members WHERE id=%s;", (membership_id,))
    conn.commit()
    cur.close()
    conn.close()

# ── Session state defaults ────────────────────────────────────────────────────
if "delete_membership_id" not in st.session_state:
    st.session_state.delete_membership_id = None

# ── Page ──────────────────────────────────────────────────────────────────────
st.title("Club Memberships")

# ── Add Membership Form ───────────────────────────────────────────────────────
st.subheader("Enroll a Student in a Club")

students = fetch_students()
clubs = fetch_clubs()

student_map = {"-- Select a student --": None}
student_map.update({name: sid for sid, name, email in students})

club_map = {"-- Select a club --": None}
club_map.update({name: cid for cid, name in clubs})

with st.form("add_membership_form", clear_on_submit=True):
    selected_student = st.selectbox("Student *", options=list(student_map.keys()))
    selected_club = st.selectbox("Club *", options=list(club_map.keys()))
    submitted = st.form_submit_button("Enroll Student")

    if submitted:
        errors = []
        if student_map[selected_student] is None:
            errors.append("Please select a student.")
        if club_map[selected_club] is None:
            errors.append("Please select a club.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            try:
                insert_membership(student_map[selected_student], club_map[selected_club])
                st.success(f"{selected_student} has been enrolled in {selected_club}!")
                st.rerun()
            except psycopg2.errors.UniqueViolation:
                st.error(f"{selected_student} is already a member of {selected_club}.")
            except Exception as ex:
                st.error(f"Unexpected error: {ex}")

st.divider()

# ── Filter by Club ────────────────────────────────────────────────────────────
st.subheader("Current Memberships")

filter_options = {"All Clubs": None}
filter_options.update({name: cid for cid, name in clubs})

filter_col, _ = st.columns([2, 3])
with filter_col:
    selected_filter = st.selectbox("Filter by Club", options=list(filter_options.keys()))

filter_club_id = filter_options[selected_filter]
memberships = fetch_memberships(club_filter_id=filter_club_id)

if not memberships:
    st.info("No memberships found." if filter_club_id else "No memberships yet. Enroll a student above.")
else:
    h1, h2, h3, h4, h5 = st.columns([2, 3, 2, 2, 1])
    h1.markdown("**Student**")
    h2.markdown("**Email**")
    h3.markdown("**Club**")
    h4.markdown("**Date Joined**")
    h5.markdown("**Remove**")

    st.divider()

    for row in memberships:
        cm_id, student, email, club, joined_at = row
        c1, c2, c3, c4, c5 = st.columns([2, 3, 2, 2, 1])
        c1.write(student)
        c2.write(email)
        c3.write(club)
        c4.write(joined_at.strftime("%Y-%m-%d") if joined_at else "")

        if c5.button("Remove", key=f"delete_{cm_id}"):
            st.session_state.delete_membership_id = cm_id
            st.rerun()

        if st.session_state.delete_membership_id == cm_id:
            st.warning(f"Remove **{student}** from **{club}**? This cannot be undone.")
            conf_col, cancel_col = st.columns([1, 5])
            if conf_col.button("Yes, Remove", key=f"confirm_{cm_id}"):
                delete_membership(cm_id)
                st.session_state.delete_membership_id = None
                st.success(f"{student} has been removed from {club}.")
                st.rerun()
            if cancel_col.button("Cancel", key=f"cancel_{cm_id}"):
                st.session_state.delete_membership_id = None
                st.rerun()

st.divider()

# ── Club Roster View ──────────────────────────────────────────────────────────
st.subheader("Club Roster")

if not clubs:
    st.info("No clubs found. Add clubs first.")
else:
    roster_map = {name: cid for cid, name in clubs}
    selected_roster_club = st.selectbox("Select a club to view its roster", options=list(roster_map.keys()))
    roster_club_id = roster_map[selected_roster_club]
    roster = fetch_club_roster(roster_club_id)

    st.metric("Total Members", len(roster))

    if not roster:
        st.info(f"No members in {selected_roster_club} yet.")
    else:
        st.table(
            [
                {
                    "Student": r[0],
                    "Email": r[1],
                    "Joined": r[2].strftime("%Y-%m-%d") if r[2] else ""
                }
                for r in roster
            ]
        )
