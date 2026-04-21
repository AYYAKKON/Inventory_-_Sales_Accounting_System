import sys
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    print("ReportLab is installed and working!")
    c = canvas.Canvas("test_pdf.pdf", pagesize=letter)
    c.drawString(100, 750, "Hello World from ReportLab")
    c.save()
    print("PDF generated successfully.")
except ImportError:
    print("ReportLab is NOT installed.")
except Exception as e:
    print(f"An error occurred: {e}")
