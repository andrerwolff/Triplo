import google.generativeai as genai
import streamlit as st

st.title ('Triplo')

st.sidebar.button("Hello World")
    

""" THIS WORKS FOR SIMPLE CHAT BOT
#connect api key
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

#set model in app state (??? Look into this more)
if "gemini_model" not in st.session_state:
    st.session_state["gemini_model"] = "gemini-1.5-flash"

#initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

#Display old messages (not sure about role and content right now)
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

#Assign and determine messages user will enter (investigate the loop here)
if prompt := st.chat_input("What is up?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    #appointments?
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        # Simulate stream of response with milliseconds delay
        response = model.generate_content(
            prompt,
            stream=True,
        )

        for chunk in response:
            full_response += chunk.text
            message_placeholder.markdown(full_response + "▌")
        
        message_placeholder.markdown(full_response)

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})
"""