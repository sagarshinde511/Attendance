import io
import mysql.connector
import pandas as pd
import streamlit as st

# Database connection details
DB_CONFIG = {
    "host": "82.180.143.66",
    "user": "u263681140_students1",
    "password": "testStudents@123",
    "database": "u263681140_students1",
}

# Default Login Credentials
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"


def get_db_connection():
  return mysql.connector.connect(**DB_CONFIG)


# --- Database Functions ---


def get_stud_ids():
  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute("SELECT id, studId FROM attendance_enroll")
  data = cursor.fetchall()
  conn.close()
  return data


def update_stud_id(record_id, new_stud_id):
  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute(
      "UPDATE attendance_enroll SET studId = %s WHERE id = %s",
      (new_stud_id, record_id),
  )
  conn.commit()
  conn.close()


def insert_student(roll_no, name, branch):
  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO StudentAttendance (RollNo, Name, Branch) VALUES (%s, %s,"
      " %s)",
      (roll_no, name, branch),
  )
  conn.commit()
  conn.close()


def get_all_users():
  conn = get_db_connection()
  cursor = conn.cursor(dictionary=True)
  cursor.execute("SELECT * FROM StudentAttendance")
  data = cursor.fetchall()
  conn.close()
  return pd.DataFrame(data)


def update_user_info(original_roll_no, new_roll_no, new_name, new_branch):
  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute(
      """
        UPDATE StudentAttendance 
        SET RollNo = %s, Name = %s, Branch = %s 
        WHERE RollNo = %s
        """,
      (new_roll_no, new_name, new_branch, original_roll_no),
  )
  conn.commit()
  conn.close()


def get_attendance():
  conn = get_db_connection()
  cursor = conn.cursor(dictionary=True)
  cursor.execute("SELECT * FROM StoreAttendance")
  data = cursor.fetchall()
  conn.close()
  return pd.DataFrame(data)


# --- Helper Function for Excel Export ---
def to_excel(df):
  output = io.BytesIO()
  with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df.to_excel(writer, index=False, sheet_name="Attendance")
  return output.getvalue()


# --- Session State & Auth ---

if "logged_in" not in st.session_state:
  st.session_state.logged_in = False


def login_page():
  st.title("Admin Login")
  with st.form("login_form"):
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    submit = st.form_submit_button("Login")

    if submit:
      if username == DEFAULT_USERNAME and password == DEFAULT_PASSWORD:
        st.session_state.logged_in = True
        st.rerun()
      else:
        st.error("Invalid username or password.")


# --- Main Application ---


def main_app():
  with st.sidebar:
    st.write(f"Logged in as **{DEFAULT_USERNAME}**")
    if st.button("🔄 Refresh Data", use_container_width=True):
      st.rerun()
    if st.button("Logout", use_container_width=True):
      st.session_state.logged_in = False
      st.rerun()

  st.title("Student Attendance Management")

  # Added the 4th tab: "Manage Users"
  tabs = st.tabs([
      "Update Student ID",
      "Register Student",
      "Check Attendance",
      "Manage Users",
  ])

  # Tab 1: Update Student ID
  with tabs[0]:
    st.header("Update Student ID in Attendance Enroll")
    stud_id_records = get_stud_ids()
    if stud_id_records:
      record_dict = {
          f"ID: {rec[0]}, Student ID: {rec[1]}": rec[0]
          for rec in stud_id_records
      }
      selected_record = st.selectbox(
          "Select Record to Update:", list(record_dict.keys())
      )
      new_stud_id = st.text_input("Enter New Student ID:")
      if st.button("Update"):
        if new_stud_id:
          update_stud_id(record_dict[selected_record], new_stud_id)
          st.success(
              f"Updated Student ID to {new_stud_id} for {selected_record}"
          )
        else:
          st.warning("Please enter a new Student ID.")
    else:
      st.error("No records found in the database.")

  # Tab 2: Register Student
  with tabs[1]:
    st.header("Register New Student")
    roll_no = st.text_input("Roll Number:")
    name = st.text_input("Name:")
    branch = st.text_input("Branch:")
    if st.button("Register"):
      if roll_no and name and branch:
        insert_student(roll_no, name, branch)
        st.success(
            f"Student {name} (Roll No: {roll_no}) registered successfully."
        )
      else:
        st.warning("Please fill all fields.")

  # Tab 3: Check Attendance (With Filters & CSV/Excel Export)
  with tabs[2]:
    col1, col2 = st.columns([4, 1])
    with col1:
      st.header("Attendance Records")
    with col2:
      st.write("")
      if st.button("🔄 Refresh", key="refresh_att"):
        st.rerun()

    df_attendance = get_attendance()

    if not df_attendance.empty:
      st.subheader("Filter Records")
      f_col1, f_col2 = st.columns(2)

      with f_col1:
        search_roll = st.text_input(
            "Filter by Roll Number:", placeholder="Enter Roll No..."
        )
      with f_col2:
        enable_date_filter = st.checkbox("Filter by Date")
        selected_date = st.date_input(
            "Select Date:", disabled=not enable_date_filter
        )

      # Apply Roll Number Filter (Dynamically finds column containing 'roll')
      roll_cols = [c for c in df_attendance.columns if "roll" in c.lower()]
      if search_roll and roll_cols:
        roll_col = roll_cols[0]
        df_attendance = df_attendance[
            df_attendance[roll_col]
            .astype(str)
            .str.contains(search_roll, case=False, na=False)
        ]

      # Apply Date Filter (Dynamically finds column containing 'date' or 'time')
      date_cols = [
          c
          for c in df_attendance.columns
          if "date" in c.lower() or "time" in c.lower()
      ]
      if enable_date_filter and date_cols:
        date_col = date_cols[0]
        # Matches YYYY-MM-DD string representation
        df_attendance = df_attendance[
            df_attendance[date_col]
            .astype(str)
            .str.contains(str(selected_date), na=False)
        ]

      st.dataframe(df_attendance, use_container_width=True)

      # Download Buttons
      if not df_attendance.empty:
        st.subheader("Export Data")
        d_col1, d_col2, _ = st.columns([1, 1, 3])

        with d_col1:
          csv_data = df_attendance.to_csv(index=False).encode("utf-8")
          st.download_button(
              label="📥 Download CSV",
              data=csv_data,
              file_name="attendance_records.csv",
              mime="text/csv",
              use_container_width=True,
          )

        with d_col2:
          excel_data = to_excel(df_attendance)
          st.download_button(
              label="📥 Download Excel",
              data=excel_data,
              file_name="attendance_records.xlsx",
              mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
              use_container_width=True,
          )
    else:
      st.warning("No attendance records found.")

  # Tab 4: Manage Users (Fetch & Update User Information)
  with tabs[3]:
    st.header("All Registered Users")
    df_users = get_all_users()

    if not df_users.empty:
      st.dataframe(df_users, use_container_width=True)

      st.divider()
      st.subheader("Update User Information")

      # Create dropdown options mapped to user rows
      user_options = {
          f"{row['RollNo']} - {row['Name']} ({row['Branch']})": row
          for _, row in df_users.iterrows()
      }
      selected_user_label = st.selectbox(
          "Select User to Edit:", list(user_options.keys())
      )
      selected_user = user_options[selected_user_label]

      with st.form("edit_user_form"):
        edit_roll = st.text_input("Roll Number:", value=selected_user["RollNo"])
        edit_name = st.text_input("Name:", value=selected_user["Name"])
        edit_branch = st.text_input("Branch:", value=selected_user["Branch"])

        save_changes = st.form_submit_button("Save Changes")
        if save_changes:
          if edit_roll and edit_name and edit_branch:
            update_user_info(
                selected_user["RollNo"], edit_roll, edit_name, edit_branch
            )
            st.success(f"Updated information for {edit_name}!")
            st.rerun()
          else:
            st.warning("All fields are required.")
    else:
      st.info("No registered users found in StudentAttendance.")


# App Routing
if st.session_state.logged_in:
  main_app()
else:
  login_page()
