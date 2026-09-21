import streamlit as st
from groq import Groq
from PIL import Image
from fpdf import FPDF
from datetime import datetime
import json
import base64
import io
import os
import re
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
    win_dir = "C:\\Windows\\Fonts"
    win_reg = os.path.join(win_dir, "calibri.ttf")
    win_bold = os.path.join(win_dir, "calibrib.ttf")
    win_ital = os.path.join(win_dir, "calibrii.ttf")
    if os.path.exists(win_reg) and os.path.exists(win_bold) and os.path.exists(win_ital):
        return "Calibri", {"": win_reg, "B": win_bold, "I": win_ital}

    if os.path.exists("calibri.ttf") and os.path.exists("calibrib.ttf") and os.path.exists("calibrii.ttf"):
        return "Calibri", {"": "calibri.ttf", "B": "calibrib.ttf", "I": "calibrii.ttf"}

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
        return "Helvetica", None


# -------------------------------------------------------------------------
# 2. Clean Text Function (Removes '???' and raw asterisks)
# -------------------------------------------------------------------------
def clean_text(val):
    """Safely converts unicode to clean ASCII, stripping characters that turn into '???' and removes stray asterisks"""
    if val is None:
        return ""
    if isinstance(val, list):
        val = ", ".join(str(item) for item in val if item is not None)
    elif not isinstance(val, str):
        val = str(val)

    # Remove markdown asterisks to prevent raw '*word*' mistakes
    val = val.replace("**", "").replace("*", "")

    replacements = {
        "’": "'", "‘": "'", "“": '"', "”": '"', "`": "'",
        "–": "-", "—": "-", "―": "-", "…": "...",
        "•": "-", "▪": "-", "►": "-", "·": "-", "★": "-",
        "✓": "[x]", "✔": "[x]", "✔️": "[x]",
        "\u00a0": " ", "\u200b": "", "\u2003": " ", "\t": "    "
    }
    for k, v in replacements.items():
        val = val.replace(k, v)

    val = unicodedata.normalize('NFKD', val).encode('ascii', 'ignore').decode('ascii')
    return val.strip()


# -------------------------------------------------------------------------
# 3. PDF Builder (Calibri Typography & Clean Layout)
# -------------------------------------------------------------------------
class CompleteCVPDF(FPDF):
    def __init__(self, doc_type="CV"):
        super().__init__(format="A4", unit="mm")
        self.doc_type = doc_type
        self.set_margins(16, 14, 16)
        self.set_auto_page_break(auto=True, margin=15)

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
        """Organization Block with clean bullets"""
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

        self.set_font(self.font_family, "", 9)
        self.set_text_color(35, 35, 35)
        for bullet in bullets:
            self.set_x(self.l_margin)
            self.multi_cell(avail_w, 4.3, f"-  {clean_text(bullet)}", new_x="LMARGIN", new_y="NEXT")
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

# Initialize Session State
if "detected_positions" not in st.session_state:
    st.session_state.detected_positions = []
if "target_position" not in st.session_state:
    st.session_state.target_position = ""
if "generated_app_data" not in st.session_state:
    st.session_state.generated_app_data = None
if "cv_pdf_bytes" not in st.session_state:
    st.session_state.cv_pdf_bytes = None
if "cl_pdf_bytes" not in st.session_state:
    st.session_state.cl_pdf_bytes = None

raw_key = st.secrets.get("GROQ_API_KEY", None)
if not raw_key:
    raw_key = st.sidebar.text_input("Groq API Key (starts with gsk_):", type="password")

api_key = raw_key.strip().strip('"').strip("'") if raw_key else None

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
        height=240
    )
else:
    up_file = st.file_uploader("Upload Vacancy Notice (JPG, PNG)", type=["jpg", "jpeg", "png"])
    if up_file:
        uploaded_image_bytes = up_file.getvalue()
        st.image(uploaded_image_bytes, caption="Uploaded Notice", use_container_width=True)

has_input = (bool(vacancy_text.strip()) if "Paste" in input_mode else uploaded_image_bytes is not None)

# -------------------------------------------------------------------------
# STEP 1: POSITION SECTION (ALWAYS VISIBLE)
# -------------------------------------------------------------------------
st.markdown("---")
st.subheader("🎯 Step 1: Target Position")

col_p1, col_p2 = st.columns([2, 1])

with col_p2:
    st.write("")
    st.write("")
    scan_clicked = st.button("🔍 Scan Notice for Positions", disabled=not (has_input and api_key))

if scan_clicked:
    with st.spinner("Scanning notice for positions..."):
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
            detected = parsed_scan.get("positions", [])
            st.session_state.detected_positions = detected
            if detected:
                st.session_state.target_position = detected[0]
        except Exception as e:
            st.error(f"Scan error: {e}")

with col_p1:
    if st.session_state.detected_positions:
        if len(st.session_state.detected_positions) > 1:
            selected_pos = st.selectbox(
                "Detected Vacancies (Select one or type below):",
                options=st.session_state.detected_positions,
                index=0
            )
            st.session_state.target_position = selected_pos
        else:
            st.session_state.target_position = st.session_state.detected_positions[0]
    
    # Always display the confirmed target position in an editable text box
    target_role = st.text_input(
        "Target Position (Auto-detected or Type manually):",
        value=st.session_state.target_position,
        placeholder="e.g. Project Officer, Agriculture Coordinator, Field Researcher"
    )
    st.session_state.target_position = target_role

# -------------------------------------------------------------------------
# STEP 2: GENERATE APPLICATION
# -------------------------------------------------------------------------
st.markdown("### 🚀 Step 2: Generate Application")
can_generate = bool(target_role.strip()) and has_input and bool(api_key)

if st.button("Generate Complete Application", type="primary", disabled=not can_generate):
    with st.spinner(f"Crafting clean application for '{target_role}' in Calibri typography..."):
        try:
            client = Groq(api_key=api_key)
            text_model, vision_model = get_groq_active_models(client)

            today_formatted = datetime.today().strftime("%B %d, %Y")

            full_prompt = f"""
            You are an expert HR recruitment specialist for national and international NGOs in Nepal (UN, USAID, FCDO partners, Save the Children, CARE).
            Candidate: SUDHA PANTHI (Phone: +977-9860906707, Email: Sudha.panthee@gmail.com).
            Target Position: {target_role}
            Today's Exact Date: {today_formatted}

            CRITICAL FACTUAL & FORMATTING RULES:
            1. STRICT DEGREE ACCURACY:
               - Sudha's degree is ONLY: Bachelor of Science in Agriculture (B.Sc. Agriculture) and ongoing Master of Science in Agriculture (M.Sc. Agriculture) from IAAS, Tribhuvan University.
               - DO NOT state she has a degree in "Rural Development" or any other subject.
            
            2. NO ASTERISKS / NO RAW MARKDOWN:
               - DO NOT use markdown asterisks (* or **) anywhere in the cover letter or bullets.
               - Write in clean, formal, professional English text without any symbols.

            3. DATE MANDATE:
               - Start the cover letter text with today's real date: {today_formatted}.
               - NEVER use placeholders like "[Date]".

            4. MAJOR WORKS UNDER EXPERIENCE:
               - Provide 4 to 6 detailed, action-packed bullet points per organization.
               - Ground duties strictly in her authentic organizations:
                 * Nepal Development Research Institute (MATSYA Project, Feb-May 2025): Fisheries KII/FGDs, Kobo Toolbox real-time survey management, stakeholder qualitative transcription.
                 * National Agriculture Research Centre (NARC Agronomy Division, 2023-2024): Pipeline wheat trials, JTA field guidance, laboratory & agronomic data analysis, technical research reporting.
                 * Global Peace Foundation (June 2023-Feb 2024): Priority matrix/logframe community assessments, Tanahu organic farming/water management/IPM/Jhol Mol implementation, leadership & food security capacity building.
                 * Harihar Women Savings and Loan Cooperatives Limited (April-May 2024): 7-day training on off-season vegetables, crop demonstration, IPM for women farmers.

            5. COMPREHENSIVE COVER LETTER:
               - 4 detailed, formal paragraphs addressed to Hiring Committee / {target_role}.
               - Include Sudha's contact info (+977-9860906707 | Sudha.panthee@gmail.com).

            6. GMAIL APPLICATION EMAIL:
               - Subject line and formal Gmail body listing attached documents: CV (PDF), Cover Letter (PDF), Academic Transcripts, and Nagarikta.

            Return valid JSON only:
            {{
                "vacancy_details": {{
                    "job_title": "{target_role}",
                    "organization": "string"
                }},
                "email_subject": "Application for {target_role} - Sudha Panthi",
                "email_body": "Formal Gmail body text with attached documents checklist and contact details...",
                "tailored_career_objective": "3-5 lines tailored to {target_role} without asterisks",
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
                        "bullets": ["Detailed clean bullet without asterisks", "Detailed clean bullet"]
                    }},
                    {{
                        "organization": "National Agriculture Research Centre, Government of Nepal (Agronomy Division)",
                        "location": "Khumaltar, Lalitpur",
                        "role": "Research Assistant",
                        "dates": "2023-2024",
                        "bullets": ["Detailed clean bullet without asterisks", "Detailed clean bullet"]
                    }},
                    {{
                        "organization": "Global Peace Foundation",
                        "location": "Nepal",
                        "role": "Fellowship, Global Peacebuilders Leadership Program",
                        "dates": "June 2023-February 2024",
                        "bullets": ["Detailed clean bullet without asterisks", "Detailed clean bullet"]
                    }},
                    {{
                        "organization": "Harihar Women Savings and Loan Cooperatives Limited",
                        "location": "Pokhara, Nepal",
                        "role": "Trainer",
                        "dates": "April 29-May 5,2024",
                        "bullets": ["Detailed clean bullet without asterisks", "Detailed clean bullet"]
                    }}
                ],
                "cover_letter": "{today_formatted}\\n\\nHiring Committee... (4 thorough paragraphs without any asterisks, ending with Sudha's phone +977-9860906707 and email)"
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
                            {"type": "text", "text": f"Tailor application for {target_role} in JSON:"},
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

            # Normalize types & ensure date
            if isinstance(data.get("tailored_career_objective"), list):
                data["tailored_career_objective"] = " ".join(str(x) for x in data["tailored_career_objective"])
            if isinstance(data.get("cover_letter"), list):
                data["cover_letter"] = "\n\n".join(str(x) for x in data["cover_letter"])
            if isinstance(data.get("email_body"), list):
                data["email_body"] = "\n\n".join(str(x) for x in data["email_body"])

            # Post-process Cover Letter Date & replace placeholders
            raw_cl = clean_text(data.get("cover_letter", ""))
            raw_cl = re.sub(r'\[\s*Date\s*\]', today_formatted, raw_cl, flags=re.IGNORECASE)
            if not raw_cl.startswith(today_formatted):
                raw_cl = f"{today_formatted}\n\n" + raw_cl
            data["cover_letter"] = raw_cl

            skills_dict = data.get("tailored_skills", {})
            for k in ["computer", "languages", "targeted_technical_and_soft_skills"]:
                if isinstance(skills_dict.get(k), list):
                    skills_dict[k] = ", ".join(str(x) for x in skills_dict[k])

            avail_w = 210 - 16 - 16

            # -------------------------------------------------------------
            # BUILD FULL CV PDF (Calibri)
            # -------------------------------------------------------------
            cv_pdf = CompleteCVPDF(doc_type="CV")
            cv_pdf.add_page()
            cv_pdf.draw_cv_header()
            
            # 1. Career Objective
            cv_pdf.draw_section_heading("Career Objective")
            cv_pdf.set_x(cv_pdf.l_margin)
            cv_pdf.set_font(cv_pdf.font_family, "", 9.2)
            cv_pdf.set_text_color(30, 30, 30)
            cv_pdf.multi_cell(avail_w, 4.4, clean_text(data.get("tailored_career_objective", "")), new_x="LMARGIN", new_y="NEXT")
            cv_pdf.ln(1)

            # 2. Experience
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

            # 10. Referees (Bhimsen Chaulagain's phone: 9860679982)
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
            # BUILD COVER LETTER PDF (Clean - No Asterisks)
            # -------------------------------------------------------------
            cl_pdf = CompleteCVPDF(doc_type="Cover Letter")
            cl_pdf.add_page()
            cl_pdf.draw_cv_header()
            cl_pdf.draw_section_heading(f"Application for {target_role}")
            
            cl_pdf.set_x(cl_pdf.l_margin)
            cl_pdf.set_font(cl_pdf.font_family, "", 9.8)
            cl_pdf.set_text_color(30, 30, 30)
            cl_pdf.multi_cell(avail_w, 4.8, clean_text(data.get("cover_letter", "")), new_x="LMARGIN", new_y="NEXT")
            
            cl_buf = io.BytesIO()
            cl_pdf.output(cl_buf)

            # Store into Streamlit Session State
            st.session_state.generated_app_data = data
            st.session_state.cv_pdf_bytes = cv_buf.getvalue()
            st.session_state.cl_pdf_bytes = cl_buf.getvalue()

        except Exception as e:
            st.error(f"Generation error: {e}")

# -------------------------------------------------------------------------
# 7. Render Results from Session State
# -------------------------------------------------------------------------
if st.session_state.generated_app_data is not None:
    data = st.session_state.generated_app_data
    current_target = st.session_state.target_position

    st.markdown("---")
    st.success(f"Application ready for: **{current_target}**")

    tab_cv, tab_cl, tab_email = st.tabs(["CV", "Cover Letter", "Email"])

    with tab_cv:
        st.markdown("### Career Objective")
        st.write(clean_text(data.get("tailored_career_objective", "")))

        st.markdown("### Experience")
        for org in data.get("tailored_experience", []):
            with st.expander(f"📍 {clean_text(org.get('organization', ''))} - {clean_text(org.get('role', ''))}", expanded=True):
                for b in org.get("bullets", []):
                    st.write(f"- {clean_text(b)}")

        st.download_button(
            label="📥 Download CV (PDF)",
            data=st.session_state.cv_pdf_bytes,
            file_name=f"Sudha_Panthi_CV_{current_target.replace(' ', '_')}.pdf",
            mime="application/pdf",
            key="btn_download_cv"
        )

    with tab_cl:
        st.subheader("Cover Letter")
        st.text_area("Cover Letter Preview:", value=clean_text(data.get("cover_letter", "")), height=400, key="cl_preview_area")
        
        st.download_button(
            label="📥 Download Cover Letter (PDF)",
            data=st.session_state.cl_pdf_bytes,
            file_name=f"Sudha_Panthi_Cover_Letter_{current_target.replace(' ', '_')}.pdf",
            mime="application/pdf",
            key="btn_download_cl"
        )

    with tab_email:
        st.subheader("Email Template")
        email_sub = clean_text(data.get("email_subject", f"Application for {current_target} - Sudha Panthi"))
        st.text_input("Subject Line:", value=email_sub, key="email_sub_input")

        email_msg = clean_text(data.get("email_body", ""))
        st.text_area("Email Body:", value=email_msg, height=350, key="email_body_area")
        st.caption("Attach your CV (PDF), Cover Letter (PDF), Transcripts, and Nagarikta before sending.")
