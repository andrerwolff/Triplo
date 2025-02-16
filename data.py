import streamlit as st
from st_files_connection import FilesConnection


# Create connection object and retrieve file contents.
# Specify input format is a  csv and to cache the result for 600 seconds.
conn_gcs = st.connection ('gcs', type=FilesConnection)
df = conn_gcs.read("triplo_001/myfile.csv", input_format="csv", ttl=600)

# Print Results
for row in df.itertuples():
    st.write(f"{row.owner} has a :{row.pet}")

#Create the SQL connection to triplo_db as specified in secrets file
#conn = st.connection('triplo_db', type='sql')

# https://docs.streamlit.io/develop/concepts/connections/connecting-to-data For when i get here
