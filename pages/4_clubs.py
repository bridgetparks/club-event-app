import streamlit as st
import psycopg2
import psycopg2.errors

# ── Connection ────────────────────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(st.secrets["DB_URL"])

# ── Helpers ───────────────────────────────────────────────────────────────────
def fetch_clubs():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, description, created_at
        FROM clubs
        ORDER BY name ASC;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def insert_club(name, description):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO clubs (name, description) VALUES (%s, %s);",
        (name.strip(), description.strip())
    )
    conn.commit()
    cur.close()
    conn.close()

def update_club(club_id, name, description):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE clubs SET name=%s, description=%s WHERE id=%s;",
        (name.strip(), description.strip(), club_id)
    )
    conn.commit()
    cur.close()
    conn.close()

def delete_club(club_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM clubs WHERE id=%s;", (club_id,))
    conn.commit()
    cur.close()
    conn.close()

def fetch_member_count(club_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM club_members WHERE club_id=%s;",
        (club_id,)
    )
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count

# ── Session state defaults ────────────────────────────────────────────────────
if "edit_club_id" not in st.session_state:
    st.session_state.edit_club_id = None
if "delete_club_id" not in st.session_state:
    st.session_state.delete_club_id = None

# ── Page ──────────────────────────────────────────────────────────────────────
st.title("Manage Clubs")

# ── Add Club Form ─────────────────────────────────────────────────────────────
st.subheader("Create New Club")

with st.form("add_club_form", clear_on_submit=True):
    new_name = st.text_input("Club Name *")
    new_description = st.text_area("Description")
    submitted = st.form_submit_button("Create Club")

    if submitted:
        errors = []
        if not new_name.strip():
            errors.append("Club name is required.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            try:
                insert_club(new_name, new_description)
                st.success(f"Club '{new_name.strip()}' created successfully!")
                st.rerun()
            except psycopg2.errors.UniqueViolation:
                st.error(f"A club named '{new_name.strip()}' already exists.")
            except Exception as ex:
                st.error(f"Unexpected error: {ex}")

st.divider()

# ── Edit Form (shown when an Edit button is clicked) ──────────────────────────
if st.session_state.edit_club_id is not None:
    clubs = fetch_clubs()
    target = next((r for r in clubs if r[0] == st.session_state.edit_club_id), None)

    if target:
        cid, cname, cdesc, ccreated = target
        st.subheader(f"Editing: {cname}")

        with st.form("edit_club_form"):
            edit_name = st.text_input("Club Name *", value=cname)
            edit_desc = st.text_area("Description", value=cdesc or "")

            save_col, cancel_col = st.columns([1, 5])
            with save_col:
                save = st.form_submit_button("Save Changes")
            with cancel_col:
                cancel = st.form_submit_button("Cancel")

        if cancel:
            st.session_state.edit_club_id = None
            st.rerun()

        if save:
            errors = []
            if not edit_name.strip():
                errors.append("Club name is required.")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                try:
                    update_club(cid, edit_name, edit_desc)
                    st.success("Club updated successfully!")
                    st.session_state.edit_club_id = None
                    st.rerun()
                except psycopg2.errors.UniqueViolation:
                    st.error(f"A club named '{edit_name.strip()}' already exists.")
                except Exception as ex:
                    st.error(f"Unexpected error: {ex}")

    st.divider()

# ── Current Clubs Table ───────────────────────────────────────────────────────
st.subheader("Current Clubs")

clubs = fetch_clubs()

if not clubs:
    st.info("No clubs found. Create one above.")
else:
    h1, h2, h3, h4, h5, h6 = st.columns([1, 2, 3, 2, 1, 1])
    h1.markdown("**ID**")
    h2.markdown("**Club Name**")
    h3.markdown("**Description**")
    h4.markdown("**Created**")
    h5.markdown("**Edit**")
    h6.markdown("**Delete**")

    st.divider()

    for row in clubs:
        cid, cname, cdesc, ccreated = row
        member_count = fetch_member_count(cid)

        c1, c2, c3, c4, c5, c6 = st.columns([1, 2, 3, 2, 1, 1])
        c1.write(cid)
        c2.write(f"{cname} ({member_count} members)")
        c3.write(cdesc or "—")
        c4.write(ccreated.strftime("%Y-%m-%d") if ccreated else "")

        if c5.button("Edit", key=f"edit_{cid}"):
            st.session_state.edit_club_id = cid
            st.session_state.delete_club_id = None
            st.rerun()

        if c6.button("Delete", key=f"delete_{cid}"):
            st.session_state.delete_club_id = cid
            st.session_state.edit_club_id = None
            st.rerun()

        if st.session_state.delete_club_id == cid:
            st.warning(
                f"Are you sure you want to delete **{cname}**? "
                f"This will also remove all {member_count} membership(s) for this club."
            )
            conf_col, cancel_col = st.columns([1, 5])
            if conf_col.button("Yes, Delete", key=f"confirm_{cid}"):
                delete_club(cid)
                st.session_state.delete_club_id = None
                st.success(f"'{cname}' has been deleted.")
                st.rerun()
            if cancel_col.button("Cancel", key=f"cancel_del_{cid}"):
                st.session_state.delete_club_id = None
                st.rerun()
