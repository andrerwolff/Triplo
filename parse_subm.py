import google.generativeai as genai
import os
import base64
from dotenv import load_dotenv

load_dotenv()  # Load .env file
api_key=os.getenv('GOOGLE_API_KEY')
print(api_key)
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

def ask_questions_pdf(pdf_path, questions):
    answers = []
    with open(pdf_path, 'rb') as pdf_file:
        pdf_bytes = pdf_file.read()
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_content = {
            'mime_type': 'application/pdf',
            'data': pdf_base64
        }
        for question in questions:
            response = model.generate_content([question, pdf_content])
            answers.append({"question": question, "answer": response.text})
    return answers

# Example usage
questions = ["What is the main topic?", "Summarize key points in 3 sentences."]
answers = ask_questions_pdf('resources/Subm 2402-006, Ferguson, PVC SDR35 PS46 Pipe, 4-15-24.pdf', questions)
with open('pdf_answers.json', 'w') as f:
    import json
    json.dump(answers, f, indent=2)