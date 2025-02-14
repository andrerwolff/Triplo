import streamlit as st
from user import User
from project import Project
from submittal import Submittal
from reference import Reference


def debug_page():
    for project in st.session_state.user.project_list:
        st.write(project)
        for ref in project.references:
            st.write(ref)
        for sub in project.submittals:
            st.write(sub)

