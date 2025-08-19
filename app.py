import google.generativeai as genai
import os
import base64
import json
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

app = FastAPI()

# Enable CORS for GitHub Pages frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://andrerwolff.github.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Load API Key ----
load_dotenv()
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

# ---- Gemini Model ----
model = genai.GenerativeModel('gemini-2.0-flash')

# ---- Helper: Read file and convert to Gemini format ----
def encode_pdf_to_gemini_content(pdf_bytes):
    encoded = base64.b64encode(pdf_bytes).decode('utf-8')
    return {"mime_type": "application/pdf", "data": encoded}



# ---- Main Generator ----
@app.post("/generate_review")
async def generate_review(spec_text: str = Form(...), submittal: UploadFile = File(...)):
    pdf_content = encode_pdf_to_gemini_content(await submittal.read())
    prompt = """
You are an experienced civil engineer assisting a junior engineer with a high-level product submittal review. You are not writing a formal response, but providing an internal review summary.

You are given:
- A text-based specification section (Spec.txt)
- A multimedia product submittal PDF (Submittal.pdf)

Your job is to:
1. Extract key information from the product submittal
2. Compare that information to the specification section
3. Provide structured findings that include:

Section 1: Summary of Submitted Product
- Product Name / Model:
- Manufacturer:
- Key features / performance data:
- Certifications or test data included:
- Notable product images or diagrams: 

Section 2: Compliance Snapshot
(Use the specification requirements as a checklist. For each item, assign a code in brackets based on your assessment, and include a legend:

[C] – Likely Compliant
[X] – Likely Non-Compliant
[U] – Unclear or Needs Further Review)

Example format:
[C] Manufacturer is listed in the spec (or equal?)
[U] Product appears to meet performance criteria (e.g., psi, flow rate, material grade)
[X] Submittal includes test data or certifications required
[C] Installation instructions or procedures are included
[U] Warranty or maintenance info provided (if required)

Section 3: Potential Issues or Gaps
- Any missing or ambiguous info?
- Vague or overly broad submittal language?
- Product line submitted instead of specific model?
- Overreliance on marketing content?

Section 4: Recommendations for Engineer Review
- What should a junior engineer flag for deeper review?
- Any key follow-up questions?

Be helpful, direct, and concise. If unsure, defer to project team review. Avoid assumptions.
"""

    # Combine prompt and inputs
    response = model.generate_content([prompt, spec_text, pdf_content])
    return {"review": response.text}

# ---- Example Usage ----
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)