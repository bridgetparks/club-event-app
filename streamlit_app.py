import streamlit as st
import psycopg2

st.set_page_config(page_title="GU Club Tracker", page_icon="🐶")

def get_connection():
    return psycopg2.connect(st.secrets["DB_URL"])

st.title("🐶 Gonzaga University Club Tracker")
st.write("Welcome! Use the sidebar to navigate between pages.")
st.markdown("---")

st.subheader("📊 Current Data")

try:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM students;")
    student_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM clubs;")
    club_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM club_members;")
    membership_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM events;")
    event_count = cur.fetchone()[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Students", student_count)
    col2.metric("Clubs", club_count)
    col3.metric("Memberships", membership_count)
    col4.metric("Events", event_count)

    st.markdown("---")

    st.subheader("📋 Recent Club Memberships")
    cur.execute("""
        SELECT s.first_name || ' ' || s.last_name AS student,
               s.email,
               c.name AS club,
               cm.joined_at
        FROM club_members cm
        JOIN students s ON cm.student_id = s.id
        JOIN clubs c ON cm.club_id = c.id
        ORDER BY cm.joined_at DESC
        LIMIT 10;
    """)
    rows = cur.fetchall()
    if rows:
        st.table(
            [{"Student": r[0], "Email": r[1], "Club": r[2], "Joined": r[3].strftime("%Y-%m-%d %H:%M")} for r in rows]
        )
    else:
        st.info("No memberships yet. Add some students and clubs, then enroll them!")

    st.markdown("---")

    st.subheader("📅 Upcoming Events")
    cur.execute("""
        SELECT e.title, e.location, e.event_date,
               STRING_AGG(c.name, ', ') AS clubs
        FROM events e
        LEFT JOIN event_clubs ec ON e.id = ec.event_id
        LEFT JOIN clubs c ON ec.club_id = c.id
        WHERE e.event_date >= NOW()
        GROUP BY e.id, e.title, e.location, e.event_date
        ORDER BY e.event_date ASC
        LIMIT 5;
    """)
    upcoming = cur.fetchall()
    if upcoming:
        st.table(
            [{"Event": r[0], "Location": r[1], "Date": r[2].strftime("%Y-%m-%d %H:%M"), "Clubs": r[3] or "None"} for r in upcoming]
        )
    else:
        st.info("No upcoming events. Create one on the Events page!")

    cur.close()
    conn.close()

except Exception as e:
    st.error(f"Database connection error: {e}")
