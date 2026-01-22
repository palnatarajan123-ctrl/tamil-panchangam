@router.get("/prediction/{prediction_id}/pdf")
def download_prediction_pdf(prediction_id: str):
    prediction = load_prediction(prediction_id)

    pdf_context = build_pdf_context(
        chart_id=prediction.chart_id,
        prediction_id=prediction.id,
        month=prediction.month,
        year=prediction.year,
        interpretation=prediction.interpretation,
        explainability=build_explainability(...),
        d1_chart=prediction.envelope["rasi"]["planet_signs"],
        d9_chart=prediction.envelope["navamsa"]["planet_signs"],
        d9_dignity=prediction.envelope["navamsa"]["dignity"],
    )

    pdf_bytes = generate_monthly_prediction_pdf(pdf_context)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=monthly_prediction.pdf"
        },
    )
