import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_interview_report(result_data, interview_data, student_name, job_title):
    """
    Generates a PDF report for the interview results.
    """
    report_filename = f"report_{result_data['interview_id']}.pdf"
    report_path = os.path.join("uploads", "reports", report_filename)
    
    # Ensure directory exists (redundant but safe)
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    doc = SimpleDocTemplate(report_path, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    normal_style = styles['Normal']
    
    elements = []
    
    # Header
    elements.append(Paragraph(f"Interview Report: {student_name}", title_style))
    elements.append(Paragraph(f"Job Role: {job_title}", subtitle_style))
    elements.append(Spacer(1, 12))
    
    # Summary Table
    summary_data = [
        ["Metric", "Value"],
        ["Interview Score", f"{result_data['interview_score']}%"],
        ["Job Match Score", f"{result_data['job_match_score']}%"],
        ["Final Weighted Score", f"{result_data['final_score']}%"],
        ["Overall Feedback", result_data['feedback']]
    ]
    
    summary_table = Table(summary_data, colWidths=[150, 300])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#333333")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f4f4f4")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 24))
    
    # Detailed Q&A Section
    elements.append(Paragraph("Detailed Question & Answer Analysis", subtitle_style))
    elements.append(Spacer(1, 12))
    
    for i, ans in enumerate(result_data['answers']):
        # Fetch original question data for options
        orig_q = interview_data['questions'][i]
        
        # Question Header
        elements.append(Paragraph(f"Question {i+1}: {ans['question']}", styles['Heading3']))
        
        # Options List
        options_html = "<br/>".join([f"&bull; {opt}" for opt in orig_q['options']])
        elements.append(Paragraph(f"<b>Options:</b><br/>{options_html}", normal_style))
        elements.append(Spacer(1, 6))
        
        # Student Answer & Correct Answer
        result_color = "green" if ans['is_correct'] else "red"
        status_text = "CORRECT" if ans['is_correct'] else "INCORRECT"
        
        elements.append(Paragraph(f"<b>Student Answer:</b> <font color='{result_color}'>{ans['student_answer']} ({status_text})</font>", normal_style))
        elements.append(Paragraph(f"<b>Correct Answer:</b> {ans['correct_answer']}", normal_style))
        elements.append(Spacer(1, 12))
        
        # Divider
        elements.append(Paragraph("<hr color='lightgrey' width='100%'/>", normal_style))
        elements.append(Spacer(1, 12))
        
    # Build PDF
    doc.build(elements)
    
    return f"/uploads/reports/{report_filename}"
