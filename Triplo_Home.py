import streamlit as st
import lorem

# Define the pages
# Home page, where the user can see a list of projects and create a new project
def home_page():
    st.write("# Welcome to Triplo! 👋")
    st.write(lorem.paragraph())

    # Container to display a list of projects
    c1 = st.container(border=True)
    c1.header("Project List")
    # Cycle through the list of projects and display them in an expander
    for project in st.session_state.project_list:
        expander = c1.expander(project, expanded=False)
        expander.write(lorem.sentence())

        col1, col2 = expander.columns([0.8,0.2])
        # Button to navigate to the project page
        if col1.button("Go To Project :arrow_right:", key="go_"+project):
            st.session_state.project_name = project
            st.session_state.page = "project"
            st.rerun()
        if col2.button(":x:*Delete Project*", key="del_"+project):
            st.session_state.project_list.remove(project)
            st.rerun()

    # Dialog box to create a new project
    @st.dialog("Create New Project")
    def newProject():
        st.write("Complete the below information to set up a new project.")
        project_name = st.text_input("Project Name")
        if st.button("Submit"):
            st.session_state.project_list.append(project_name)
            st.rerun()
    # Button to open dialog box for a new project
    c2 = st.container(border=True)
    if c2.button("Start New Project"):
        newProject()

# Project page, where the user can see the details of a project
def project_page(project_name):
    st.write(f"# Project: {project_name}")
    st.write(lorem.paragraph())

    # Button to navigate back to the home page
    if st.button("Back to Home", key="home"):
        st.session_state.page = "home"
        st.rerun()

# Initialize the session states
if 'project_list' not in st.session_state:
    st.session_state.project_list = ["Lafayette WRF Improvements", "NWC - CSU Spur"]
if 'page' not in st.session_state:
    st.session_state.page = "home"

# Render the page based on the current state
if st.session_state.page == "home":
    home_page()
elif st.session_state.page == "project":
    project_page(st.session_state.project_name)

# Sidebar, where the user can manage their account and preferences. Present on all pages
st.sidebar.button("Manage Account")
st.sidebar.button("Prefrences")
