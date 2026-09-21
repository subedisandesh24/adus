import streamlit as st
from groq import Groq
from PIL import Image
from fpdf import FPDF
import json
import base64
import io
import os
import urllib.request
import unicodedata

# -------------------------------------------------------------------------
# 1. Calibri Font Manager (Works locally & on Streamlit Cloud)
# -------------------------------------------------------------------------
@st.cache_resource
def setup_calibri_fonts():
    """
    Finds native Calibri on Windows or downloads Carlito (Google's metric-identical
    open-source Calibri twin) for Streamlit Cloud/Linux.
    """
    # 1. Check Windows native fonts
    win_dir = "C:\\Windows\\Fonts"
    win_reg = os.path.join(win_dir, "calibri.ttf")
    win_bold = os.path.join(win_dir, "calibrib.ttf")
    win_ital = os.path.join(win_dir, "calibrii.ttf")
    if os.path.exists(win_reg) and os.path.exists(win_bold) and os.path.exists(win_ital):
        return "Calibri", {"": win_reg, "B": win_bold, "I": win_ital}

    # 2. Check local repo folder for calibri.ttf
    if os.path.exists("calibri.ttf") and os.path.exists("calibrib.ttf") and os.path.exists("calibrii.ttf"):
        return "Calibri", {"": "calibri.ttf", "B": "calibrib.ttf", "I": "calibrii.ttf"}

    # 3. Download metric-compatible Carlito (Calibri equivalent) on Linux / Cloud
    carlito_urls = {
        "": "https://raw.githubusercontent.com/google/fonts/main/ofl/carlito/Carlito-Regular.ttf",
        "B": "https://raw.githubusercontent.com/google/fonts/main/ofl/carlito/Carlito-Bold.ttf",
        "I": "https://raw.githubusercontent.com/google/fonts/main/ofl/carlito/Carlito-Italic.ttf"
    }
    local_files = {"": "calibri_reg.ttf", "B": "calibri_bold.ttf", "I": "calibri_ital.ttf"}

    try:
        for style, url in carlito_urls.items():
            dest = local_files[style]
            if not os.path.exists(dest):
                urllib.request.urlretrieve(url, dest)
        return "Calibri", local_files
    except Exception:
        # Fallback to standard PDF sans-serif if offline
        return "Helvetica", None


# -------------------------------------------------------------------------
# 2. Clean Text Function (Preserves Bold/Italic Asterisks & ASCII)
# -------------------------------------------------------------------------
def clean_text(val):
    """Safely converts unicode to clean ASCII, stripping characters that turn into '???'"""
    if val is None:
        return ""
    if isinstance(val, list):
        val = ", ".join(str(item) for item in val if item is not None)
    elif not isinstance(val, str):
        val = str(val)

    replacements = {
        "’": "'", "‘": "'", "“": '"', "”": '"', "`": "'",
        "–": "-", "—": "-", "―": "-", "…": "...",
        "•": "-", "▪": "-", "►": "-", "·": "-", "★": "*",
        "✓": "[x]", "✔": "[x]", "✔️": "[x]",
        "\u00a0": " ", "\u200b": "", "\u2003": " ", "\t": "    "
    }
    for k, v in replacements.items():
        val = val.replace(k, v)

    val = unicodedata.normalize('NFKD', val).encode('ascii', 'ignore').decode('ascii')
    return val.strip()


# -------------------------------------------------------------------------
# 3. PDF Builder (Calibri Typography + Eye-Catching Bold/Italics)
# -------------------------------------------------------------------------
class CompleteCVPDF(FPDF):
    def __init__(self, doc_type="CV"):
        super().__init__(format="A4", unit="mm")
        self.doc_type = doc_type
        self.set_margins(16, 14, 16)
        self.set_auto_page_break(auto=True, margin=15)

        # Register Calibri or fallback to Helvetica
        self.font_family, font_paths = setup_calibri_fonts()
        if font_paths:
            for style, path in font_paths.items():
                self.add_font("Calibri", style=style, fname=path)

    @property
    def printable_width(self):
        return self.w - self.l_margin - self.r_margin

    def draw_cv_header(self):
        """Header matching Sudha's CV with blue LinkedIn hyperlink"""
        self.set_y(14)
        self.set_x(self.l_margin)
        
        # Name on Left
        self.set_font(self.font_family, "B", 18)
        self.set_text_color(20, 20, 20)
        self.cell(90, 10, "SUDHA PANTHI", align="L")
        
        # Contact Details on Right
        contact_x = self.w - self.r_margin - 88
        self.set_font(self.font_family, "", 9)
        
        # Phone
        self.set_xy(contact_x, 14)
        self.set_text_color(60, 60, 60)
        self.cell(88, 3.8, "+977-9860906707", align="R", new_x="LMARGIN", new_y="NEXT")
        
        # Email
        self.set_x(contact_x)
        self.cell(88, 3.8, "Sudha.panthee@gmail.com", align="R", new_x="LMARGIN", new_y="NEXT")
        
        # LinkedIn with Blue Hyperlink
        self.set_x(contact_x)
        self.set_text_color(0, 80, 200)
        self.cell(
            88, 3.8, "linkedin.com/in/sudha-panthi-10aa801b0", 
            align="R", 
            link="https://www.linkedin.com/in/sudha-panthi-10aa801b0", 
            new_x="LMARGIN", 
            new_y="NEXT"
        )
        self.set_text_color(20, 20, 20)
        self.ln(3)

    def draw_section_heading(self, title):
        """Heading with horizontal divider line"""
        avail_w = self.printable_width
        self.ln(2)
        self.set_x(self.l_margin)
        self.set_font(self.font_family, "B", 11.5)
        self.set_text_color(15, 15, 15)
        self.cell(avail_w, 5, clean_text(title), new_x="LMARGIN", new_y="NEXT")
        
        curr_y = self.get_y()
        self.set_draw_color(40, 40, 40)
        self.set_line_width(0.35)
        self.line(self.l_margin, curr_y, self.w - self.r_margin, curr_y)
        self.ln(2.5)

    def draw_org_block(self, org_name, location, role_title, dates, bullets):
        """Organization Block with bolded keywords and italic role"""
        avail_w = self.printable_width
        col_left = 115
        col_right = avail_w - col_left

        self.set_x(self.l_margin)
        self.set_font(self.font_family, "B", 10.2)
        self.set_text_color(20, 20, 20)
        self.cell(col_left, 4.5, clean_text(org_name), align="L")
        self.set_font(self.font_family, "", 9)
        self.cell(col_right, 4.5, clean_text(location), align="R", new_x="LMARGIN", new_y="NEXT")

        self.set_x(self.l_margin)
        self.set_font(self.font_family, "I", 9.2)
        self.cell(col_left, 4.2, clean_text(role_title), align="L")
        self.set_font(self.font_family, "", 9)
        self.cell(col_right, 4.2, clean_text(dates), align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(0.8)

        # Bullets with Markdown support (Bold/Italic)
        self.set_font(self.font_family, "", 9)
        self.set_text_color(35, 35, 35)
        for bullet in bullets:
            self.set_x(self.l_margin)
            self.multi_cell(avail_w, 4.3, f"-  {clean_text(bullet)}", markdown=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(1.5)

    def draw_two_col_entry(self, left_bold, left_sub, right_txt, right_sub=""):
        """Two-column layout"""
        avail_w = self.printable_width
        col_left = 118
        col_right = avail_w - col_left

        self.set_x(self.l_margin)
        self.set_font(self.font_family, "B", 9.2)
        self.set_text_color(20, 20, 20)
        self.cell(col_left, 4.2, clean_text(left_bold), align="L")
        self.set_font(self.font_family, "", 9)
        self.cell(col_right, 4.2, clean_text(right_txt), align="R", new_x="LMARGIN", new_y="NEXT")

        if left_sub or right_sub:
            self.set_x(self.l_margin)
            self.set_font(self.font_family, "", 8.8)
            self.set_text_color(50, 50, 50)
            self.cell(col_left, 4.0, clean_text(left_sub), align="L")
            self.cell(col_right, 4.0, clean_text(right_sub), align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def footer(self):
        """Page Footer"""
        self.set_y(-12)
        self.set_x(self.l_margin)
        self.set_font(self.font_family, "", 8.5)
        self.set_text_color(90, 90, 90)
        avail_w = self.printable_width
        self.cell(avail_w / 2, 8, "Sudha Panthi - Phone: +977-9860906707 | Email: Sudha.panthee@gmail.com", align="L")
        self.cell(avail_w / 2, 8, f"{self.page_no()} | P a g e", align="R")


# -------------------------------------------------------------------------
# 4. Dynamic Model Selector
# -------------------------------------------------------------------------
def get_groq_active_models(client):
    try:
        available_models = [m.id for m in client.models.list().data]
        preferred_text = [
            "openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b",
            "llama-3.3-70b-versatile", "llama-3.1-8b-instant"
        ]
        text_model = next((m for m in preferred_text if m in available_models), None)
        if not text_model:
            text_model = available_models[0] if available_models else "openai/gpt-oss-120b"
            
        preferred_vision = [
            "llama-3.2-11b-vision-preview", "llama-3.2-90b-vision-preview", "qwen/qwen3.8-27b"
        ]
        vision_model = next((m for m in preferred_vision if m in available_models), text_model)
        return text_model, vision_model
    except Exception:
        return "openai/gpt-oss-120b", "llama-3.2-11b-vision-preview"


# -------------------------------------------------------------------------
# 5. Permanent CV Database (With Exact DOI & Bhimsen's Phone)
# -------------------------------------------------------------------------
PERMANENT_CV_SECTIONS = {
    "publication_text": "Impact of Farmers' Marketing Decisions on Profitability in Wheat: A Case Study of Kailali District - American Journal of Applied Statistics and Economics. ",
    "publication_doi": "https://doi.org/10.54536/ajase.v5i2.6848",
    "projects": [
        "Impact of Sowing Date and Seed Rate in Wheat Yield Performance",
        "Case Study on Agribusiness management and financing of a firm",
        "Mushroom Cultivation and disease identification",
        "Case Study on Agroforestry Model of a Community",
        "Design on Annual Vegetable Production Crop Calendar and Budget Estimation",
        "Effect of Using Single Strain and Multiple Strain Probiotics in COBB 500 Broilers"
    ],
    "education": [
        {"inst": "Tribhuvan University, Institute of Agriculture and Animal Science", "deg": "Masters of Science in Agriculture", "loc": "Kathmandu, Nepal", "yr": "2025-Present"},
        {"inst": "Tribhuvan University, Institute of Agriculture and Animal Science", "deg": "Bachelors of Science in Agriculture - Percentage: 75.38% (IDF Scholarship)", "loc": "Lamjung, Nepal", "yr": "2020-2024"},
        {"inst": "St. Xavier's College", "deg": "High School - GPA: 3.22", "loc": "Maitighar, Kathmandu", "yr": "2016-2018"},
        {"inst": "SOS Hermann Gmeiner School", "deg": "Higher Secondary - GPA: 3.8", "loc": "Sanothimi, Bhaktapur", "yr": "2016"}
    ],
    "leadership": [
        {
            "org": "Technical Students' Association of Nepal, Lamjung Campus",
            "loc": "Lamjung, Nepal",
            "roles": [
                ("President (2023-2024)", "Organised technical boot-camps on MS & Adobe packages, public speaking, teamwork, Chief Trainer."),
                ("Secretary (2022-2023)", "Conducted association programs and meetings; coordinated with partner organizations."),
                ("Deputy-Secretary (2021-2022)", "Handled minute record writing, documentation, and social media communication.")
            ]
        },
        {
            "org": "SOS'ian Social Service Club",
            "loc": "Bhaktapur, Nepal",
            "roles": [
                ("Secretary (2015-2016)", "Conducted meetings, plogging, awareness on social issues, earthquake relief fund & rural library setup.")
            ]
        }
    ],
    "trainings": [
        ("Climate Change Course, 2024", "Power Shift Nepal"),
        ("Exhibitor at Future Smart Crop Exhibition, 2024", "Food and Agriculture Organization"),
        ("Exhibitor at 5th Nepal Agritech International Expo, 2023", "Media Space Solutions Pvt. Ltd"),
        ("Model Youth Parliament, 2023", "Tony Hagen Foundation Nepal"),
        ("Training of Trainers, 2023", "Youth for Community Transformation"),
        ("Arc GIS Training, 2023", "CARITAS Nepal"),
        ("Farmers Field School", "Technical Students' Association of Nepal"),
        ("Data and Analytics Session on R Studio, 2022", "Technical Students' Association of Nepal"),
        ("Technical Bootcamp, 2021", "Technical Students' Association of Nepal"),
        ("Five days Women's Self Defence Training, 2021", "Youth for Community Transformation"),
        ("Leadership and Organizing, 2021", "Leadership and Organizing"),
        ("Capacity Building of Peacebuilders, 2020", "Global Peace Foundation"),
        ("Moral & Innovative Leadership, 2020", "Global Peace Foundation")
    ],
    "volunteering": [
        ("Flood Relief Campaign, 2024", "Global Peace Foundation"),
        ("Learn and Earn by Doing, 2024", "Awareness 360"),
        ("World Social Forum, 2024", "World Social Forum"),
        ("10th Undergraduate Practicum Assessment Symposium, 2023", "RD-TEC, Lamjung Campus"),
        ("Blood Donation, 2023", "Nepal RedCross Society")
    ],
    "referees": [
        {"name": "Dr. Mahesh Jaisi", "title": "Assistant Professor, IAAS", "phone": "+977 - 9851242082", "email": "mahesh.jaishi@gmail.com"},
        {"name": "Bhimsen Chaulagain", "title": "Senior Scientist S2, NARC", "phone": "+977 - 9860679982", "email": "bhimsen.chaulagain@gmail.com"},
        {"name": "Bambie Gordon Panta", "title": "Director, Global Peace Foundation Nepal", "phone": "+977 - 9849043897", "email": "bpanta@globalpeace.org"}
    ]
}

# -------------------------------------------------------------------------
# 6. Streamlit App & State Management
# -------------------------------------------------------------------------
st.set_page_config(page_title="Sudha Panthi - Application Matcher", layout="wide")

st.title("🌱 NGO/INGO Application Generator")
st.caption("⚡ Calibri Typography, Eye-Catchy Bold/Italic Styling & Multi-Vacancy Engine")

# Initialize Session State
if "detected_positions" not in st.session_state:
    st.session_state.detected_positions = []
if "generated_app_data" not in st.session_state:
    st.session_state.generated_app_data = None
if "cv_pdf_bytes" not in st.session_state:
    st.session_state.cv_pdf_bytes = None
if "cl_pdf_bytes" not in st.session_state:
    st.session_state.cl_pdf_bytes = None
if "active_role_title" not in st.session_state:
    st.session_state.active_role_title = ""

raw_key = st.secrets.get("GROQ_API_KEY", None)
if not raw_key:
    raw_key = st.sidebar.text_input("Groq API Key (starts with gsk_):", type="password")

api_key = raw_key.strip().strip('"').strip("'") if raw_key else None
if api_key and api_key.startswith("gsk_"):
    st.sidebar.success("⚡ Groq API Key Connected")

input_mode = st.radio(
    "Select Vacancy Input Format:",
    ["📝 Paste Job Description / Text", "🖼️ Upload Vacancy Image / Screenshot"],
    horizontal=True
)

vacancy_text = ""
uploaded_image_bytes = None

if "Paste" in input_mode:
    vacancy_text = st.text_area(
        "Paste Job Vacancy / TOR text here:",
        placeholder="Paste full job description, TOR, requirements, and responsibilities here...",
        height=260
    )
else:
    up_file = st.file_uploader("Upload Vacancy Notice (JPG, PNG)", type=["jpg", "jpeg", "png"])
    if up_file:
        uploaded_image_bytes = up_file.getvalue()
        st.image(uploaded_image_bytes, caption="Uploaded Notice", use_container_width=True)

has_input = (bool(vacancy_text.strip()) if "Paste" in input_mode else uploaded_image_bytes is not None)

# Step 1: Scan for positions
if has_input and api_key:
    col_scan, _ = st.columns([1, 2])
    with col_scan:
        if st.button("🔍 Step 1: Scan Notice & Detect Positions", type="secondary"):
            with st.spinner("Scanning positions in vacancy announcement..."):
                try:
                    client = Groq(api_key=api_key)
                    text_model, vision_model = get_groq_active_models(client)

                    scan_prompt = """
                    Scan this job announcement and list all individual job vacancies/positions available.
                    Return a JSON object:
                    {
                        "organization": "Organization Name",
                        "positions": ["Job Title 1", "Job Title 2"]
                    }
                    If only one position is mentioned, return a list with that single position.
                    """

                    if "Paste" in input_mode:
                        msgs = [
                            {"role": "system", "content": scan_prompt},
                            {"role": "user", "content": f"VACANCY TEXT:\n{vacancy_text}"}
                        ]
                        scan_model = text_model
                    else:
                        scan_model = vision_model
                        b64_img = base64.b64encode(uploaded_image_bytes).decode("utf-8")
                        msgs = [
                            {"role": "system", "content": scan_prompt},
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "List all positions in this notice in JSON:"},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                                ]
                            }
                        ]

                    res = client.chat.completions.create(
                        model=scan_model,
                        messages=msgs,
                        response_format={"type": "json_object"},
                        temperature=0.1
                    )
                    parsed_scan = json.loads(res.choices[0].message.content)
                    st.session_state.detected_positions = parsed_scan.get("positions", ["Project Officer"])
                    st.session_state.org_name = parsed_scan.get("organization", "NGO/INGO")
                except Exception as e:
                    st.error(f"Scan error: {e}")

# Step 2: Role selection and full generation
if st.session_state.detected_positions:
    st.markdown("---")
    if len(st.session_state.detected_positions) > 1:
        st.warning(f"🔔 Found {len(st.session_state.detected_positions)} vacancies in this notice!")
        selected_role = st.selectbox(
            "Which position would you like to apply for?", 
            options=st.session_state.detected_positions
        )
    else:
        selected_role = st.session_state.detected_positions[0]
        st.success(f"🎯 Target Vacancy: **{selected_role}**")

    if st.button(f"🚀 Generate Application for '{selected_role}'", type="primary"):
        with st.spinner(f"Crafting eye-catchy application in Calibri typography..."):
            try:
                client = Groq(api_key=api_key)
                text_model, vision_model = get_groq_active_models(client)

                full_prompt = f"""
                You are an expert HR recruitment specialist for national and international NGOs in Nepal (UN, USAID, FCDO partners, Save the Children, CARE).
                Candidate: SUDHA PANTHI (Phone: +977-9860906707, Email: Sudha.panthee@gmail.com).
                Target Position: {selected_role}

                CRITICAL STYLING & CONTENT INSTRUCTIONS:
                1. EYE-CATCHING BOLD & ITALIC FORMATTING:
                   - In the COVER LETTER and CV EXPERIENCE BULLETS, strategically use **bold** (e.g., **MATSYA Project**, **Kobo Toolbox**, **NARC**, **Priority Matrix**, **IPM**, **70 participants**, **36 farmers**) for high-impact keywords, methodologies, tools, and metrics.
                   - Use *italics* for degrees, project titles, or key developmental values (*Do No Harm*, *GESI*, *Modernising Aquaculture in Nepal*).
                   - This makes the application visually eye-catching and easy for HR scanners to spot core qualifications.

                2. MAJOR WORKS UNDER EXPERIENCE (EXPANDED & JD-ALIGNED):
                   - Provide 4 to 6 detailed, action-packed bullet points per organization.
                   - Align language to {selected_role} (MEAL, field data collection, local Palika coordination, training facilitation, report writing).
                   - Strictly ground duties in her authentic organizations:
                     * Nepal Development Research Institute (MATSYA Project, Feb-May 2025): Fisheries KII/FGDs, Kobo Toolbox real-time survey management, stakeholder qualitative transcription.
                     * National Agriculture Research Centre (NARC Agronomy Division, 2023-2024): Pipeline wheat trials, JTA field guidance, laboratory & agronomic data analysis, technical research reporting.
                     * Global Peace Foundation (June 2023-Feb 2024): Priority matrix/logframe community assessments, Tanahu organic farming/water management/IPM/Jhol Mol implementation, leadership & food security capacity building.
                     * Harihar Women Savings and Loan Cooperatives Limited (April-May 2024): 7-day training on off-season vegetables, crop demonstration, IPM for women farmers.

                3. COMPREHENSIVE, IN-DEPTH COVER LETTER:
                   - Write a thorough, formal, 4-paragraph cover letter tailored specifically to {selected_role}.
                   - Header must include Sudha's contact info (+977-9860906707 | Sudha.panthee@gmail.com).
                   - Paragraph 1: State role, organization, project relevance, and deep motivation.
                   - Paragraph 2: Highlight technical research, trial designs, and data tools (NARC, NDRI, Kobo Toolbox).
                   - Paragraph 3: Highlight grassroots mobilization, community training, and local coordination (GPF, Harihar Cooperative).
                   - Paragraph 4: Reiterate commitment to humanitarian standards, safeguarding, and interview readiness.
                   - Formally sign off with Sudha Panthi, Phone: +977-9860906707, Email: Sudha.panthee@gmail.com.

                4. FORMAL GMAIL APPLICATION EMAIL:
                   - Subject line and polite Gmail message body listing attached documents: CV (PDF), Cover Letter (PDF), Academic Transcripts, Nagarikta, and Certificates.

                Return valid JSON only matching this structure:
                {{
                    "vacancy_details": {{
                        "job_title": "{selected_role}",
                        "organization": "string"
                    }},
                    "email_subject": "Application for {selected_role} - Sudha Panthi",
                    "email_body": "Formal Gmail body text with attached documents checklist and contact details...",
                    "tailored_career_objective": "3-5 lines with bold/italic styling tailored to {selected_role}",
                    "tailored_skills": {{
                        "computer": "Microsoft Office, Adobe Photoshop, Adobe Illustrator, Arc-GIS, RStudio, GenStat, SPSS, Kobo Toolbox",
                        "languages": "Nepali (Native), English (Fluent)",
                        "targeted_technical_and_soft_skills": "6-8 prioritized competencies"
                    }},
                    "tailored_experience": [
                        {{
                            "organization": "Nepal Development Research Institute",
                            "location": "Sanepa, Lalitpur",
                            "role": "Field Researcher, MATSYA Project (Modernising Aquaculture in Nepal)",
                            "dates": "February-May,2025",
                            "bullets": ["Bullet with **bold** highlights", "Bullet with **bold** highlights"]
                        }},
                        {{
                            "organization": "National Agriculture Research Centre, Government of Nepal (Agronomy Division)",
                            "location": "Khumaltar, Lalitpur",
                            "role": "Research Assistant",
                            "dates": "2023-2024",
                            "bullets": ["Bullet with **bold** highlights", "Bullet with **bold** highlights"]
                        }},
                        {{
                            "organization": "Global Peace Foundation",
                            "location": "Nepal",
                            "role": "Fellowship, Global Peacebuilders Leadership Program",
                            "dates": "June 2023-February 2024",
                            "bullets": ["Bullet with **bold** highlights", "Bullet with **bold** highlights"]
                        }},
                        {{
                            "organization": "Harihar Women Savings and Loan Cooperatives Limited",
                            "location": "Pokhara, Nepal",
                            "role": "Trainer",
                            "dates": "April 29-May 5,2024",
                            "bullets": ["Bullet with **bold** highlights", "Bullet with **bold** highlights"]
                        }}
                    ],
                    "cover_letter": "Comprehensive 4-paragraph cover letter using **bold** and *italic* highlights, ending with Sudha's phone (+977-9860906707) and email"
                }}
                """

                if "Paste" in input_mode:
                    exec_model = text_model
                    exec_msgs = [
                        {"role": "system", "content": full_prompt},
                        {"role": "user", "content": f"VACANCY TEXT:\n{vacancy_text}"}
                    ]
                else:
                    exec_model = vision_model
                    b64_img = base64.b64encode(uploaded_image_bytes).decode("utf-8")
                    exec_msgs = [
                        {"role": "system", "content": full_prompt},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": f"Tailor application for {selected_role} in JSON:"},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                            ]
                        }
                    ]

                resp = client.chat.completions.create(
                    model=exec_model,
                    messages=exec_msgs,
                    response_format={"type": "json_object"},
                    temperature=0.2
                )
                data = json.loads(resp.choices[0].message.content.strip())

                # Normalize types
                if isinstance(data.get("tailored_career_objective"), list):
                    data["tailored_career_objective"] = " ".join(str(x) for x in data["tailored_career_objective"])
                if isinstance(data.get("cover_letter"), list):
                    data["cover_letter"] = "\n\n".join(str(x) for x in data["cover_letter"])
                if isinstance(data.get("email_body"), list):
                    data["email_body"] = "\n\n".join(str(x) for x in data["email_body"])

                skills_dict = data.get("tailored_skills", {})
                for k in ["computer", "languages", "targeted_technical_and_soft_skills"]:
                    if isinstance(skills_dict.get(k), list):
                        skills_dict[k] = ", ".join(str(x) for x in skills_dict[k])

                avail_w = 210 - 16 - 16

                # -------------------------------------------------------------
                # BUILD FULL CV PDF (Calibri + Eye-Catchy Bold Bullets)
                # -------------------------------------------------------------
                cv_pdf = CompleteCVPDF(doc_type="CV")
                cv_pdf.add_page()
                cv_pdf.draw_cv_header()
                
                # 1. Career Objective
                cv_pdf.draw_section_heading("Career Objective")
                cv_pdf.set_x(cv_pdf.l_margin)
                cv_pdf.set_font(cv_pdf.font_family, "", 9.2)
                cv_pdf.set_text_color(30, 30, 30)
                cv_pdf.multi_cell(avail_w, 4.4, clean_text(data.get("tailored_career_objective", "")), markdown=True, new_x="LMARGIN", new_y="NEXT")
                cv_pdf.ln(1)

                # 2. Experience (Rendered with Bold/Italic Markdown)
                cv_pdf.draw_section_heading("Experience")
                for org in data.get("tailored_experience", []):
                    raw_bullets = org.get("bullets", [])
                    if raw_bullets:
                        cv_pdf.draw_org_block(
                            org.get("organization", ""),
                            org.get("location", ""),
                            org.get("role", ""),
                            org.get("dates", ""),
                            [clean_text(b) for b in raw_bullets]
                        )

                # 3. Publication (With Clickable Blue DOI Hyperlink)
                cv_pdf.draw_section_heading("Publication")
                cv_pdf.set_x(cv_pdf.l_margin)
                cv_pdf.set_font(cv_pdf.font_family, "", 9)
                cv_pdf.set_text_color(30, 30, 30)
                cv_pdf.write(4.2, clean_text(PERMANENT_CV_SECTIONS["publication_text"]))
                
                # Render Blue DOI Link
                cv_pdf.set_text_color(0, 80, 200)
                doi_link = PERMANENT_CV_SECTIONS["publication_doi"]
                cv_pdf.write(4.2, doi_link, link=doi_link)
                cv_pdf.set_text_color(30, 30, 30)
                cv_pdf.ln(5)

                # 4. Projects
                cv_pdf.draw_section_heading("Projects")
                cv_pdf.set_font(cv_pdf.font_family, "", 9)
                for proj in PERMANENT_CV_SECTIONS["projects"]:
                    cv_pdf.set_x(cv_pdf.l_margin)
                    cv_pdf.multi_cell(avail_w, 4.2, f"-  {clean_text(proj)}", new_x="LMARGIN", new_y="NEXT")
                cv_pdf.ln(1)

                # 5. Education
                cv_pdf.draw_section_heading("Education")
                for edu in PERMANENT_CV_SECTIONS["education"]:
                    cv_pdf.draw_two_col_entry(edu["inst"], edu["deg"], edu["loc"], edu["yr"])

                # 6. Leadership Activities
                cv_pdf.draw_section_heading("Leadership Activities")
                for lead in PERMANENT_CV_SECTIONS["leadership"]:
                    cv_pdf.set_x(cv_pdf.l_margin)
                    cv_pdf.set_font(cv_pdf.font_family, "B", 9.4)
                    cv_pdf.cell(115, 4.5, clean_text(lead["org"]), align="L")
                    cv_pdf.set_font(cv_pdf.font_family, "", 9)
                    cv_pdf.cell(avail_w - 115, 4.5, clean_text(lead["loc"]), align="R", new_x="LMARGIN", new_y="NEXT")
                    for r_title, r_desc in lead["roles"]:
                        cv_pdf.set_x(cv_pdf.l_margin)
                        cv_pdf.set_font(cv_pdf.font_family, "I", 9)
                        cv_pdf.cell(avail_w, 4.0, clean_text(r_title), new_x="LMARGIN", new_y="NEXT")
                        cv_pdf.set_x(cv_pdf.l_margin)
                        cv_pdf.set_font(cv_pdf.font_family, "", 8.8)
                        cv_pdf.multi_cell(avail_w, 4.0, f"  {clean_text(r_desc)}", new_x="LMARGIN", new_y="NEXT")
                    cv_pdf.ln(1)

                # 7. Trainings and Workshops
                cv_pdf.draw_section_heading("Trainings and Workshops")
                for tr_title, tr_org in PERMANENT_CV_SECTIONS["trainings"]:
                    cv_pdf.draw_two_col_entry(tr_title, "", tr_org, "")

                # 8. Volunteering
                cv_pdf.draw_section_heading("Volunteering")
                for vol_title, vol_org in PERMANENT_CV_SECTIONS["volunteering"]:
                    cv_pdf.draw_two_col_entry(vol_title, "", vol_org, "")

                # 9. Skills
                cv_pdf.draw_section_heading("Skills")
                cv_pdf.set_x(cv_pdf.l_margin)
                cv_pdf.set_font(cv_pdf.font_family, "B", 9)
                cv_pdf.write(4.2, "Computer: ")
                cv_pdf.set_font(cv_pdf.font_family, "", 9)
                cv_pdf.write(4.2, f"{clean_text(skills_dict.get('computer', ''))}\n")
                cv_pdf.ln(1)

                cv_pdf.set_x(cv_pdf.l_margin)
                cv_pdf.set_font(cv_pdf.font_family, "B", 9)
                cv_pdf.write(4.2, "Language: ")
                cv_pdf.set_font(cv_pdf.font_family, "", 9)
                cv_pdf.write(4.2, f"{clean_text(skills_dict.get('languages', ''))}\n")
                cv_pdf.ln(1)

                cv_pdf.set_x(cv_pdf.l_margin)
                cv_pdf.set_font(cv_pdf.font_family, "B", 9)
                cv_pdf.write(4.2, "Vacancy Skills: ")
                cv_pdf.set_font(cv_pdf.font_family, "", 9)
                cv_pdf.write(4.2, f"{clean_text(skills_dict.get('targeted_technical_and_soft_skills', ''))}\n")
                cv_pdf.ln(1)

                # 10. Referees (Bhimsen Chaulagain's phone fixed to 9860679982)
                cv_pdf.draw_section_heading("Referees")
                for ref in PERMANENT_CV_SECTIONS["referees"]:
                    cv_pdf.set_x(cv_pdf.l_margin)
                    cv_pdf.set_font(cv_pdf.font_family, "B", 9.2)
                    cv_pdf.cell(70, 4, clean_text(ref["name"]), align="L")
                    cv_pdf.set_font(cv_pdf.font_family, "", 9)
                    cv_pdf.cell(avail_w - 70, 4, f"{clean_text(ref['phone'])} | {clean_text(ref['email'])}", align="R", new_x="LMARGIN", new_y="NEXT")
                    cv_pdf.set_x(cv_pdf.l_margin)
                    cv_pdf.set_font(cv_pdf.font_family, "I", 8.8)
                    cv_pdf.cell(avail_w, 3.8, clean_text(ref["title"]), new_x="LMARGIN", new_y="NEXT")
                    cv_pdf.ln(1.5)

                cv_buf = io.BytesIO()
                cv_pdf.output(cv_buf)
                
                # -------------------------------------------------------------
                # BUILD EYE-CATCHING COVER LETTER PDF (Markdown Bold/Italic)
                # -------------------------------------------------------------
                cl_pdf = CompleteCVPDF(doc_type="Cover Letter")
                cl_pdf.add_page()
                cl_pdf.draw_cv_header()
                cl_pdf.draw_section_heading(f"Application for {selected_role}")
                
                cl_pdf.set_x(cl_pdf.l_margin)
                cl_pdf.set_font(cl_pdf.font_family, "", 9.8)
                cl_pdf.set_text_color(30, 30, 30)
                cl_pdf.multi_cell(avail_w, 4.8, clean_text(data.get("cover_letter", "")), markdown=True, new_x="LMARGIN", new_y="NEXT")
                
                cl_buf = io.BytesIO()
                cl_pdf.output(cl_buf)

                # Store into Streamlit Session State
                st.session_state.generated_app_data = data
                st.session_state.cv_pdf_bytes = cv_buf.getvalue()
                st.session_state.cl_pdf_bytes = cl_buf.getvalue()
                st.session_state.active_role_title = selected_role

            except Exception as e:
                st.error(f"Generation error: {e}")

# -------------------------------------------------------------------------
# 7. Render Results from Session State (Persists after clicking Download)
# -------------------------------------------------------------------------
if st.session_state.generated_app_data is not None:
    data = st.session_state.generated_app_data
    active_role = st.session_state.active_role_title

    st.markdown("---")
    st.success(f"Application ready for: **{active_role}**")

    tab_cv, tab_cl, tab_email = st.tabs([
        "📄 Tailored Full CV (Calibri)", 
        "✉️ Eye-Catchy Cover Letter", 
        "📧 Email Body (Gmail Template)"
    ])

    with tab_cv:
        st.markdown("### Adapted Career Objective")
        st.markdown(clean_text(data.get("tailored_career_objective", "")))

        st.markdown("### Expanded Major Works Under Experience (JD Aligned)")
        for org in data.get("tailored_experience", []):
            with st.expander(f"📍 {clean_text(org.get('organization', ''))} — {clean_text(org.get('role', ''))}", expanded=True):
                for b in org.get("bullets", []):
                    st.markdown(f"• {clean_text(b)}")

        st.download_button(
            label="📥 Download Complete Tailored CV (PDF - Calibri)",
            data=st.session_state.cv_pdf_bytes,
            file_name=f"Sudha_Panthi_CV_{active_role.replace(' ', '_')}.pdf",
            mime="application/pdf",
            key="btn_download_cv"
        )

    with tab_cl:
        st.subheader("Eye-Catchy Formal Cover Letter")
        st.markdown(clean_text(data.get("cover_letter", "")))
        
        st.download_button(
            label="📥 Download Cover Letter (PDF - Calibri)",
            data=st.session_state.cl_pdf_bytes,
            file_name=f"Sudha_Panthi_Cover_Letter_{active_role.replace(' ', '_')}.pdf",
            mime="application/pdf",
            key="btn_download_cl"
        )

    with tab_email:
        st.subheader("Formal Gmail Message (Copy & Send)")
        st.write("Use this exact subject line and body when submitting your application via email:")

        email_sub = clean_text(data.get("email_subject", f"Application for {active_role} - Sudha Panthi"))
        st.text_input("Subject Line:", value=email_sub, key="email_sub_input")

        email_msg = clean_text(data.get("email_body", ""))
        st.text_area("Email Body:", value=email_msg, height=350, key="email_body_area")
        st.caption("📎 Make sure to attach: CV (PDF), Cover Letter (PDF), Transcripts, and Nagarikta before sending.")
