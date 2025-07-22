import os
import json
import smtplib
from email.message import EmailMessage
from typing import List, Dict

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

import streamlit as st
import pandas as pd  # For data editor functionality
import requests
import base64

# Import local modules
from crawlers.jsearch_crawler import crawl_jsearch
from utils.webhook import send_to_webhook  # Use the new webhook utility

# Optional: only required if you want LLM‑generated interview questions or skill extraction
try:
    import openai  # type: ignore
except ImportError:
    openai = None  # graceful fallback if package not installed

################################################################################
# Helper functions – one per agent in your architecture diagram
################################################################################

# --- CV generation -----------------------------------------------------------
def generate_cv(json_data: dict, output_path: str = "generated_cv.pdf") -> str:
    """Very simple PDF generator using fpdf2.
    Replace with proper template rendering in production.
    """
    try:
        from fpdf import FPDF  # Lazy import
    except ImportError:
        raise RuntimeError("Install fpdf2: pip install fpdf2")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    # Title page --------------------------------------------------------------
    pdf.set_font_size(16)
    pdf.cell(0, 10, json_data.get("name", ""), ln=1)
    pdf.set_font_size(12)
    pdf.cell(0, 8, json_data.get("title", ""), ln=1)
    pdf.ln(4)

    # Summary -----------------------------------------------------------------
    pdf.multi_cell(0, 5, json_data.get("summary", ""))
    pdf.ln(3)

    # Skills ------------------------------------------------------------------
    pdf.set_font_size(14)
    pdf.cell(0, 8, "Skills", ln=1)
    pdf.set_font_size(12)
    pdf.multi_cell(0, 5, ", ".join(json_data.get("skills", [])))
    pdf.ln(3)

    # Experience - convert list to string if needed ---------------------------
    pdf.set_font_size(14)
    pdf.cell(0, 8, "Experience", ln=1)
    pdf.set_font_size(12)
    experience = json_data.get("experience", "")
    if isinstance(experience, list):
        experience_str = "\n".join([", ".join(str(val) for val in record.values()) 
                                    for record in experience if isinstance(record, dict)])
    else:
        experience_str = str(experience)
    pdf.multi_cell(0, 5, experience_str)
    pdf.ln(3)

    # Education - convert list to string if needed ----------------------------
    pdf.set_font_size(14)
    pdf.cell(0, 8, "Education", ln=1)
    pdf.set_font_size(12)
    education = json_data.get("education", "")
    if isinstance(education, list):
        education_str = "\n".join([", ".join(str(val) for val in record.values()) 
                                   for record in education if isinstance(record, dict)])
    else:
        education_str = str(education)
    pdf.multi_cell(0, 5, education_str)

    # Job‑specific section ----------------------------------------------------
    job_desc = json_data.get("job_description", "")
    if job_desc:
        # Replace unsupported bullet characters "•" with a supported alternative
        job_desc = job_desc.replace("•", "- ")
        pdf.ln(4)
        pdf.set_font_size(14)
        pdf.cell(0, 8, "Target Job Highlights", ln=1)
        pdf.set_font_size(12)
        pdf.multi_cell(0, 5, job_desc)

    pdf.output(output_path)
    return output_path

# --- Skill extraction from job description -----------------------------------
COMMON_SKILLS = [
    "python",
    "java",
    "javascript",
    "sql",
    "aws",
    "azure",
    "gcp",
    "kubernetes",
    "docker",
    "ci/cd",
    "git",
    "linux",
    "machine learning",
    "data analysis",
    "agile",
]

def extract_skills_from_description(description: str) -> List[str]:
    """Very naive keyword matcher; upgrade to NLP or LLM for better accuracy."""
    desc_lower = description.lower()
    return [kw.capitalize() if kw.islower() else kw for kw in COMMON_SKILLS if kw in desc_lower]

# --- Interview‑question generation ------------------------------------------
def generate_interview_questions(
    profile: dict,
    job_description: str,
    n_questions: int = 8,
) -> List[str]:
    if openai and os.getenv("OPENAI_API_KEY"):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        system_msg = ("You are an HR expert. Create concise, thought‑provoking interview questions "
                      "tailored to the candidate's profile and the role.")
        user_msg = (
            f"Candidate profile JSON:\n{json.dumps(profile)}\n\n"
            f"Job description:\n{job_description}\n\n"
            f"Return {n_questions} bullet points only."
        )
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
        )
        text = resp.choices[0].message.content.strip()
        return [q.strip("- •\n ") for q in text.split("\n") if q.strip()][:n_questions]

    # Fallback list -----------------------------------------------------------
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
# PDF Preview Helper
################################################################################
def preview_pdf(pdf_bytes):
    """Display a PDF preview in Streamlit."""
    try:
        st.pdf(pdf_bytes)
    except Exception:
        b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        pdf_display = (
            f'<iframe src="data:application/pdf;base64,{b64_pdf}" '
            'width="700" height="1000" type="application/pdf"></iframe>'
        )
        st.markdown(pdf_display, unsafe_allow_html=True)

################################################################################
# Streamlit UI
################################################################################
st.set_page_config(page_title="Job Application AI", page_icon="🧑‍💻", layout="wide")
st.title("🎯 Job Application AI Agent")

# -----------------------------------------------------------------------------
# Session defaults
# -----------------------------------------------------------------------------
state = st.session_state
state.setdefault("profile", {})
state.setdefault("job_params", {})
state.setdefault("job_results", [])
state.setdefault("cv_path", None)
state.setdefault("interview_questions", [])

# -----------------------------------------------------------------------------
# Personal info & search parameters form
# -----------------------------------------------------------------------------
with st.form("personal_info_form", clear_on_submit=False):
    st.subheader("✨ Personal Information & Job Preferences")
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Name", state.get("profile", {}).get("name", "Jane Doe"))
        title = st.text_input("Professional Title", state.get("profile", {}).get("title", "Software Engineer"))
        summary = st.text_area("Professional Summary", state.get("profile", {}).get("summary", ""))
    with c2:
        skills = st.text_input("Key Skills (comma‑separated)", "Python, SQL, JavaScript")
    st.markdown("#### 🧳 Experience")
    exp_df_form = st.data_editor(
        pd.DataFrame(state.get("profile", {}).get("experience", [{
            "Company": "", "Position": "", "Location": "", "Begin Date": "", "End Date": ""
        }])),
        num_rows="dynamic",
        key="exp_items_form"
    )
    st.markdown("#### 🎓 Education")
    edu_df_form = st.data_editor(
        pd.DataFrame(state.get("profile", {}).get("education", [{
            "Institution": "", "Area of Study": "", "Location": "", "Begin Date": "", "End Date": ""
        }])),
        num_rows="dynamic",
        key="edu_items_form"
    )
    if st.form_submit_button("Save & Continue ➡️"):
        state["profile"] = {
            "name": name,
            "title": title,
            "summary": summary,
            "skills": [s.strip() for s in skills.split(",") if s.strip()],
            "experience": exp_df_form.to_dict("records"),
            "education": edu_df_form.to_dict("records"),
        }
        st.success("Saved! Now explore the tabs.")

# -----------------------------------------------------------------------------
# Tabs
# -----------------------------------------------------------------------------
jobs_tab, cv_tab, interview_tab, email_tab = st.tabs(
    ["🔍 Job Search", "📄 CV Generator", "🎤 Interview Prep", "📧 Generate Email"]
)

# --- 🔍 Job Search -----------------------------------------------------------
with jobs_tab:
    st.subheader("Find relevant positions (powered by the JSearch API)")
    st.info("Example search: 'developer jobs in bonn'")
    if not state.get("profile"):
        st.info("Please fill in the **Personal Information** form first.")
    else:
        default_keyword = state["profile"].get("title", "developer jobs")
        keyword_input = st.text_input("Keyword", value=state.get("job_params", {}).get("keyword", default_keyword), key="job_keyword_input")
        location_input = st.text_input("Location", value=state.get("job_params", {}).get("location", ""), key="job_location_input")
        country_input = st.selectbox("Country", ["US", "UK", "DE", "FR"], 
                                     index=["US", "UK", "DE", "FR"].index(state.get("job_params", {}).get("country", "DE")),
                                     key="job_country_input")
        work_from_home_input = st.checkbox("Work From Home Only", value=state.get("job_params", {}).get("work_from_home", False), key="job_wfh_input")
        platform_input = st.selectbox("Preferred Platform", ["LinkedIn", "Indeed", "Xing"],
                                      index=["LinkedIn", "Indeed", "Xing"].index(state.get("job_params", {}).get("platform", "LinkedIn")),
                                      key="job_platform_input")
        state["job_params"].update({
            "keyword": keyword_input,
            "location": location_input,
            "country": country_input,
            "work_from_home": work_from_home_input,
            "platform": platform_input
        })
        num_results = st.slider("Number of results", 1, 10, 5)
        if st.button("Search Jobs"):
            with st.spinner("Fetching jobs using JSearch API ..."):
                job_results = crawl_jsearch(keyword_input, location_input, num_results, 
                                            country=country_input, work_from_home=work_from_home_input, 
                                            job_platform=platform_input)
                # Ensure only the desired number of results are kept
                job_results = job_results[:num_results]
                for job in job_results:
                    job.setdefault("snippet", "No snippet available.")
                    job.setdefault("full_description", "No description available.")
                state["job_results"] = job_results
            st.success(f"Fetched {len(state['job_results'])} jobs for *{keyword_input}* in *{location_input}* ({country_input}) [WfH: {work_from_home_input}], Preferred Platform: {platform_input}.")

    if state.get("job_results"):
        for job in state["job_results"]:
            with st.expander(f"{job['title']} – {job['company']} ({job['location']})"):
                st.write(job["snippet"])
                st.markdown(f"[View posting]({job['url']})")
                st.write("---")
                st.write(job["full_description"])

# --- 📄 CV Generator ---------------------------------------------------------
with cv_tab:
    st.subheader("Create a personalised CV (auto‑merging job & profile data)")
    if not state.get("profile"):
        st.info("Fill in the **Personal Information** form first.")
    elif not state.get("job_results"):
        st.info("Run a job search so we have postings to tailor the CV.")
    else:
        dropdown_options = {
            "<None>": "",
            **{f"{i+1}. {j['title']} – {j['company']}": j["full_description"] for i, j in enumerate(state["job_results"])}
        }
        selected_label = st.selectbox("Select a job to tailor your CV", list(dropdown_options.keys()))
        selected_desc = dropdown_options[selected_label]

        # Merge profile skills with those extracted from job description
        profile_data = state["profile"].copy()
        job_skills = extract_skills_from_description(selected_desc) if selected_desc else []
        combined_skills = sorted({*(profile_data.get("skills", [])), *job_skills}, key=str.lower)
        profile_data["skills"] = combined_skills
        profile_data["job_description"] = selected_desc

        if st.button("Generate CV PDF"):
            with st.spinner("Generating personalised CV …"):
                state["cv_path"] = generate_cv(profile_data)
            st.success("Personalised CV ready!")

        if state.get("cv_path"):
            with open(state["cv_path"], "rb") as f:
                pdf_bytes = f.read()
            with st.expander("Preview Generated CV", expanded=True):
                preview_pdf(pdf_bytes)
            st.download_button("Download CV", data=pdf_bytes, file_name="cv.pdf", mime="application/pdf")

        # Send full personal and job data to webhook for CV processing.
        if st.button("Send CV Request to Webhook"):
            cv_payload = {
                "action": "cv_generation",
                "personal_details": state["profile"],
                "job_listings": state["job_results"],
                "cv_data": profile_data
            }
            if send_to_webhook(cv_payload):
                st.success("CV request sent to webhook!")

# --- 🎤 Interview Prep -------------------------------------------------------
with interview_tab:
    st.subheader("Interview Question Generator")
    if not state.get("job_results"):
        st.info("Run a job search first so we have a description to analyse.")
    else:
        job_options = {f"{i+1}. {j['title']} – {j['company']}": j for i, j in enumerate(state["job_results"])}
        selected_job = st.selectbox("Choose a job posting", list(job_options.keys()))
        jd_default = job_options[selected_job]["full_description"]
        job_description = st.text_area("Job description", jd_default, height=150)
        quick_profile = {
            "name": state["profile"].get("name", ""),
            "title": state["profile"].get("title", ""),
            "skills": state["profile"].get("skills", []),
        }
        if st.button("Generate Questions"):
            with st.spinner("Calling interview‑prep agent …"):
                state["interview_questions"] = generate_interview_questions(quick_profile, job_description)
            st.success("Questions ready!")
        if state.get("interview_questions"):
            st.markdown("### Suggested Questions")
            for q in state["interview_questions"]:
                st.write(f"• {q}")
            st.caption("Tip: rehearse concise STAR‑format answers.")
            if st.button("Send Interview Request to Webhook"):
                interview_payload = {
                    "action": "interview_prep",
                    "personal_details": state["profile"],
                    "job_listings": state["job_results"],
                    "interview_questions": state["interview_questions"]
                }
                if send_to_webhook(interview_payload):
                    st.success("Interview request sent to webhook!")

# --- 📧 Email Text Generator --------------------------------------------------
with email_tab:
    st.subheader("Generate Email Text")
    job_options = {"<None>": None}
    if state.get("job_results"):
        for i, job in enumerate(state["job_results"]):
            label = f"{i+1}. {job['title']} – {job['company']}"
            job_options[label] = job
    selected_job_label = st.selectbox("Select a job listing to reference", list(job_options.keys()))
    selected_job = job_options[selected_job_label]
    if selected_job:
        default_subject = f"Regarding the {selected_job['title']} position at {selected_job['company']}"
    else:
        default_subject = f"Regarding the {state.get('job_params', {}).get('keyword', '')} position"
    subject = st.text_input("Subject", default_subject)
    body = st.text_area("Message", value="Hello,\n\nI am excited to apply …\n\nBest regards,\n")
    full_email_text = f"Subject: {subject}\n\n{body}"
    st.markdown("### Generated Email Text")
    st.code(full_email_text, language="markdown")
    if st.button("Send Email Request to Webhook"):
        email_payload = {
            "action": "email_generation",
            "personal_details": state["profile"],
            "job_listings": state["job_results"],
            "email_subject": subject,
            "email_body": body
        }
        if send_to_webhook(email_payload):
            st.success("Email request sent to webhook!")
