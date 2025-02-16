import streamlit as st
from project import Project
from submittal import Submittal
from constants import CSI_DIVS

def submittal_page(project: Project, submittal: Submittal):
    st.title(submittal.name)
    st.subheader(project.name, divider="gray")

    with st.expander("Specification References:"):
        for spec_ref in submittal.spec_ref:
            st.write(spec_ref)
        if st.button("Add Specification Reference"):
            add_spec_ref(submittal)
    
    st.write("Comments:")
    st.write(submittal.comments)
    comment = st.text_area("Add Comments:")
    if comment is not None:
        print(comment)





@st.dialog("Add Spec Ref")
def add_spec_ref(submittal):
    with st.form("new_spec_ref", border=False):
        spec_refs = st.multiselect("Relevent Specifications:", CSI_DIVS)
        submittal.add_spec_refs(spec_refs)

        if st.form_submit_button():
            st.rerun()
