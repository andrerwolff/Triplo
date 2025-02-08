import streamlit as st
import lorem
from project import Project

def project_page(project):
    st.title(project.name)
    st.subheader("Project Description", divider="gray")

    proj_dash, proj_ref, subs, rfis = st.tabs(["Project Dashboard", "Project Reference Docs", "Submittals", "RFIs"])

    with proj_ref:
        uploaded_files = st.file_uploader("Add a reference document (.txt).", type="'txt'" ,accept_multiple_files=True)
        for uploaded_file in uploaded_files:
            bytes_data = uploaded_file.read()
            st.write("filename:", uploaded_file.name)
            st.write(bytes_data)


    with subs:
        in_process, completed = st.tabs(["Under Review", "Completed"])
        with in_process:
            # Container to display submittals
            c1 = st.container(border=True)
            c1.header("Active Submittals")
            # Cycle through the list of projects and display them in an expander
            for submittal in project.open_submittals:
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
            c2.header("Closed Submittals")
            # Cycle through the list of projects and display them in an expander
            for submittal in project.closed_submittals:
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

    # Button to navigate back to the home page
    if st.button("Return Home",icon=":material/home:", key="homex"):
        st.session_state.page = "home"
        st.rerun()