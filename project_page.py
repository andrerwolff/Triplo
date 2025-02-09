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
        uploaded_file = st.file_uploader("Upload Project Reference")
        if uploaded_file is not None:
            project.add_project_resource(uploaded_file)
            st.rerun()


    with st.expander("Submittals", icon=":material/docs:"):
        in_process, completed = st.tabs(["Under Review", "Completed"])
        with in_process:
            # Container to display submittals
            c1 = st.container(border=True)
            # Cycle through the list of projects and display them in an expander
            for submittal in project.submittals:
                if submittal.status == "Active":
                    expander = c1.expander(submittal, expanded=False)
                    expander.write(lorem.sentence())

                    col1, col2 = expander.columns([0.8,0.2])
                    # Button to navigate to the project page
                    if col1.button("Go To Submittal :arrow_right:", key="go_"+submittal):
                        st.session_state.submittal = submittal
                        st.session_state.page = "submittal"
                        st.rerun()
                    if col2.button(":x:*Delete Submittal*", key="del_"+submittal):
                        st.session_state.submittal_list.remove(submittal)
                        st.rerun()
        with completed:
            c2 = st.container(border=True)
            # Cycle through the list of projects and display them in an expander
            for submittal in project.submittals:
                if submittal.status == "Closed":
                    expander = c2.expander(submittal, expanded=False)
                    expander.write(lorem.sentence())

                    col1, col2 = expander.columns([0.8,0.2])
                    # Button to navigate to the project page
                    if col1.button("Go To Submittal :arrow_right:", key="go_"+submittal):
                        st.session_state.submittal = submittal
                        st.session_state.page = "submittal"
                        st.rerun()
                    if col2.button(":x:*Delete Submittal*", key="del_"+submittal):
                        st.session_state.submittal_list.remove(submittal)
                        st.rerun()
        st.divider()
        uploaded_file = st.file_uploader("Upload Submittal")
        if uploaded_file is not None:
            project.add_submittal(uploaded_file)
            st.rerun()