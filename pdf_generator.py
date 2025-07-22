import json
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvass

# Read JSON from file
with open('data.json', 'r') as file:
    cv_data = json.load(file)
s
# Generate PDF
def generate_cv_pdf(cv, filename):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    y = height - 50

    def write_line(text, indent=0):
        nonlocal y  
        if y < 50:
            c.showPage()
            y = height - 50
        c.drawString(50 + indent, y, text)
        y -= 20

    c.setFont("Helvetica-Bold", 16)
    write_line(cv["name"])
    c.setFont("Helvetica", 12)
    write_line(f"Email: {cv['email']}")
    write_line(f"Location: {cv['location']}")
    write_line(f"Desired Role: {cv['desired_job_title']}")
    y -= 10

    write_line("Skills:")
    for skill in cv["skills"]:
        write_line(f"- {skill}", indent=20)

    y -= 10
    write_line("Work Experience:")
    for job in cv["work_experience"]:
        write_line(f"{job['job_title']} at {job['company']} ({job['begin_date']} to {job['end_date']})", indent=20)
        write_line(f"Position: {job['position']}, Location: {job['location']}", indent=40)

    y -= 10
    write_line("Education:")
    for edu in cv["education"]:
        write_line(f"{edu['institution']} - {edu['area_of_study']} ({edu['begin_date']} to {edu['end_date']})", indent=20)
        write_line(f"Location: {edu['location']}", indent=40)

    c.save()

# Save PDF
generate_cv_pdf(cv_data, "cv_output.pdf")
