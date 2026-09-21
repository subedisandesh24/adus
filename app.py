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
    if val is None:
        return ""
    if isinstance(val, list):
        val = ", ".join(str(item) for item in val if item is not None)
    elif not isinstance(val, str):
        val = str(val)

    # Strip markdown asterisks to guarantee zero raw '*word*' mistakes
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
# 3. PDF Builder (Calibri + Justified Alignment for Major Works)
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
        self.set_y(14)
        self.set_x(self.l_margin)
        
        # Name on Left
        self.set_font(self.font_family, "B", 18)
        self.set_text_color(20, 20, 20)
        self.cell(90, 10, "SUDHA PANTHI", align="L")
        
        # Contact Details on Right
        contact_x = self.w - self.r_margin - 88
        self.set_font(self.font_family, "", 9)
        
        self.set_xy(contact_x, 14)
        self.set_text_color(60, 60, 60)
        self.cell(88, 3.8, "+977-9860906707", align="R", new_x="LMARGIN", new_y="NEXT")
        
        self.set_x(contact_x)
        self.cell(88, 3.8, "Sudha.panthee@gmail.com", align="R", new_x="LMARGIN", new_y="NEXT")
        
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
        """Organization Block with JUSTIFIED alignment for major works"""
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

        # Bullets rendered with JUSTIFIED (align="J") alignment
        self.set_font(self.font_family, "", 9)
        self.set_text_color(35, 35, 35)
        for bullet in bullets:
            self.set_x(self.l_margin)
            self.multi_cell(avail_w, 4.3, f"-  {clean_text(bullet)}", align="J", new_x="LMARGIN", new_y="NEXT")
        self.ln(1.5)

    def draw_two_col_entry(self, left_bold, left_sub, right_txt, right_sub=""):
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
# 5. Permanent CV Database (Exact DOI & Bhimsen's Phone)
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
# 6. Streamlit Progressive Workflow State
# -------------------------------------------------------------------------
st.set_page_config(page_title="Sudha Panthi - Application Matcher", layout="wide")

st.title("🌱 NGO/INGO Application Generator")

# Initialize Session State Variables
if "scanned_data" not in st.session_state:
    st.session_state.scanned_data = None
if "selected_position" not in st.session_state:
    st.session_state.selected_position = ""
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
# STAGE 1: ONLY SHOW "Scan Notice" WHEN INPUT IS INSERTED
# -------------------------------------------------------------------------
if has_input and api_key:
    st.markdown("---")
    if st.button("🔍 Scan Notice", type="secondary"):
        with st.spinner("Scanning notice for positions and organization..."):
            try:
                client = Groq(api_key=api_key)
                text_model, vision_model = get_groq_active_models(client)

                scan_prompt = """
                Scan this job announcement and extract:
                1. The organization name.
                2. All distinct individual job vacancies/positions available.
                Return valid JSON only:
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
                                {"type": "text", "text": "Extract organization and positions in JSON:"},
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
                st.session_state.scanned_data = parsed_scan
                positions = parsed_scan.get("positions", [])
                if positions:
                    st.session_state.selected_position = positions[0]
            except Exception as e:
                st.error(f"Scan error: {e}")

# -------------------------------------------------------------------------
# STAGE 2 & 3: DISPLAY FINDINGS, ALLOW CHOICE, THEN SHOW "Generate Application"
# -------------------------------------------------------------------------
if st.session_state.scanned_data:
    org_name = st.session_state.scanned_data.get("organization", "Organization")
    positions = st.session_state.scanned_data.get("positions", [])
    total_vacancies = len(positions)

    st.markdown("---")
    st.info(f"🏢 **Organization:** {org_name}  |  📋 **Total Vacancies Found:** {total_vacancies}")

    if total_vacancies > 1:
        chosen_pos = st.selectbox(
            "Select which vacancy you want to apply for:",
            options=positions,
            index=0
        )
        st.session_state.selected_position = chosen_pos
    elif total_vacancies == 1:
        st.session_state.selected_position = positions[0]
        st.write(f"🎯 **Target Position:** {positions[0]}")
    else:
        manual_pos = st.text_input("Enter Position Title:", value="Project Officer")
        st.session_state.selected_position = manual_pos

    target_role = st.session_state.selected_position

    # STAGE 3: Show Generate Application Button AFTER choosing
    if target_role:
        st.write("")
        if st.button(f"🚀 Generate Application for '{target_role}'", type="primary"):
            with st.spinner(f"Crafting evidence-based INGO application in Calibri typography..."):
                try:
                    client = Groq(api_key=api_key)
                    text_model, vision_model = get_groq_active_models(client)

                    today_formatted = datetime.today().strftime("%B %d, %Y")

                    full_prompt = f"""
                    You are a senior recruitment director and technical advisor for international and national NGOs in Nepal (UN agencies, USAID, FCDO, EU partners, Save the Children, CARE, Plan International).
                    
                    Candidate: SUDHA PANTHI (Phone: +977-9860906707, Email: Sudha.panthee@gmail.com).
                    Target Position: {target_role}
                    Organization: {org_name}
                    Today's Exact Date: {today_formatted}

                    CRITICAL CANDIDATE PROFILE & EVIDENCE BASE:
                    - Degree: Bachelor of Science in Agriculture (B.Sc. Agriculture) from IAAS Tribhuvan University (Percentage: 75.38%, IDF Scholarship). Ongoing Master of Science in Agriculture (M.Sc. Agriculture, IAAS TU, 2025-Present).
                    - STRICT FACT: DO NOT state she has a degree in "Rural Development" or any other subject.
                    - Verified Track Record:
                      1. Nepal Development Research Institute (NDRI, MATSYA Project - Modernising Aquaculture in Nepal, Feb-May 2025):
                         Field Researcher: KIIs with fish farmers, breeders, government officers; FGD facilitation on value chain bottlenecks; door-to-door household questionnaires; transcription & reporting; real-time digital survey management using Kobo Toolbox.
                      2. National Agriculture Research Centre (NARC, Government of Nepal, Agronomy Division, 2023-2024):
                         Research Assistant: Guided Junior Technical Assistants (JTAs) on field agronomy trials; pipeline wheat variety field/lab experiments; data recording, statistical analysis, interpretation, and progress report writing.
                      3. Global Peace Foundation (June 2023-Feb 2024):
                         Fellow: Community needs assessment using Priority Matrix, Preference Ranking, and Logframe design; implemented 'Building a Path for Organic Community' in remote Tanahu village training 36 local farmers on efficient water management, nursery beds, IPM, and liquid bio-fertilizer (Jhol Mol); leadership & food waste reduction training in Lamjung (70 participants); menstrual hygiene/sustainable environment training at SOS Hermann Gmeiner School (75 students).
                      4. Harihar Women Savings and Loan Cooperatives Limited (Pokhara, April-May 2024):
                         Trainer: Delivered 7-day training on off-season vegetable cultivation and IPM; practical crop demonstrations for women cooperative members.
                      5. Technical Skills & Tools: Kobo Toolbox, Arc-GIS, RStudio, GenStat, SPSS, MS Office.

                    ========================================================================
                    SECTION A: IN-DEPTH, EVIDENCE-BASED COVER LETTER (~1 TO 1.2 PAGES)
                    ========================================================================
                    - Tone: Professional, confident, sincere, human, development-oriented, and practical.
                    - Evidence-Based: SHOW evidence rather than generic flattery: "Through my work with smallholder farmers, women cooperatives, and research trials, I have managed digital survey tools, facilitated participatory training, and executed field trials."
                    - Natural INGO Terminology: Weave in relevant development terms based on the JD: food security, livelihoods, resilience, inclusion (GESI), value chains, climate adaptation, capacity building, safeguarding, and MEAL.
                    - 5-Paragraph Structure:
                      * Paragraph 1 (Opening): Exact position, organization, professional identity (Agriculture & Livelihoods professional), and motivation.
                      * Paragraph 2 (Relevant Experience): Concrete evidence from NDRI (aquaculture survey, Kobo Toolbox, multi-stakeholder KIIs/FGDs) and NARC (wheat trials, JTA supervision).
                      * Paragraph 3 (Community Mobilization): Tanahu organic farming project (36 farmers, water management, IPM, Jhol Mol), Harihar women cooperative (off-season vegetables).
                      * Paragraph 4 (Technical Competence): Connecting agricultural science + field implementation + digital tools (Kobo Toolbox/GIS/RStudio) to the organization's goals.
                      * Paragraph 5 (Closing): Contribution, safeguarding, availability, and formal sign-off.
                    - Date Mandate: Start strictly with: "{today_formatted}\\n\\nHiring Committee\\n{org_name}\\n..."
                    - Closing: Formally end with:
                      "Sincerely,\\nSudha Panthi\\nPhone: +977-9860906707\\nEmail: Sudha.panthee@gmail.com\\nLalitpur / Kathmandu, Nepal"

                    ========================================================================
                    SECTION B: INGO-TAILORED CV (Calibri, Justified Major Works)
                    ========================================================================
                    1. Professional Identity Tagline:
                       e.g. "Agriculture & Livelihoods Professional | Food Security | Value Chains | Climate Resilience | MEAL"
                    2. Tailored Professional Summary (3-4 lines).
                    3. Core Competencies Matrix (8-12 prioritized competencies aligned to JD).
                    4. Professional Experience (Action + What + Who/Where + Result):
                       Provide 4-5 substantive, action-packed bullet points for each of the 4 authentic organizations with genuine numbers (36 farmers, 70 participants, 75 students, KIIs/FGDs).

                    ========================================================================
                    SECTION C: ADMINISTRATIVE GMAIL APPLICATION MESSAGE & ATTACHMENTS
                    ========================================================================
                    - Brief, formal, clear, and administrative email body.
                    - State position and source.
                    - 1-2 sentence statement of suitability.
                    - ATTACHMENTS LIST: Scan the notice to determine exactly what documents are requested. In standard NGO vacancies, this is strictly:
                      1. Updated Curriculum Vitae (CV)
                      2. Cover Letter
                      (Do not list transcripts or citizenship unless the vacancy explicitly asked for them).

                    NO ASTERISKS RULE: Do NOT use markdown asterisks (* or **) in any JSON string. Write clean, formal, standard English text.

                    Return valid JSON only matching this exact schema:
                    {{
                        "vacancy_details": {{
                            "job_title": "{target_role}",
                            "organization": "{org_name}"
                        }},
                        "cv_professional_tagline": "Agriculture & Livelihoods Professional | Food Security | Value Chains | Climate Resilience | MEAL",
                        "cv_professional_summary": "3-4 lines tailored professional summary...",
                        "cv_core_competencies": ["Competency 1", "Competency 2", "Competency 3", "Competency 4", "Competency 5", "Competency 6", "Competency 7", "Competency 8"],
                        "tailored_experience": [
                            {{
                                "organization": "Nepal Development Research Institute",
                                "location": "Sanepa, Lalitpur",
                                "role": "Field Researcher, MATSYA Project (Modernising Aquaculture in Nepal)",
                                "dates": "February-May,2025",
                                "bullets": ["Detailed action-result bullet 1", "Detailed action-result bullet 2", "Detailed action-result bullet 3", "Detailed action-result bullet 4"]
                            }},
                            {{
                                "organization": "National Agriculture Research Centre, Government of Nepal (Agronomy Division)",
                                "location": "Khumaltar, Lalitpur",
                                "role": "Research Assistant",
                                "dates": "2023-2024",
                                "bullets": ["Detailed action-result bullet 1", "Detailed action-result bullet 2", "Detailed action-result bullet 3", "Detailed action-result bullet 4"]
                            }},
                            {{
                                "organization": "Global Peace Foundation",
                                "location": "Nepal",
                                "role": "Fellowship, Global Peacebuilders Leadership Program",
                                "dates": "June 2023-February 2024",
                                "bullets": ["Detailed action-result bullet 1", "Detailed action-result bullet 2", "Detailed action-result bullet 3", "Detailed action-result bullet 4"]
                            }},
                            {{
                                "organization": "Harihar Women Savings and Loan Cooperatives Limited",
                                "location": "Pokhara, Nepal",
                                "role": "Trainer",
                                "dates": "April 29-May 5,2024",
                                "bullets": ["Detailed action-result bullet 1", "Detailed action-result bullet 2", "Detailed action-result bullet 3"]
                            }}
                        ],
                        "cover_letter": "{today_formatted}\\n\\nHiring Committee\\n{org_name}... (5 substantive evidence-based paragraphs, ending with Sudha's contact info)",
                        "email_subject": "Application for {target_role} - Sudha Panthi",
                        "email_body": "Formal Gmail body text with attachments checklist and contact details...",
                        "requested_documents": ["Updated CV (PDF)", "Cover Letter (PDF)"]
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

                    # Post-process Cover Letter Date & replace placeholders
                    raw_cl = clean_text(data.get("cover_letter", ""))
                    raw_cl = re.sub(r'\[\s*Date\s*\]', today_formatted, raw_cl, flags=re.IGNORECASE)
                    if not raw_cl.startswith(today_formatted):
                        raw_cl = f"{today_formatted}\n\n" + raw_cl
                    data["cover_letter"] = raw_cl

                    avail_w = 210 - 16 - 16

                    # ---------------------------------------------------------
                    # BUILD INGO-STYLE FULL CV PDF (Calibri + Justified Bullets)
                    # ---------------------------------------------------------
                    cv_pdf = CompleteCVPDF(doc_type="CV")
                    cv_pdf.add_page()
                    cv_pdf.draw_cv_header()
                    
                    # 1. Professional Identity Tagline
                    tagline = clean_text(data.get("cv_professional_tagline", "Agriculture & Livelihoods Professional | Food Security | Value Chains | Climate Resilience | MEAL"))
                    cv_pdf.set_x(cv_pdf.l_margin)
                    cv_pdf.set_font(cv_pdf.font_family, "B", 10.5)
                    cv_pdf.set_text_color(0, 80, 160)
                    cv_pdf.cell(avail_w, 5, tagline, new_x="LMARGIN", new_y="NEXT")
                    cv_pdf.ln(1)

                    # 2. Tailored Professional Summary (Justified)
                    summary_text = clean_text(data.get("cv_professional_summary", ""))
                    cv_pdf.set_x(cv_pdf.l_margin)
                    cv_pdf.set_font(cv_pdf.font_family, "", 9.2)
                    cv_pdf.set_text_color(30, 30, 30)
                    cv_pdf.multi_cell(avail_w, 4.3, summary_text, align="J", new_x="LMARGIN", new_y="NEXT")
                    cv_pdf.ln(1.5)

                    # 3. Core Competencies Matrix
                    cv_pdf.draw_section_heading("Core Competencies")
                    competencies = data.get("cv_core_competencies", [])
                    if isinstance(competencies, list) and competencies:
                        col_w = avail_w / 2
                        for i in range(0, len(competencies), 2):
                            cv_pdf.set_x(cv_pdf.l_margin)
                            cv_pdf.set_font(cv_pdf.font_family, "", 9)
                            cv_pdf.set_text_color(35, 35, 35)
                            c1 = f"[x]  {clean_text(competencies[i])}"
                            cv_pdf.cell(col_w, 4.2, c1, align="L")
                            if i + 1 < len(competencies):
                                c2 = f"[x]  {clean_text(competencies[i+1])}"
                                cv_pdf.cell(col_w, 4.2, c2, align="L", new_x="LMARGIN", new_y="NEXT")
                            else:
                                cv_pdf.ln(4.2)
                        cv_pdf.ln(1)

                    # 4. Professional Experience (Justified Bullets via draw_org_block)
                    cv_pdf.draw_section_heading("Professional Experience")
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

                    # 5. Publication (With Clickable Blue DOI Hyperlink)
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

                    # 6. Selected Field & Research Projects
                    cv_pdf.draw_section_heading("Selected Field & Research Projects")
                    cv_pdf.set_font(cv_pdf.font_family, "", 9)
                    for proj in PERMANENT_CV_SECTIONS["projects"]:
                        cv_pdf.set_x(cv_pdf.l_margin)
                        cv_pdf.multi_cell(avail_w, 4.2, f"-  {clean_text(proj)}", new_x="LMARGIN", new_y="NEXT")
                    cv_pdf.ln(1)

                    # 7. Education
                    cv_pdf.draw_section_heading("Education")
                    for edu in PERMANENT_CV_SECTIONS["education"]:
                        cv_pdf.draw_two_col_entry(edu["inst"], edu["deg"], edu["loc"], edu["yr"])

                    # 8. Leadership Activities
                    cv_pdf.draw_section_heading("Leadership & Community Engagement")
                    for lead in PERMANENT_CV_SECTIONS["leadership"]:
                        cv_pdf.set_x(cv_pdf.l_margin)
                        cv_pdf.set_font(cv_pdf.font_family, "B", 9.4)
                        cv_pdf.cell(115, 4.5, clean_text(lead["org"]), align="L")
                        cv_pdf.set_font("Helvetica", "", 9)
                        cv_pdf.cell(avail_w - 115, 4.5, clean_text(lead["loc"]), align="R", new_x="LMARGIN", new_y="NEXT")
                        for r_title, r_desc in lead["roles"]:
                            cv_pdf.set_x(cv_pdf.l_margin)
                            cv_pdf.set_font("Helvetica", "I", 9)
                            cv_pdf.cell(avail_w, 4.0, clean_text(r_title), new_x="LMARGIN", new_y="NEXT")
                            cv_pdf.set_x(cv_pdf.l_margin)
                            cv_pdf.set_font("Helvetica", "", 8.8)
                            cv_pdf.multi_cell(avail_w, 4.0, f"  {clean_text(r_desc)}", align="J", new_x="LMARGIN", new_y="NEXT")
                        cv_pdf.ln(1)

                    # 9. Relevant Trainings and Workshops
                    cv_pdf.draw_section_heading("Trainings & Capacity Building")
                    for tr_title, tr_org in PERMANENT_CV_SECTIONS["trainings"]:
                        cv_pdf.draw_two_col_entry(tr_title, "", tr_org, "")

                    # 10. Volunteering Records
                    cv_pdf.draw_section_heading("Volunteering & Community Action")
                    for vol_title, vol_org in PERMANENT_CV_SECTIONS["volunteering"]:
                        cv_pdf.draw_two_col_entry(vol_title, "", vol_org, "")

                    # 11. Technical Tools & Languages
                    cv_pdf.draw_section_heading("Technical Tools & Languages")
                    cv_pdf.set_x(cv_pdf.l_margin)
                    cv_pdf.set_font(cv_pdf.font_family, "B", 9)
                    cv_pdf.write(4.2, "Software & Analysis: ")
                    cv_pdf.set_font(cv_pdf.font_family, "", 9)
                    cv_pdf.write(4.2, "Kobo Toolbox, Arc-GIS, RStudio, GenStat, SPSS, Microsoft Office, Adobe Illustrator, Adobe Photoshop\n")
                    cv_pdf.ln(1)

                    cv_pdf.set_x(cv_pdf.l_margin)
                    cv_pdf.set_font(cv_pdf.font_family, "B", 9)
                    cv_pdf.write(4.2, "Languages: ")
                    cv_pdf.set_font(cv_pdf.font_family, "", 9)
                    cv_pdf.write(4.2, "Nepali (Native), English (Professional Working Proficiency)\n")
                    cv_pdf.ln(1)

                    # 12. Professional Referees (Bhimsen Chaulagain's phone: 9860679982)
                    cv_pdf.draw_section_heading("Referees")
                    for ref in PERMANENT_CV_SECTIONS["referees"]:
                        cv_pdf.set_x(cv_pdf.l_margin)
                        cv_pdf.set_font(cv_pdf.font_family, "B", 9.2)
                        cv_pdf.cell(70, 4, clean_text(ref["name"]), align="L")
                        cv_pdf.set_font("Helvetica", "", 9)
                        cv_pdf.cell(avail_w - 70, 4, f"{clean_text(ref['phone'])} | {clean_text(ref['email'])}", align="R", new_x="LMARGIN", new_y="NEXT")
                        cv_pdf.set_x(cv_pdf.l_margin)
                        cv_pdf.set_font("Helvetica", "I", 8.8)
                        cv_pdf.cell(avail_w, 3.8, clean_text(ref["title"]), new_x="LMARGIN", new_y="NEXT")
                        cv_pdf.ln(1.5)

                    cv_buf = io.BytesIO()
                    cv_pdf.output(cv_buf)
                    
                    # ---------------------------------------------------------
                    # BUILD EVIDENCE-BASED COVER LETTER PDF (Justified Flow)
                    # ---------------------------------------------------------
                    cl_pdf = CompleteCVPDF(doc_type="Cover Letter")
                    cl_pdf.add_page()
                    cl_pdf.draw_cv_header()
                    cl_pdf.draw_section_heading(f"Application for {target_role}")
                    
                    cl_pdf.set_x(cl_pdf.l_margin)
                    cl_pdf.set_font(cl_pdf.font_family, "", 9.5)
                    cl_pdf.set_text_color(30, 30, 30)
                    cl_pdf.multi_cell(avail_w, 4.8, clean_text(data.get("cover_letter", "")), align="J", new_x="LMARGIN", new_y="NEXT")
                    
                    cl_buf = io.BytesIO()
                    cl_pdf.output(cl_buf)

                    # Store state for persistent downloads
                    st.session_state.generated_app_data = data
                    st.session_state.cv_pdf_bytes = cv_buf.getvalue()
                    st.session_state.cl_pdf_bytes = cl_buf.getvalue()

                except Exception as e:
                    st.error(f"Generation error: {e}")

# -------------------------------------------------------------------------
# STAGE 4: DISPLAY CV, COVER LETTER, AND EMAIL WITH DOWNLOAD BUTTONS AT THE END
# -------------------------------------------------------------------------
if st.session_state.generated_app_data is not None:
    data = st.session_state.generated_app_data
    current_target = st.session_state.selected_position

    st.markdown("---")
    st.success(f"Application ready for: **{current_target}**")

    tab_cv, tab_cl, tab_email = st.tabs(["CV", "Cover Letter", "Email"])

    with tab_cv:
        st.markdown(f"### {clean_text(data.get('cv_professional_tagline', ''))}")
        st.write(clean_text(data.get("cv_professional_summary", "")))

        st.markdown("#### Core Competencies")
        comps = data.get("cv_core_competencies", [])
        if comps:
            cols = st.columns(3)
            for idx, comp in enumerate(comps):
                cols[idx % 3].write(f"✔ {clean_text(comp)}")

        st.markdown("#### Professional Experience (Justified Major Works)")
        for org in data.get("tailored_experience", []):
            with st.expander(f"📍 {clean_text(org.get('organization', ''))} - {clean_text(org.get('role', ''))}", expanded=True):
                for b in org.get("bullets", []):
                    st.write(f"- {clean_text(b)}")

        st.write("")
        st.download_button(
            label="📥 Download CV (PDF)",
            data=st.session_state.cv_pdf_bytes,
            file_name=f"Sudha_Panthi_CV_{current_target.replace(' ', '_')}.pdf",
            mime="application/pdf",
            key="btn_download_cv"
        )

    with tab_cl:
        st.subheader("Cover Letter (Evidence-Based & JD Aligned)")
        st.text_area("Cover Letter Preview:", value=clean_text(data.get("cover_letter", "")), height=460, key="cl_preview_area")
        
        st.write("")
        st.download_button(
            label="📥 Download Cover Letter (PDF)",
            data=st.session_state.cl_pdf_bytes,
            file_name=f"Sudha_Panthi_Cover_Letter_{current_target.replace(' ', '_')}.pdf",
            mime="application/pdf",
            key="btn_download_cl"
        )

    with tab_email:
        st.subheader("Email Template (Formal & Administrative)")
        email_sub = clean_text(data.get("email_subject", f"Application for {current_target} - Sudha Panthi"))
        st.text_input("Subject Line:", value=email_sub, key="email_sub_input")

        email_msg = clean_text(data.get("email_body", ""))
        st.text_area("Email Body:", value=email_msg, height=350, key="email_body_area")
        
        # Dynamic checklist caption reflecting only what was requested
        req_docs = data.get("requested_documents", ["Updated CV (PDF)", "Cover Letter (PDF)"])
        if isinstance(req_docs, str):
            req_docs = [req_docs]
        req_docs = [clean_text(d) for d in req_docs if d]
        if not req_docs:
            req_docs = ["Updated CV (PDF)", "Cover Letter (PDF)"]

        docs_caption = ", ".join(req_docs)
        st.caption(f"📎 **Requested Attachments:** {docs_caption}")
