import streamlit as st
import lorem

st.set_page_config(
    page_title="Triplo",
    layout="wide",
)

st.write("# Welcome to Triplo! 👋")
st.write(lorem.paragraph())

st.sidebar.button("Manage Account")
st.sidebar.button("Prefrences")

project_list = ["*Lafayette WRF Improvements*", "*NWC - CSU Spur*"]

c1 = st.container(border=True)
c1.header("Project List")

for project in project_list:
    expander = c1.expander(project)
    expander.write(lorem.sentence())
    expander.button("Go to Project", key=project)

c2 = st.container(border=True)
c2.button("Start New Project")