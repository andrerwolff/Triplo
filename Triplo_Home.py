import streamlit as st
import lorem

st.set_page_config(
    page_title="Triplo",
    layout="wide",
    initial_sidebar_state="collapsed",
)

'''def project_page():
    st.write("Project Page")
    st.write(st.session_state.project)'''

st.write("# Welcome to Triplo! 👋")
st.write(lorem.paragraph())

st.sidebar.button("Manage Account",)
st.sidebar.button("Prefrences")

if 'project_list' not in st.session_state:
    st.session_state.project_list = ["Lafayette WRF Improvements", "NWC - CSU Spur"]

c1 = st.container(border=True)
c1.header("Project List")

for project in st.session_state.project_list:
    expander = c1.expander(project)
    expander.write(lorem.sentence())
    expander.button("Open Project", key=project)


@st.dialog("Create New Project")
def newProject():
    st.write("Complete the below information to set up a new project.")
    project_name = st.text_input("Project Name")
    if st.button("Submit"):
        st.session_state.project_list.append(project_name)
        st.rerun()

c2 = st.container(border=True)
if c2.button("Start New Project"):
    newProject()

