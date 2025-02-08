import streamlit as st
import lorem
from project_page import project_page
from project import Project

# Set the page configuration
st.set_page_config(
    page_title="Triplo",
    page_icon=":material/animation:",
    layout="wide",
    initial_sidebar_state="auto",
)

# Initialize the session states
if 'project_list' not in st.session_state:
    p1 = Project("Lafayette WRF", "Wastewater Treatment Plant")
    p2 = Project("NWC - CSU Spur", "Structure - Higher Education")
    st.session_state.project_list = [p1, p2]
if 'page' not in st.session_state:
    st.session_state.page = "home"

# Sidebar, where the user can manage their account and preferences. Present on all pages
st.sidebar.title(":material/animation:  Triplo")

if st.sidebar.button("Home", icon=":material/home:",key="home", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()

expander = st.sidebar.expander("Projects", icon=":material/library_books:")
left, right = expander.columns([0.1,0.9])
for project in st.session_state.project_list:
    if right.button(project.name, key="proj_"+project.name, type="tertiary"):
        st.session_state.project = project
        st.session_state.page = "project"
        st.rerun()
if right.button("New Project",icon=":material/add:", key="new_proj", type="secondary"):
    st.session_state.page = "home"
    st.rerun()
st.sidebar.divider()
st.sidebar.button("Settings", icon=":material/settings:",key="settings", type="tertiary")
st.sidebar.button("Help",icon=":material/help:", key="help", type="tertiary")


# Define the pages
# Home page, where the user can see a list of projects and create a new project
def home_page():
    st.title(":material/animation: Dashboard")

    # Container to display a list of projects
    c1 = st.container(border=True)
    c1.header("Active Projects")
    # Cycle through the list of projects and display them in an expander
    for project in st.session_state.project_list:
        if project.status == "Active":
            expander = c1.expander(project.name, expanded=False)
            expander.write(str(project))

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



# Render the page based on the current state
if st.session_state.page == "home":
    home_page()
elif st.session_state.page == "project":
    project_page(st.session_state.project)