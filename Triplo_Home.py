import streamlit as st
import lorem
from project_page import project_page
from project import Project

# Set the page configuration
st.set_page_config(
    page_title="Triplo",
    layout="wide",
    initial_sidebar_state="collapsed",
)

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
        expander = c1.expander(project.name, expanded=False)
        expander.write(lorem.sentence())

        col1, col2 = expander.columns([0.8,0.2])
        # Button to navigate to the project page
        if col1.button("Go To Project :arrow_right:", key="go_"+project.name):
            st.session_state.project = project
            st.session_state.page = "project"
            st.rerun()
        if col2.button(":x:*Delete Project*", key="del_"+project.name):
            st.session_state.project_list.remove(project)
            st.rerun()

    # Dialog box to create a new project
    @st.dialog("Create New Project")
    def newProject():
        st.write("Complete the below information to set up a new project.")
        project_name = st.text_input("Project Name")
        if st.button("Submit"):
            p1 = Project(project_name)
            st.session_state.project_list.append(p1)
            st.rerun()
    # Button to open dialog box for a new project
    c2 = st.container(border=True)
    if c2.button("Start New Project"):
        newProject()

# Initialize the session states
if 'project_list' not in st.session_state:
    p1 = Project("Lafayette WRF Improvements")
    p2 = Project("NWC - CSU Spur")
    st.session_state.project_list = [p1, p2]
if 'page' not in st.session_state:
    st.session_state.page = "home"

# Render the page based on the current state
if st.session_state.page == "home":
    home_page()
elif st.session_state.page == "project":
    project_page(st.session_state.project)

# Sidebar, where the user can manage their account and preferences. Present on all pages
st.sidebar.button("Manage Account")
st.sidebar.button("Prefrences")
