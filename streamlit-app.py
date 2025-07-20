import os
import json
import smtplib
from email.message import EmailMessage
from typing import List, Dict

import streamlit as st

# Optional: only required if you want LLM‑generated interview questions
try:
    import openai  # type: ignore
except ImportError:
    openai = None  # graceful fallback if package not installed

################################################################################
# Helper functions – one per agent in your architecture diagram
################################################################################

def crawl_jobs(keyword: str, num_results: int = 10) -> List[Dict]:
    """Return a list of job dicts for the UI.

    Replace this stub with Selenium/Playwright or a third‑party API.
    """
    return [
        {
            "title": f"{keyword} Engineer {i + 1}",
            "company": "Acme Corp",
            "location": "Remote",
            "snippet": "We are looking for a talented …",
            "url": f"https://example.com/job/{i + 1}",
            "full_description": (
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                "Vivamus luctus urna sed urna ultricies ac tempor dui sagittis."
            ),
        }
        for i in range(num_results)
    ]


def send_email(
    to_address: str,
    subject: str,
    body: str,
    attachment_path: str | None = None,
):
    """Lightweight SMTP email sender."""
    server = os.getenv("SMTP_SERVER")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")

    if not all([server, port, user, password]):
        raise RuntimeError("Missing SMTP_* env vars")

    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(body)

    if attachment_path:
        with open(attachment_path, "rb") as f:
            data = f.read()
        msg.add_attachment(
            data,
            maintype="application",
            subtype="octet-stream",
            filename=os.path.basename(attachment_path),
        )

    with smtplib.SMTP(server, port) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)


def generate_cv(json_data: dict, output_path: str = "generated_cv.pdf") -> str:
    """Generate a very simple PDF from JSON profile data using fpdf2."""
    try:
        from fpdf import FPDF  # lazy import so users install only if needed
    except ImportError:
        raise RuntimeError("Install fpdf2: pip install fpdf2")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    text = json.dumps(json_data, indent=2)
    for line in text.split("\n"):
        pdf.multi_cell(0, 5, line)
    pdf.output(output_path)
    return output_path


def generate_interview_questions(
    profile: dict,
    job_description: str,
    n_questions: int = 8,
) -> List[str]:
    """Return a list of personalised interview questions.

    If `openai` is available **and** an `OPENAI_API_KEY` is set, call the OpenAI
    ChatCompletion endpoint. Otherwise return a deterministic stub so the UI
    keeps working offline.
    """
    if openai and os.getenv("OPENAI_API_KEY"):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        system_msg = (
            "You are an HR expert. Create concise, thought‑provoking interview "
            "questions tailored to the candidate's profile and the role.""")
        user_msg = (
            f"Candidate profile JSON:\n{json.dumps(profile)}\n\n"  # keep it short
            f"Job description:\n{job_description}\n\n"
            f"Return {n_questions} bullet points only."
        )
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
            temperature=0.7,
        )
        text = resp.choices[0].message.content.strip()
        # Split bullets – tolerant of either '\n-' or regular newlines
        questions = [q.strip("- •\n ") for q in text.split("\n") if q.strip()]
        return questions[:n_questions]
    else:
        # Offline fallback – generic starter list
        return [
            "Tell me about a challenging project you recently completed.",
            "How do you prioritise tasks when multiple deadlines collide?",
            "Describe a time you learned a new technology quickly.",
            "How do you stay current with developments in your field?",
            "Tell me about a mistake you made and what you learned from it.",
            "What excites you most about this role at our company?",
            "Describe how you handle feedback from peers or managers.",
            "What is your approach to collaborating with cross‑functional teams?",
        ][: n_questions]

################################################################################
# Streamlit UI
################################################################################

st.set_page_config(page_title="Job Application AI", page_icon="🧑‍💻", layout="wide")

st.title("🎯 Job Application AI Agent")

# Persistent session data
state = st.session_state
state.setdefault("job_results", [])
state.setdefault("cv_path", None)
state.setdefault("interview_questions", [])

# Sidebar for SMTP creds (optional)
with st.sidebar:
    st.header("🔧 Settings")
    smtp_user = st.text_input("SMTP user", os.getenv("SMTP_USER", ""))
    smtp_server = st.text_input("SMTP server", os.getenv("SMTP_SERVER", "smtp.gmail.com"))
    smtp_port = st.number_input("SMTP port", value=int(os.getenv("SMTP_PORT", "587")), step=1)
    smtp_pass = st.text_input("SMTP password", type="password", value=os.getenv("SMTP_PASSWORD", ""))
    if st.button("Save SMTP creds"):
        os.environ.update(
            {
                "SMTP_SERVER": smtp_server,
                "SMTP_PORT": str(smtp_port),
                "SMTP_USER": smtp_user,
                "SMTP_PASSWORD": smtp_pass,
            }
        )
        st.success("Saved for session.")

# MAIN TABS ====================================================================

jobs_tab, cv_tab, interview_tab, email_tab = st.tabs(
    ["🔍 Job Search", "📄 CV Generator", "🎤 Interview Prep", "📧 Send Email"]
)

# --- Job Search ---------------------------------------------------------------
with jobs_tab:
    st.subheader("Find relevant positions")
    keyword = st.text_input("Keyword", value="Data Scientist")
    num_results = st.slider("Results", 1, 20, 10, help="How many jobs to fetch")

    if st.button("Search Jobs"):
        with st.spinner("Crawling job boards …"):
            state.job_results = crawl_jobs(keyword, num_results)
        st.success(f"Fetched {len(state.job_results)} jobs!")

    if state.job_results:
        for idx, job in enumerate(state.job_results):
            with st.expander(f"{job['title']} – {job['company']} ({job['location']})"):
                st.write(job["snippet"])
                st.markdown(f"[View posting]({job['url']})")
                st.write("---")
                st.write(job["full_description"])

# --- CV Generator -------------------------------------------------------------
with cv_tab:
    st.subheader("Create a personalised CV")

    uploaded_json = st.file_uploader("Profile JSON", type="json")

    if uploaded_json:
        profile_data = json.load(uploaded_json)
        st.success("Loaded profile from file.")
    else:
        st.info("No JSON uploaded – fill in the form below.")
        profile_data = {
            "name": st.text_input("Name", "Jane Doe"),
            "title": st.text_input("Professional Title", "Software Engineer"),
            "summary": st.text_area("Professional Summary"),
            "skills": st.text_area("Key Skills (comma‑separated)").split(","),
            "experience": st.text_area("Experience (bullet list)"),
            "education": st.text_area("Education"),
        }

    if st.button("Generate CV PDF"):
        with st.spinner("Generating PDF …"):
            state.cv_path = generate_cv(profile_data)
        st.success("CV ready!")

    if state.cv_path:
        with open(state.cv_path, "rb") as f:
            st.download_button("Download CV", data=f.read(), file_name="cv.pdf", mime="application/pdf")

# --- Interview Prep -----------------------------------------------------------
with interview_tab:
    st.subheader("Interview Question Generator")
    st.write("Select a job from the search tab or paste a description.")

    job_options = {f"{i+1}. {j['title']} – {j['company']}": j for i, j in enumerate(state.job_results)}
    selected_label = st.selectbox("Use job posting", ["<None>"] + list(job_options.keys()))

    if selected_label != "<None>":
        jd_default = job_options[selected_label]["full_description"]
    else:
        jd_default = ""

    job_description = st.text_area("Job description", jd_default, height=150)

    # Re‑use profile_data from CV tab if available, else ask for quick summary
    quick_profile = {
        "name": profile_data.get("name", ""),
        "title": profile_data.get("title", ""),
        "skills": profile_data.get("skills", []),
    }

    if st.button("Generate Questions"):
        with st.spinner("Calling interview‑prep agent …"):
            state.interview_questions = generate_interview_questions(quick_profile, job_description)
        st.success("Questions ready!")

    if state.interview_questions:
        st.markdown("### Suggested Questions")
        for q in state.interview_questions:
            st.write(f"• {q}")
        st.caption("Tip: rehearse concise STAR‑format answers.")

# --- Email Sender -------------------------------------------------------------
with email_tab:
    st.subheader("Email the recruiter")

    to_address = st.text_input("To (email)")
    subject = st.text_input("Subject", "Regarding the {keyword} position")
    body = st.text_area("Message", value="Hello,\n\nI am excited to apply …\n\nBest regards,\n")
    attach_cv = st.checkbox("Attach generated CV", value=True)

    if st.button("Send Email"):
        if not to_address:
            st.error("Recipient email is required.")
        else:
            try:
                send_email(
                    to_address,
                    subject,
                    body,
                    attachment_path=state.cv_path if attach_cv else None,
                )
                st.success("Email sent!")
            except Exception as ex:
                st.error(f"Failed to send: {ex}")

################################################################################
# End of file – happy coding! 🎉
################################################################################
