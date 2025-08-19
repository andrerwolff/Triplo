import google.generativeai as genai
import os
import base64
import json
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

def generate_answers(spec_text, submittal_pdf_path, questions):
    answers = []
    with open(submittal_pdf_path, 'rb') as pdf_file:
        pdf_bytes = pdf_file.read()
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_content = {'mime_type': 'application/pdf', 'data': pdf_base64}
        for question in questions:
            prompt = f"Using this specification text: '{spec_text}' and the provided submittal PDF, answer: {question}"
            response = model.generate_content([prompt, pdf_content])
            answers.append({"question": question, "answer": response.text})
    return answers

# Example usage
with open('resources/33 05 05.02 Buried Piping-Gravity_v1.txt', 'r') as f:
    spec_text = f.read()
with open('questions.json', 'r') as f:
    questions = json.load(f)['questions']
answers = generate_answers(spec_text, 'resources/Subm 2402-006, Ferguson, PVC SDR35 PS46 Pipe, 4-15-24.pdf', questions)
with open('combined_answers.json', 'w') as f:
    json.dump(answers, f, indent=2)