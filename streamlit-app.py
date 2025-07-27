import base64
import os
import json
import smtplib
from email.message import EmailMessage
from typing import List, Dict

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

import streamlit as st
import pandas as pd  # for data editor functionality
from utils.webhook import send_to_webhook  # new webhook utility
from crawlers.jsearch_crawler import crawl_jsearch

import requests  # for HTTP requests

# Optional: if using LLM-powered functions
try:
    import openai  # type: ignore
except ImportError:
    openai = None

################################################################################
# Helper functions – CV generation, skill extraction and interview question generation
################################################################################

def generate_cv(json_data: dict, output_path: str = "generated_cv.pdf") -> str:
    try:
        from fpdf import FPDF  # Lazy import
    except ImportError:
        raise RuntimeError("Install fpdf2: pip install fpdf2")
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    # Title
    pdf.set_font_size(16)
    pdf.cell(0, 10, json_data.get("name", ""), ln=1)
    pdf.set_font_size(12)
    pdf.cell(0, 8, json_data.get("title", ""), ln=1)
    pdf.ln(4)
    # Summary
    pdf.multi_cell(0, 5, json_data.get("summary", ""))
    pdf.ln(3)
    # Skills
    pdf.set_font_size(14)
    pdf.cell(0, 8, "Skills", ln=1)
    pdf.set_font_size(12)
    pdf.multi_cell(0, 5, ", ".join(json_data.get("skills", [])))
    pdf.ln(3)
    # Experience
    pdf.set_font_size(14)
    pdf.cell(0, 8, "Experience", ln=1)
    pdf.set_font_size(12)
    experience = json_data.get("experience", "")
    if isinstance(experience, list):
        experience_str = "\n".join([", ".join(str(val) for val in record.values()) for record in experience if isinstance(record, dict)])
    else:
        experience_str = str(experience)
    pdf.multi_cell(0, 5, experience_str)
    pdf.ln(3)
    # Education
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
    # Job-specific section
    job_desc = json_data.get("job_description", "")
    if job_desc:
        job_desc = job_desc.replace("•", "- ")
        pdf.ln(4)
        pdf.set_font_size(14)
        pdf.cell(0, 8, "Target Job Highlights", ln=1)
        pdf.set_font_size(12)
        pdf.multi_cell(0, 5, job_desc)
    pdf.output(output_path)
    return output_path

COMMON_SKILLS = [
    "python", "java", "javascript", "sql", "aws", "azure", "gcp",
    "kubernetes", "docker", "ci/cd", "git", "linux", "machine learning",
    "data analysis", "agile",
]

def extract_skills_from_description(description: str) -> List[str]:
    desc_lower = description.lower()
    return [kw.capitalize() if kw.islower() else kw for kw in COMMON_SKILLS if kw in desc_lower]

def generate_interview_questions(profile: dict, job_description: str, n_questions: int = 8) -> List[str]:
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
            messages=[{"role": "system", "content": system_msg},
                      {"role": "user", "content": user_msg}],
            temperature=0.7,
        )
        text = resp.choices[0].message.content.strip()
        return [q.strip("- •\n ") for q in text.split("\n") if q.strip()][:n_questions]
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

# --- Session defaults ---
state = st.session_state
state.setdefault("profile", {})
state.setdefault("job_params", {})
state.setdefault("job_results", [])
state.setdefault("cv_path", None)
state.setdefault("interview_questions", [])

# --- Personal info & search form ---
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
    exp_df_form = st.data_editor(pd.DataFrame(state.get("profile", {}).get("experience", [{
        "Company": "", "Position": "", "Location": "", "Begin Date": "", "End Date": ""
    }])), num_rows="dynamic", key="exp_items_form")
    st.markdown("#### 🎓 Education")
    edu_df_form = st.data_editor(pd.DataFrame(state.get("profile", {}).get("education", [{
        "Institution": "", "Area of Study": "", "Location": "", "Begin Date": "", "End Date": ""
    }])), num_rows="dynamic", key="edu_items_form")
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

# --- Tabs ---
jobs_tab, cv_tab, interview_tab, email_tab = st.tabs([
    "🔍 Job Search", "📄 CV Generator", "🎤 Interview Prep", "📧 Generate Email"
])

# --- Job Search Tab ---
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
                job_results = crawl_jsearch(keyword_input, location_input, num_results, country=country_input, work_from_home=work_from_home_input, job_platform=platform_input)
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

# --- CV Generator Tab ---
with cv_tab:
    st.subheader("Create a personalised CV (auto‑merging job & profile data)")
    if not state.get("profile"):
        st.info("Fill in the **Personal Information** form first.")
    elif not state.get("job_results"):
        st.info("Run a job search so we have postings to tailor the CV.")
    else:
        dropdown_options = {"<None>": ""}
        dropdown_options.update({
            f"{i+1}. {j['title']} – {j['company']}": j["full_description"]
            for i, j in enumerate(state["job_results"])
        })
        selected_label = st.selectbox("Select a job to tailor your CV", list(dropdown_options.keys()))
        selected_desc = dropdown_options[selected_label]
        profile_data = state["profile"].copy()
        job_skills = extract_skills_from_description(selected_desc) if selected_desc else []
        combined_skills = sorted({*(profile_data.get("skills", [])), *job_skills}, key=str.lower)
        profile_data["skills"] = combined_skills
        profile_data["job_description"] = selected_desc
        
        if st.button("Generate CV PDF"):
            with st.spinner("Sending request to CV agent..."):
                # Build the unified payload from personal details and job listings.
                unified_payload = {
                    "personal_details": state["profile"],
                    "job_listings": state.get("job_results", [])
                }
                # Send the payload to the webhook and expect generated CV data in response.
                result = send_to_webhook(unified_payload)
                if result.get("cover_letters"):
                    # örnek olarak ilk mektubu alıyoruz
                    first_letter = next(iter(result["cover_letters"].values()))
                    profile_data["job_description"] = first_letter
                    state["cv_path"] = generate_cv(profile_data)
                else:
                    st.error("Failed to receive generated CV data from webhook.")
        if state.get("cv_path"):
            with open(state["cv_path"], "rb") as f:
                st.download_button("Download CV", data=f.read(), file_name="cv.pdf", mime="application/pdf")


# --- Interview Prep Tab ---
with interview_tab:
    st.subheader("Interview Question Generator")
    
    if not state.get("job_results"):
        st.info("Run a job search first so we have a description to analyse.")
    else:
        # Job seçenekleri oluştur
        job_options = {f"{i+1}. {j['title']} – {j['company']}": j for i, j in enumerate(state["job_results"])}
        selected_job = st.selectbox("Choose a job posting", list(job_options.keys()))
        jd_default = job_options[selected_job]["full_description"]

        # Dinamik yükseklik: 20 karakter/satır, 5 piksel/satır
        estimated_lines = max(len(jd_default) // 100, 10)
        text_area_height = estimated_lines * 20  # örn. 20 piksel/satır

        job_description = st.text_area("Job description", jd_default, height=text_area_height)

        quick_profile = {
            "name": state["profile"].get("name", ""),
            "title": state["profile"].get("title", ""),
            "skills": state["profile"].get("skills", []),
        }


        # Tüm joblar için webhook'a gönder
        if st.button("Generate Interview Questions For Selected Job"):
            unified_payload = {
                "action": "question",  # 👈 yeni alan
                "personal_details": state["profile"],
                "job_listings": state.get("job_results", [])
            }

            result = send_to_webhook(unified_payload)

            # Normalize: Eğer liste geldiyse içinden al
            result_dict = result[0] if isinstance(result, list) and result else result

            # Başlık eşlemesi için liste oluştur
            job_titles = [f"{job['title']} – {job['company']}" for job in state["job_results"]]

            if result_dict:
                st.success("Interview questions received!")
                for i, (job_key, job_data) in enumerate(result_dict.items()):
                    # Eşleşen başlıkla göster (ya da fallback)
                    title = job_titles[i] if i < len(job_titles) else job_key
                    questions = job_data.get("interview_questions", [])

                    if questions:
                        st.markdown(f"### {title}")
                        for j, qa in enumerate(questions, 1):
                            q = qa.get("question", "").strip()
                            a = qa.get("answer", "").strip()
                            if q:
                                st.markdown(f"**Q{j}: {q}**")
                                if a:
                                    st.markdown(f"**A{j}: {a}**")
                    else:
                        st.warning(f"No questions found for {title}")

                state["interview_questions"] = result_dict
            else:
                st.error("No interview questions received from webhook.")



# --- Email Text Generator Tab ---
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

    if st.button("Send Email Request to Webhook"):
        unified_payload = {
            "action": "email",  
            "selected_job": selected_job,
            "personal_details": state["profile"],
            #"job_listings": state.get("job_results", []),
            
        }
        result = send_to_webhook(unified_payload)

        # Normalize webhook result (handle both dict and list)
        result_dict = result[0] if isinstance(result, list) and result else result

        if result_dict.get("email_draft", {}).get("draft"):
            draft_text = result_dict["email_draft"]["draft"]
            job_title = f"{selected_job['title']} – {selected_job['company']}"
            
            subject = f"Regarding the {selected_job['title']} position at {selected_job['company']}"
            
            # Satır boşluklarını düzelt
            formatted_text = draft_text.replace("\\n", "\n")

            # Yüksekliği ayarla
            lines = max(formatted_text.count("\n") + 5, 12)
            height = lines * 20

            # Konu ayrı göster
            st.markdown(f"**Subject:** `{subject}`")

            # Taslak mail metni
            st.text_area("Email Preview", formatted_text, height=height, key="email_preview")



        else:
            st.warning("Email draft not returned by webhook. (This is normal if email step is disabled.)")





