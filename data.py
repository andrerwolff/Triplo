import streamlit as st

#Create the SQL connection to triplo_db as specified in secrets file
conn = st.connection('triplo_db', type='sql')

# https://docs.streamlit.io/develop/concepts/connections/connecting-to-data For when i get here
