import streamlit as st
import lorem
from project import Project
from submittal import Submittal
from constants import CSI_DIVS


def project_page(project: Project):
    st.title(project.name)
    st.subheader(project.desc, divider="gray")

    with st.expander("Project References", icon=":material/summarize:"):
        for ref in project.references:
            st.write(ref.name)
        st.divider()
        if st.button("Upload Reference"):
            new_ref(project)

    
    

    with st.expander("Submittals", icon=":material/docs:"):
        # Cycle through the list of projects and display them in an expander
        for submittal in project.submittals:
            if st.button(submittal.name):
                st.session_state.submittal = submittal
                st.session_state.page = "submittal"
                st.rerun()
        st.divider()

        if st.button("Upload Submittal"):
            new_sub(project)


@st.dialog("Upload Reference")
def new_ref(project):
    with st.form("new_ref", border=False):
        ref_type = st.selectbox("What is this reference document",
            ("Specificaion", "Approved Products", "Other"),
            index=None,
            placeholder="Select reference type...",)
        comments = st.text_input("Comments:")

        if 'uploaded_file' not in st.session_state:
            st.session_state.uploaded_file = None

        uploaded_file = st.file_uploader("Upload Project Reference")
        if uploaded_file is not None and uploaded_file != st.session_state.uploaded_file:
            if uploaded_file.name not in [r.name for r in project.references]:
                project.add_reference(uploaded_file, ref_type, comments)
                st.session_state.uploaded_file = uploaded_file
        if st.form_submit_button():
            st.rerun()

@st.dialog("Upload Submittal") #num :int, name, spec_refs, references, status='Active'
def new_sub(project):
    with st.form("new_sub", border=False):
        num = st.text_input("Submittal Number:")
        name = st.text_input("Submittal Name:")
        spec_refs = st.multiselect("Relevent Specifications:", CSI_DIVS)
        comments = st.text_input("Comments:")

        if 'uploaded_file' not in st.session_state:
            st.session_state.uploaded_file = None

        uploaded_file = st.file_uploader("Upload Submittal")
        if uploaded_file is not None and uploaded_file != st.session_state.uploaded_file:
            if uploaded_file.name not in [r.name for r in project.submittals]:
                project.add_submittal(uploaded_file, num, comments, spec_refs)
                st.session_state.uploaded_file = uploaded_file

        if st.form_submit_button():
            st.rerun()