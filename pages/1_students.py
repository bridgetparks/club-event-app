import streamlit as st
import psycopg2
import re

# ── Connection ────────────────────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(st.secrets["DB_URL"])

# ── Helpers ───────────────────────────────────────────────────────────────────
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email.strip()))

def fetch_students():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, first_name, last_name, email, created_at
        FROM students
        ORDER BY last_name, first_name;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def insert_student(first_name, last_name, email):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO students (first_name, last_name, email) VALUES (%s, %s, %s);",
        (first_name.strip(), last_name.strip(), email.strip().lower())
    )
    conn.commit()
    cur.close()
    conn.close()

def update_student(student_id, first_name, last_name, email):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE students SET first_name=%s, last_name=%s, email=%s WHERE id=%s;",
        (first_name.strip(), last_name.strip(), email.strip().lower(), student_id)
    )
    conn.commit()
    cur.close()
    conn.close()

def delete_student(student_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE id=%s;", (student_id,))
    conn.commit()
    cur.close()
    conn.close()

# ── Session state defaults ────────────────────────────────────────────────────
if "edit_student_id" not in st.session_state:
    st.session_state.edit_student_id = None
if "delete_student_id" not in st.session_state:
    st.session_state.delete_student_id = None

# ── Page ──────────────────────────────────────────────────────────────────────
st.title("Manage Students")

# ── Add Student Form ──────────────────────────────────────────────────────────
st.subheader("Add New Student")
with st.form("add_student_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        new_first = st.text_input("First Name *")
        new_email = st.text_input("Email *")
    with col2:
        new_last = st.text_input("Last Name *")
    submitted = st.form_submit_button("Add Student")

    if submitted:
        errors = []
        if not new_first.strip():
            errors.append("First name is required.")
        if not new_last.strip():
            errors.append("Last name is required.")
        if not new_email.strip():
            errors.append("Email is required.")
        elif not is_valid_email(new_email):
            errors.append("Email format is invalid.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            try:
                insert_student(new_first, new_last, new_email)
                st.success(f"Student {new_first.strip()} {new_last.strip()} added successfully!")
                st.rerun()
            except psycopg2.errors.UniqueViolation:
                st.error("A student with that email already exists.")
            except Exception as ex:
                st.error(f"Unexpected error: {ex}")

st.divider()

# ── Edit Form (shown when an Edit button is clicked) ──────────────────────────
if st.session_state.edit_student_id is not None:
    students = fetch_students()
    target = next((r for r in students if r[0] == st.session_state.edit_student_id), None)

    if target:
        st.subheader(f"Editing: {target[1]} {target[2]}")
        with st.form("edit_student_form"):
            col1, col2 = st.columns(2)
            with col1:
                edit_first = st.text_input("First Name *", value=target[1])
                edit_email = st.text_input("Email *", value=target[3])
            with col2:
                edit_last = st.text_input("Last Name *", value=target[2])

            save_col, cancel_col = st.columns([1, 5])
            with save_col:
                save = st.form_submit_button("Save Changes")
            with cancel_col:
                cancel = st.form_submit_button("Cancel")

        if cancel:
            st.session_state.edit_student_id = None
            st.rerun()

        if save:
            errors = []
            if not edit_first.strip():
                errors.append("First name is required.")
            if not edit_last.strip():
                errors.append("Last name is required.")
            if not edit_email.strip():
                errors.append("Email is required.")
            elif not is_valid_email(edit_email):
                errors.append("Email format is invalid.")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                try:
                    update_student(st.session_state.edit_student_id, edit_first, edit_last, edit_email)
                    st.success("Student updated successfully!")
                    st.session_state.edit_student_id = None
                    st.rerun()
                except psycopg2.errors.UniqueViolation:
                    st.error("Another student already has that email.")
                except Exception as ex:
                    st.error(f"Unexpected error: {ex}")

    st.divider()

# ── Current Students Table ────────────────────────────────────────────────────
st.subheader("Current Students")

students = fetch_students()

if not students:
    st.info("No students found. Add one above.")
else:
    h1, h2, h3, h4, h5, h6 = st.columns([1, 2, 2, 3, 2, 1])
    h1.markdown("**ID**")
    h2.markdown("**First Name**")
    h3.markdown("**Last Name**")
    h4.markdown("**Email**")
    h5.markdown("**Joined**")
    h6.markdown("**Actions**")

    st.divider()

    for row in students:
        sid, first, last, email, created_at = row
        c1, c2, c3, c4, c5, c6, c7 = st.columns([1, 2, 2, 3, 2, 1, 1])
        c1.write(sid)
        c2.write(first)
        c3.write(last)
        c4.write(email)
        c5.write(created_at.strftime("%Y-%m-%d") if created_at else "")

        if c6.button("Edit", key=f"edit_{sid}"):
            st.session_state.edit_student_id = sid
            st.session_state.delete_student_id = None
            st.rerun()

        if c7.button("Delete", key=f"delete_{sid}"):
            st.session_state.delete_student_id = sid
            st.session_state.edit_student_id = None
            st.rerun()

        if st.session_state.delete_student_id == sid:
            st.warning(f"Are you sure you want to delete **{first} {last}**? This will also remove their club memberships.")
            conf_col, cancel_col = st.columns([1, 5])
            if conf_col.button("Yes, Delete", key=f"confirm_{sid}"):
                delete_student(sid)
                st.session_state.delete_student_id = None
                st.success(f"{first} {last} has been deleted.")
                st.rerun()
            if cancel_col.button("Cancel", key=f"cancel_del_{sid}"):
                st.session_state.delete_student_id = None
                st.rerun()
