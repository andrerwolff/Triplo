import streamlit as st
import lorem
from project import Project
from submittal import Submittal

def project_page(project: Project):
    st.title(project.name)
    st.subheader(project.desc, divider="gray")

    with st.expander("Project References", icon=":material/summarize:"):
        for resource in project.project_resources:
            st.write(resource.name)
        st.divider()

        if 'uploaded_file' not in st.session_state:
            st.session_state.uploaded_file = None

        uploaded_file = st.file_uploader("Upload Project Reference")
        if uploaded_file is not None and uploaded_file != st.session_state.uploaded_file:
            if uploaded_file.name not in [r.name for r in project.project_resources]:
                project.add_project_resource(uploaded_file)
                st.session_state.uploaded_file = uploaded_file
                st.rerun()

    with st.expander("Submittals", icon=":material/docs:"):
        # Cycle through the list of projects and display them in an expander
        for submittal in project.submittals:
            st.button(submittal.name)
        st.divider()

        if 'uploaded_file' not in st.session_state:
            st.session_state.uploaded_file = None

        uploaded_file = st.file_uploader("Upload Submittal")
        if uploaded_file is not None and uploaded_file != st.session_state.uploaded_file:
            if uploaded_file.name not in [r.name for r in project.submittals]:
                project.add_submittal(uploaded_file)
                st.session_state.uploaded_file = uploaded_file
                st.rerun()