import streamlit as st
import lorem
from project import Project
import docx # Reads Word files

from docx import Document  


def extract_text_from_docx(docx_file):
    """Extracts text from a Word (.docx) file."""
    doc = Document(docx_file)  # Open the Word file
    text = "\n".join([para.text for para in doc.paragraphs])  # Get text from each paragraph
    return text


import fitz  # PyMuPDF
import io  # To handle the in-memory file

def extract_text_from_pdf(pdf_file):
    """Extracts text from a PDF file."""
    try:
        # Check if file is empty
        if pdf_file is None or pdf_file.size == 0:
            st.error("The uploaded PDF file is empty.")
            return None
        
        # Create a BytesIO object from the uploaded file
        pdf_bytes = pdf_file.getvalue()
        pdf_stream = io.BytesIO(pdf_bytes)
        
        # Open the PDF from the in-memory stream
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        
        text = ""
        # Extract text from each page
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text()
            
        doc.close()
        
        # Check if any text was extracted
        if not text.strip():
            st.warning("No text extracted from the PDF. It may be an image-based PDF.")
            return "No extractable text found (possibly an image-based PDF)"
        
        return text
    except Exception as e:
        st.error(f"An error occurred while processing the PDF: {str(e)}")
        return None




def project_page(project):
    st.title(project.name)
    st.subheader("Project Description", divider="gray")

    proj_dash, proj_ref, subs, rfis = st.tabs(["Project Dashboard", "Project Reference Docs", "Submittals", "RFIs"])

    # 📂 **Reference Documents Tab**
    with proj_ref:
        uploaded_files = st.file_uploader("Add a reference document", type=["txt", "docx", "pdf"], accept_multiple_files=True)
        for uploaded_file in uploaded_files:
            bytes_data = uploaded_file.read()
            st.write("filename:", uploaded_file.name)
            
            if uploaded_file.name.endswith(".txt"):
                st.write(bytes_data.decode("utf-8"))  # Display text from .txt files

            elif uploaded_file.name.endswith(".docx"):
                text = extract_text_from_docx(uploaded_file)
                st.write(text)  # Display the extracted text from docx

            elif uploaded_file.name.endswith(".pdf"):
                text = extract_text_from_pdf(uploaded_file)
                st.write(text)  # Display the extracted text from pdf
            

    # 📂 **Submittals Tab**
    with subs:
        in_process, completed = st.tabs(["Under Review", "Completed"])

        with in_process:
            st.subheader("Upload a Submittal")
            submittal_file = st.file_uploader("Upload a submittal (.pdf, .docx)", 
                                              type=["pdf", "docx"])

            if submittal_file:
                st.write(f"Uploaded: **{submittal_file.name}**")

                if submittal_file.type == "application/pdf":  # Handling PDF
                    sub_text = extract_text_from_pdf(submittal_file)
                elif submittal_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":  # Handling .docx
                    sub_text = extract_text_from_docx(submittal_file)
                
                st.text_area("Extracted Content", sub_text, height=200)

        with completed:
            st.write("📂 Closed Submittals will be shown here.")

    # 🔙 **Return Home Button**
    if st.button("Return Home", icon=":material/home:"):
        st.session_state.page = "home"
        st.rerun()

    st.write(f"PyMuPDF version: {fitz.__version__}")
