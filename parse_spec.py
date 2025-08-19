import PyPDF2

def extract_text_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for page in reader.pages:
            text += page.extract_text() or ''
    return text

# Example usage
text = extract_text_pdf('46 41 00 Submerged Turbine Mixers.pdf')
with open('extracted_text.txt', 'w') as f:
    f.write(text)