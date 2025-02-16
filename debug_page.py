import streamlit as st
from user import User
from project import Project
from submittal import Submittal
from reference import Reference
from google.cloud import storage
import pymupdf4llm

def debug_page():
    #for project in st.session_state.user.project_list:
        #st.write(project)
        #for ref in project.references:
            #st.write(ref)
        #for sub in project.submittals:
            #st.write(sub)
    #client = storage.Client()
    #bucket_name = "triplo_001"
    #file_name = "Subm 2402-006, Ferguson, PVC SDR35 PS46 Pipe, 4-15-24.pdf"
    loc_file_name = "resources/33 05 05.02 Buried Piping-Gravity_v0.5.pdf"

    #bucket = client.bucket(bucket_name)
    #blob = bucket.blob(file_name)


    md_text = pymupdf4llm.to_markdown(loc_file_name)
    st.markdown(md_text)