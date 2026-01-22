from app.pdf.pdf_context_sample import sample_pdf_context
from app.pdf.pdf_generator import generate_monthly_prediction_pdf

pdf_bytes = generate_monthly_prediction_pdf(sample_pdf_context)

with open("monthly_prediction_test.pdf", "wb") as f:
    f.write(pdf_bytes)
