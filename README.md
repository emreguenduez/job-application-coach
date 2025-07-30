# 💼 Job Application coach

An intelligent assistant to streamline and automate the job application process using a modern full-stack approach combining web crawling, data pipelines, and AI agents.

---

## ✨ Features

* **Job Discovery**: Search and retrieve job listings from most popular employment websites (e.g., LinkedIn).
* **Streamlit UI**: Interactive dashboard to explore jobs, trigger application flows, and monitor progress.
* **Automated CV/Email Generation**: Leverages **OpenAI agents** to tailor CVs, cover letters, and emails to job descriptions.
* **Interview Preparation**: Generates personalized interview questions and answers using LLMs.
* **n8n Backend Workflows**: Orchestrates tasks like email drafting, file generation, and storage.
* **Modular Crawler**: Easily extendable architecture to plug in more job portals.
* **Local and Remote Execution**: Backend workflows can run on `n8n.cloud` or locally via Docker.

---

## 🛠️ Tech Stack

| Layer          | Tools/Frameworks                                         |
| -------------- | -------------------------------------------------------- |
| **Frontend**   | Streamlit                                                |
| **API**        | jSearch API                                              |
| **Backend**    | n8n, Python (Flask/REST)                                 |
| **Database**   | MongoDB                         |                        |
| **AI**         | OpenAI GPT (Agents via n8n HTTP modules)                 |

---

## 📁 Project Structure

```bash
JOB-APPLICATION-COACH/
├── crawlers/
│   ├── .env                  # Environment variables for crawler
│   └── jsearch_crawler.py    # jsearch API
├── utils/
│   └── webhook.py            # Webhook utilities and handlers
├── .gitignore               # Git ignore rules
├── LICENSE                 # Project license
├── n8n_json.json          # n8n workflow configuration
├── README.md              # Project documentation
├── requirements.txt       # Python dependencies
└── streamlit-app.py       # Main Streamlit application
```

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/emreguenduez/job-application-coach.git
cd job-application-coach
```

### 2. Create a virtual environment and activate it
```bash
python -m venv venv
source venv/bin/activate

```
### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the crawlers folder and add RAPIDAPI_KEY key to it. The value for this API key is provided in report.

### 5. Run Streamlit UI

```bash
streamlit run streamlit-app.py
```

### 6. Download and Run n8n Locally

In n8n editor choose Import from file and then select n8n_Json.json file; this is the n8n workflow. 

### 7. Import the OpenAPI Credentials:

Copy and paste the provided OpenAI API key from the report. In n8n editor and inside the credentials section, enter the OpenAI API key and save it. Go to workflow and select this credential for each of the 3 agents and then activate the workflow.


## 📡 How It Works

1. **Users enter their data into app** this is the data we need to feed models for downstream tasks.
2. Our crawler sends extracted data about jobs to **n8n backend**.
3. **n8n calls OpenAI agents** to:

   * Generate a personalized CV, email, and interview Q\&A
4. Our interactive UI displays jobs, email draft, interview questions, and CV.

---

## 🧠 AI Agent Capabilities

* **Resume Optimization**: Tailors resume to specific job keywords.
* **Email Drafting**: Generates formal emails in for applications in English.
* **Interview Simulation**: Uses job description to create mock interview Q\&A.

---

## 👤 Creators

* **EMRULLAH DAGKUSU**
* **AMIR KAZEMZADEH MOGHANJOUGHI**
* **OSMAN DOGUKAN URKAN**
* **MUSTAFA EMRE GUNDUZ**
