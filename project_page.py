import io
import hashlib
import streamlit as st
from docx import Document
import fitz  # PyMuPDF

from project import Project
from storage import save_projects


def _content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@st.cache_data(show_spinner="Extracting text from PDF…")
def extract_text_from_pdf_cached(_content_hash_key: str, pdf_bytes: bytes) -> str | None:
    """Extracts text from PDF bytes. Cached by content hash."""
    if not pdf_bytes:
        return None
    try:
        pdf_stream = io.BytesIO(pdf_bytes)
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text()
        doc.close()
        if not text.strip():
            return "No extractable text found (possibly an image-based PDF)"
        return text
    except Exception:
        return None


def extract_text_from_pdf(pdf_bytes_or_file) -> str | None:
    """Extracts text from a PDF (bytes, BytesIO, or file-like with .getvalue())."""
    if pdf_bytes_or_file is None:
        return None
    if hasattr(pdf_bytes_or_file, "getvalue"):
        pdf_bytes = pdf_bytes_or_file.getvalue()
    elif isinstance(pdf_bytes_or_file, bytes):
        pdf_bytes = pdf_bytes_or_file
    else:
        pdf_bytes = pdf_bytes_or_file.read()
    if not pdf_bytes:
        st.error("The uploaded PDF file is empty.")
        return None
    key = _content_hash(pdf_bytes)
    result = extract_text_from_pdf_cached(key, pdf_bytes)
    if result is None:
        st.error("An error occurred while processing the PDF.")
    elif result == "No extractable text found (possibly an image-based PDF)":
        st.warning("No text extracted from the PDF. It may be an image-based PDF.")
    return result


@st.cache_data(show_spinner="Extracting text from document…")
def extract_text_from_docx_cached(_content_hash_key: str, docx_bytes: bytes) -> str | None:
    """Extracts text from DOCX bytes. Cached by content hash."""
    if not docx_bytes:
        return None
    try:
        stream = io.BytesIO(docx_bytes)
        doc = Document(stream)
        return "\n".join(para.text for para in doc.paragraphs)
    except Exception:
        return None


def extract_text_from_docx(docx_bytes_or_file):
    """Extracts text from a Word .docx (bytes, BytesIO, or file-like)."""
    if docx_bytes_or_file is None:
        return None
    if hasattr(docx_bytes_or_file, "getvalue"):
        docx_bytes = docx_bytes_or_file.getvalue()
    elif isinstance(docx_bytes_or_file, bytes):
        docx_bytes = docx_bytes_or_file
    else:
        docx_bytes = docx_bytes_or_file.read()
    if not docx_bytes:
        return None
    key = _content_hash(docx_bytes)
    return extract_text_from_docx_cached(key, docx_bytes) or ""


# Max file size (MB) before warning
MAX_FILE_SIZE_MB = 50


def _get_bytes(uploaded_file) -> bytes | None:
    """Read file once; warn if too large."""
    if uploaded_file is None:
        return None
    size_mb = uploaded_file.size / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        st.warning(f"Large file ({size_mb:.1f} MB). Extraction may be slow.")
    return uploaded_file.getvalue()


def project_page(project):
    st.caption(f"Home \u203a Projects \u203a {project.name}")
    st.title(project.name)
    st.subheader("Project Description", divider="gray")

    proj_dash, proj_ref, subs, rfis = st.tabs(["Project Dashboard", "Project Reference Docs", "Submittals", "RFIs"])

    # Project Dashboard
    with proj_dash:
        st.subheader("Overview")
        st.write(f"**Project:** {project.name}")
        if hasattr(project, "reference_docs") and project.reference_docs:
            st.write(f"**Reference documents:** {len(project.reference_docs)}")
        else:
            st.write("**Reference documents:** 0")
        open_count = len(project.open_submittals) if hasattr(project, "open_submittals") else 0
        closed_count = len(project.closed_submittals) if hasattr(project, "closed_submittals") else 0
        st.write(f"**Submittals:** {open_count} under review, {closed_count} completed")
        if hasattr(project, "rfis") and project.rfis:
            st.write(f"**RFIs:** {len(project.rfis)}")
        st.caption("Use the other tabs to add reference docs, submittals, and RFIs.")

    # Reference Documents Tab
    with proj_ref:
        from constants import CSI_DIVS
        st.subheader("Reference Documents")
        if hasattr(project, "reference_docs") and project.reference_docs:
            for ref in project.reference_docs:
                with st.expander(ref.get("name", "Document"), expanded=False):
                    csi = ref.get("csi_division")
                    if csi:
                        st.caption(f"CSI: {csi}")
                    st.text_area("Content", ref.get("extracted_text", ""), height=200, key=f"ref_{ref.get('id', id(ref))}")
        st.subheader("Add a reference document")
        csi_division = st.selectbox("CSI Division (optional)", [""] + list(CSI_DIVS), key="ref_csi")
        uploaded_files = st.file_uploader("Add a reference document", type=["txt", "docx", "pdf"], accept_multiple_files=True)
        for uploaded_file in uploaded_files:
            bytes_data = _get_bytes(uploaded_file)
            if bytes_data is None:
                continue
            st.write("filename:", uploaded_file.name)
            try:
                if uploaded_file.name.endswith(".txt"):
                    text = bytes_data.decode("utf-8", errors="replace")
                elif uploaded_file.name.endswith(".docx"):
                    text = extract_text_from_docx(bytes_data) or ""
                elif uploaded_file.name.endswith(".pdf"):
                    text = extract_text_from_pdf(bytes_data) or ""
                else:
                    text = ""
                if text is not None:
                    st.text_area("Extracted Content", text, height=200, key=f"ref_upload_{uploaded_file.name}_{id(uploaded_file)}")
                    if st.button("Save to project", key=f"save_ref_{uploaded_file.name}_{id(uploaded_file)}"):
                        if not hasattr(project, "reference_docs"):
                            project.reference_docs = []
                        project.reference_docs.append({
                            "name": uploaded_file.name,
                            "csi_division": csi_division or None,
                            "extracted_text": text,
                        })
                        save_projects(st.session_state.get("project_list", []))
                        st.rerun()
            except Exception as e:
                st.error(f"Could not process this file: {e}")

        # Optional: Ask Gemini about reference documents
        with st.expander("Ask about your documents (Gemini)"):
            try:
                api_key = st.secrets.get("GEMINI_API_KEY")
            except Exception:
                api_key = None
            if api_key:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                context_parts = []
                if hasattr(project, "reference_docs") and project.reference_docs:
                    for ref in project.reference_docs[:5]:
                        t = ref.get("extracted_text", "")
                        if t:
                            context_parts.append(f"[{ref.get('name', 'Doc')}]\n{t[:8000]}")
                context = "\n\n".join(context_parts) if context_parts else "No reference documents yet."
                chat_key = f"gemini_messages_{project.name}"
                if chat_key not in st.session_state:
                    st.session_state[chat_key] = []
                for msg in st.session_state[chat_key]:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
                if prompt := st.chat_input("Ask about your reference documents…"):
                    st.session_state[chat_key].append({"role": "user", "content": prompt})
                    with st.chat_message("assistant"):
                        model = genai.GenerativeModel("gemini-1.5-flash")
                        full_response = ""
                        resp = model.generate_content(
                            f"Use the following project reference document excerpts to answer. If the answer is not in the documents, say so.\n\n---\n{context}\n---\n\nQuestion: {prompt}",
                            stream=True,
                        )
                        for chunk in resp:
                            full_response += (chunk.text or "")
                        st.markdown(full_response)
                    st.session_state[chat_key].append({"role": "assistant", "content": full_response})
                    st.rerun()
            else:
                st.caption("Add GEMINI_API_KEY to Streamlit secrets to enable. See README.")

    # Submittals Tab
    with subs:
        in_process, completed = st.tabs(["Under Review", "Completed"])
        with in_process:
            st.subheader("Under Review")
            if hasattr(project, "open_submittals") and project.open_submittals:
                for sub in project.open_submittals:
                    if isinstance(sub, dict):
                        with st.expander(sub.get("name", "Submittal"), expanded=False):
                            st.text_area("Content", sub.get("extracted_text", ""), height=150, key=f"sub_open_{sub.get('id', id(sub))}")
                            if st.button("Mark completed", key=f"complete_{sub.get('id', id(sub))}"):
                                if not hasattr(project, "closed_submittals"):
                                    project.closed_submittals = []
                                project.closed_submittals.append(sub)
                                project.open_submittals.remove(sub)
                                save_projects(st.session_state.get("project_list", []))
                                st.rerun()
                    else:
                        st.write(sub)
            st.subheader("Upload a Submittal")
            from constants import CSI_DIVS
            sub_csi = st.selectbox("CSI Division (optional)", [""] + list(CSI_DIVS), key="sub_csi")
            submittal_file = st.file_uploader("Upload a submittal (.pdf, .docx)", type=["pdf", "docx"])
            if submittal_file:
                st.write(f"Uploaded: **{submittal_file.name}**")
                bytes_data = _get_bytes(submittal_file)
                if bytes_data:
                    with st.spinner("Extracting text…"):
                        if submittal_file.type == "application/pdf":
                            sub_text = extract_text_from_pdf(bytes_data)
                        else:
                            sub_text = extract_text_from_docx(bytes_data)
                    if sub_text is not None:
                        st.text_area("Extracted Content", sub_text, height=200, key="sub_upload_content")
                        if st.button("Add to Under Review"):
                            if not hasattr(project, "open_submittals"):
                                project.open_submittals = []
                            if isinstance(project.open_submittals, list) and project.open_submittals and isinstance(project.open_submittals[0], str):
                                project.open_submittals = []
                            project.open_submittals.append({
                                "name": submittal_file.name,
                                "csi_division": sub_csi or None,
                                "extracted_text": sub_text,
                            })
                            save_projects(st.session_state.get("project_list", []))
                            st.rerun()
        with completed:
            st.subheader("Completed")
            if hasattr(project, "closed_submittals") and project.closed_submittals:
                for sub in project.closed_submittals:
                    if isinstance(sub, dict):
                        with st.expander(sub.get("name", "Submittal"), expanded=False):
                            st.text_area("Content", sub.get("extracted_text", ""), height=150, key=f"sub_closed_{sub.get('id', id(sub))}")
                    else:
                        st.write(sub)
            else:
                st.write("Closed submittals will appear here.")

    # RFIs Tab
    with rfis:
        st.subheader("RFIs")
        if hasattr(project, "rfis") and project.rfis:
            for rfi in project.rfis:
                with st.expander(f"{rfi.get('title', 'RFI')} — {rfi.get('status', 'Open')}", expanded=False):
                    st.write("**Date:**", rfi.get("date", ""))
                    st.write(rfi.get("description", ""))
        else:
            st.write("No RFIs yet.")
        with st.expander("Add RFI"):
            rfi_title = st.text_input("Title")
            rfi_desc = st.text_area("Description")
            rfi_status = st.selectbox("Status", ["Open", "Answered", "Closed"])
            if st.button("Add RFI"):
                if not hasattr(project, "rfis"):
                    project.rfis = []
                from datetime import datetime
                project.rfis.append({
                    "title": rfi_title or "Untitled",
                    "description": rfi_desc,
                    "status": rfi_status,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                })
                save_projects(st.session_state.get("project_list", []))
                st.rerun()

    # Navigation back home is intentionally handled via breadcrumb / app nav.
