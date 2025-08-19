import google.generativeai as genai
import os
import base64
import json
from dotenv import load_dotenv

# ---- Load API Key ----
load_dotenv()
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

# ---- Gemini Model ----
model = genai.GenerativeModel('gemini-2.0-flash')

# ---- Helper: Read file and convert to Gemini format ----
def encode_pdf_to_gemini_content(pdf_path):
    with open(pdf_path, 'rb') as pdf_file:
        encoded = base64.b64encode(pdf_file.read()).decode('utf-8')
    return {
        "mime_type": "application/pdf",
        "data": encoded
    }

# ---- Main Generator ----
def generate_review(spec_text, pdf_path):
    pdf_content = encode_pdf_to_gemini_content(pdf_path)

    # Prompt is aligned with earlier guidance
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
    return response.text

# ---- Example Usage ----
if __name__ == "__main__":
    spec_file = 'resources/33 05 05.02 Buried Piping-Gravity_v1.txt'
    pdf_file = 'resources/Subm 2402-006, Ferguson, PVC SDR35 PS46 Pipe, 4-15-24.pdf'

    with open(spec_file, 'r') as f:
        spec_text = f.read()

    review = generate_review(spec_text, pdf_file)

    output_file = 'structured_submittal_review.txt'
    with open(output_file, 'w') as f:
        f.write(review)

    print(f"Submittal review written to: {output_file}")