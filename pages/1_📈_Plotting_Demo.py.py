import streamlit as st
import lorem

st.set_page_config(
    page_title="New Project",
    layout="centered",
)
st.title("New Project")
col1, col2 = st.columns(2)
col1.write(lorem.paragraph())
col2.write(lorem.sentence())

st.button("click me")
st.write(lorem.paragraph())