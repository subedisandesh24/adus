import streamlit as st
from groq import Groq
from PIL import Image
from fpdf import FPDF
import json
import base64
import io
import unicodedata

# -------------------------------------------------------------------------
# 1. Clean Text Function (Eliminates all '???' marks completely)
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

    # Convert characters to closest ASCII and DROP unsupported symbols instead of replacing with '?'
    val = unicodedata.normalize('NFKD', val).encode('ascii', 'ignore').decode('ascii')
    return val.strip()


# -------------------------------------------------------------------------
# 2. PDF Builder (Clean Typography & Bounded Margins)
# -------------------------------------------------------------------------
class CompleteCVPDF(FPDF):
    def __init__(self, doc_type="CV"):
        super().__init__(format="A4", unit="mm")
        self.doc_type = doc_type
        self.set_margins(16, 14, 16)
        self.set_auto_page_break(auto=True, margin=15)

    @property
    def printable_width(self):
        return self.w - self.l_margin - self.r_margin

    def draw_cv_header(self):
        """Header matching Sudha's CV"""
        self.set_y(14)
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(20, 20, 20)
        self.cell(90, 10, "SUDHA PANTHI", align="L")
        
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(60, 60, 60)
        self.set_x(self.w - self.r_margin - 85)
        contact_info = "+977-9860906707\nSudha.panthee@gmail.com\nlinkedin.com/in/sudha-panthi-10aa801b0"
        self.multi_cell(85, 3.8, contact_info, align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def draw_section_heading(self, title):
        """Heading with horizontal line"""
        avail_w = self.printable_width
        self.ln(2)
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(15, 15, 15)
        self.cell(avail_w, 5, clean_text(title), new_x="LMARGIN", new_y="NEXT")
        
        curr_y = self.get_y()
        self.set_draw_color(40, 40, 40)
        self.set_line_width(0.35)
        self.line(self.l_margin, curr_y, self.w - self.r_margin, curr_y)
        self.ln(2.5)

    def draw_org_block(self, org_name, location, role_title, dates, bullets):
        """Organization Block"""
        avail_w = self.printable_width
        col_left = 115
        col_right = avail_w - col_left

        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 9.8)
        self.set_text_color(20, 20, 20)
        self.cell(col_left, 4.5, clean_text(org_name), align="L")
        self.set_font("Helvetica", "", 9)
        self.cell(col_right, 4.5, clean_text(location), align="R", new_x="LMARGIN", new_y="NEXT")

        self.set_x(self.l_margin)
        self.set_font("Helvetica", "I", 9)
        self.cell(col_left, 4.2, clean_text(role_title), align="L")
        self.set_font("Helvetica", "", 9)
        self.cell(col_right, 4.2, clean_text(dates), align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(0.8)

        self.set_font("Helvetica", "", 8.8)
        self.set_text_color(35, 35, 35)
        for bullet in bullets:
            self.set_x(self.l_margin)
            self.multi_cell(avail_w, 4.2, f"-  {clean_text(bullet)}", new_x="LMARGIN", new_y="NEXT")
        self.ln(1.5)

    def draw_two_col_entry(self, left_bold, left_sub, right_txt, right_sub=""):
        """Two-column layout"""
        avail_w = self.printable_width
        col_left = 118
        col_right = avail_w - col_left

        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(20, 20, 20)
        self.cell(col_left, 4.2, clean_text(left_bold), align="L")
        self.set_font("Helvetica", "", 8.8)
        self.cell(col_right, 4.2, clean_text(right_txt), align="R", new_x="LMARGIN", new_y="NEXT")

        if left_sub or right_sub:
            self.set_x(self.l_margin)
            self.set_font("Helvetica", "", 8.5)
            self.set_text_color(50, 50, 50)
            self.cell(col_left, 4.0, clean_text(left_sub), align="L")
            self.cell(col_right, 4.0, clean_text(right_sub), align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def footer(self):
        """Page Footer"""
        self.set_y(-12)
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(90, 90, 90)
        avail_w = self.printable_width
        self.cell(avail_w / 2, 8, "Sudha Panthi - Phone: +977-9860906707 | Email: Sudha.panthee@gmail.com", align="L")
        self.cell(avail_w / 2, 8, f"{self.page_no()} | P a g e", align="R")


# -------------------------------------------------------------------------
# 3. Dynamic Model Selector
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
# 4. Permanent CV Database (Included in every generated CV)
# -------------------------------------------------------------------------
PERMANENT_CV_SECTIONS = {
    "publication": "Impact of Farmers' Marketing Decisions on Profitability in Wheat: A Case Study of Kailali District - American Journal of Applied Statistics and Economics. DOI:10.54536/ajase.v5i2.6848",
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
        {"name": "Bhimsen Chaulagain", "title": "Senior Scientist S2, NARC", "phone": "+977 - 9860906707", "email": "bhimsen.chaulagain@gmail.com"},
        {"name": "Bambie Gordon Panta", "title": "Director, Global Peace Foundation Nepal", "phone": "+977 - 9849043897", "email": "bpanta@globalpeace.org"}
    ]
}

# -------------------------------------------------------------------------
# 5. Streamlit User Interface & Multi-Vacancy Detection
# -------------------------------------------------------------------------
st.set_page_config(page_title="Sudha Panthi - Application Matcher", layout="wide")

st.title("🌱 NGO/INGO Application Generator")
st.caption("⚡ Powered by Groq - Zero '???' errors & auto-vacancy selection")

# Session state initialization
if "detected_positions" not in st.session_state:
    st.session_state.detected_positions = []
if "confirmed_position" not in st.session_state:
    st.session_state.confirmed_position = ""
if "vacancy_content_cache" not in st.session_state:
    st.session_state.vacancy_content_cache = None

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
        placeholder="Paste full job notice, multiple vacancies, or requirements here...",
        height=260
    )
else:
    up_file = st.file_uploader("Upload Vacancy Notice (JPG, PNG)", type=["jpg", "jpeg", "png"])
    if up_file:
        uploaded_image_bytes = up_file.getvalue()
        st.image(uploaded_image_bytes, caption="Uploaded Notice", use_container_width=True)

# Step 1: Detect available positions
has_input = (bool(vacancy_text.strip()) if "Paste" in input_mode else uploaded_image_bytes is not None)

if has_input and api_key:
    col_scan, col_status = st.columns([1, 2])
    with col_scan:
        if st.button("🔍 Step 1: Scan Notice & Detect Positions", type="secondary"):
            with st.spinner("Scanning for positions in vacancy..."):
                try:
                    client = Groq(api_key=api_key)
                    text_model, vision_model = get_groq_active_models(client)

                    scan_prompt = """
                    Scan this job advertisement and list all individual job vacancies/positions available.
                    Return a JSON object matching this structure:
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

# Step 2: Handle single or multiple positions
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

    # Step 3: Generate Application
    if st.button(f"🚀 Generate Application for '{selected_role}'", type="primary"):
        with st.spinner(f"Tailoring CV and Cover Letter for {selected_role}..."):
            try:
                client = Groq(api_key=api_key)
                text_model, vision_model = get_groq_active_models(client)

                full_prompt = f"""
                You are an expert HR recruitment specialist for NGOs/INGOs in Nepal.
                Candidate is SUDHA PANTHI (Phone: +977-9860906707, Email: Sudha.panthee@gmail.com).
                Target Position: {selected_role}

                CRITICAL REQUIREMENTS:
                1. Tailor all documents specifically for the selected role: '{selected_role}'.
                2. Do NOT use fancy quotes or rare unicode symbols. Use simple ASCII characters.
                3. The cover letter MUST explicitly include Sudha's phone number (+977-9860906707) in the opening and closing.
                4. Authentic organization bullets MUST strictly stay with:
                   - Nepal Development Research Institute (Feb-May 2025)
                   - National Agriculture Research Centre (2023-2024)
                   - Global Peace Foundation (June 2023-Feb 2024)
                   - Harihar Women Savings and Loan Cooperatives Limited (April-May 2024)

                Return valid JSON only:
                {{
                    "vacancy_details": {{
                        "job_title": "{selected_role}",
                        "organization": "string"
                    }},
                    "tailored_career_objective": "3-5 lines tailored to {selected_role}",
                    "tailored_skills": {{
                        "computer": "Microsoft Office, Adobe Photoshop, Adobe Illustrator, Arc-GIS, RStudio, GenStat, SPSS, Kobo Toolbox",
                        "languages": "Nepali (Native), English (Fluent)",
                        "targeted_technical_and_soft_skills": "5-8 prioritized competencies"
                    }},
                    "tailored_experience": [
                        {{
                            "organization": "Nepal Development Research Institute",
                            "location": "Sanepa, Lalitpur",
                            "role": "Field Researcher, MATSYA Project (Modernising Aquaculture in Nepal)",
                            "dates": "February-May,2025",
                            "bullets": ["string"]
                        }},
                        {{
                            "organization": "National Agriculture Research Centre, Government of Nepal (Agronomy Division)",
                            "location": "Khumaltar, Lalitpur",
                            "role": "Research Assistant",
                            "dates": "2023-2024",
                            "bullets": ["string"]
                        }},
                        {{
                            "organization": "Global Peace Foundation",
                            "location": "Nepal",
                            "role": "Fellowship, Global Peacebuilders Leadership Program",
                            "dates": "June 2023-February 2024",
                            "bullets": ["string"]
                        }},
                        {{
                            "organization": "Harihar Women Savings and Loan Cooperatives Limited",
                            "location": "Pokhara, Nepal",
                            "role": "Trainer",
                            "dates": "April 29-May 5,2024",
                            "bullets": ["string"]
                        }}
                    ],
                    "cover_letter": "Complete professional 1-page cover letter. Include Sudha's contact info (+977-9860906707) and end formally."
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

                # Normalize fields
                if isinstance(data.get("tailored_career_objective"), list):
                    data["tailored_career_objective"] = " ".join(str(x) for x in data["tailored_career_objective"])
                if isinstance(data.get("cover_letter"), list):
                    data["cover_letter"] = "\n\n".join(str(x) for x in data["cover_letter"])

                skills_dict = data.get("tailored_skills", {})
                for k in ["computer", "languages", "targeted_technical_and_soft_skills"]:
                    if isinstance(skills_dict.get(k), list):
                        skills_dict[k] = ", ".join(str(x) for x in skills_dict[k])

                avail_w = 210 - 16 - 16

                # -------------------------------------------------------------
                # BUILD FULL CV PDF
                # -------------------------------------------------------------
                cv_pdf = CompleteCVPDF(doc_type="CV")
                cv_pdf.add_page()
                cv_pdf.draw_cv_header()
                
                # 1. Career Objective
                cv_pdf.draw_section_heading("Career Objective")
                cv_pdf.set_x(cv_pdf.l_margin)
                cv_pdf.set_font("Helvetica", "", 9)
                cv_pdf.set_text_color(30, 30, 30)
                cv_pdf.multi_cell(avail_w, 4.3, clean_text(data.get("tailored_career_objective", "")), new_x="LMARGIN", new_y="NEXT")
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

                # 3. Publication
                cv_pdf.draw_section_heading("Publication")
                cv_pdf.set_x(cv_pdf.l_margin)
                cv_pdf.set_font("Helvetica", "", 8.8)
                cv_pdf.multi_cell(avail_w, 4.2, clean_text(PERMANENT_CV_SECTIONS["publication"]), new_x="LMARGIN", new_y="NEXT")
                cv_pdf.ln(1)

                # 4. Projects
                cv_pdf.draw_section_heading("Projects")
                cv_pdf.set_font("Helvetica", "", 8.8)
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
                    cv_pdf.set_font("Helvetica", "B", 9.2)
                    cv_pdf.cell(115, 4.5, clean_text(lead["org"]), align="L")
                    cv_pdf.set_font("Helvetica", "", 8.8)
                    cv_pdf.cell(avail_w - 115, 4.5, clean_text(lead["loc"]), align="R", new_x="LMARGIN", new_y="NEXT")
                    for r_title, r_desc in lead["roles"]:
                        cv_pdf.set_x(cv_pdf.l_margin)
                        cv_pdf.set_font("Helvetica", "I", 8.8)
                        cv_pdf.cell(avail_w, 4.0, clean_text(r_title), new_x="LMARGIN", new_y="NEXT")
                        cv_pdf.set_x(cv_pdf.l_margin)
                        cv_pdf.set_font("Helvetica", "", 8.6)
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
                cv_pdf.set_font("Helvetica", "B", 8.8)
                cv_pdf.write(4.2, "Computer: ")
                cv_pdf.set_font("Helvetica", "", 8.8)
                cv_pdf.write(4.2, f"{clean_text(skills_dict.get('computer', ''))}\n")
                cv_pdf.ln(1)

                cv_pdf.set_x(cv_pdf.l_margin)
                cv_pdf.set_font("Helvetica", "B", 8.8)
                cv_pdf.write(4.2, "Language: ")
                cv_pdf.set_font("Helvetica", "", 8.8)
                cv_pdf.write(4.2, f"{clean_text(skills_dict.get('languages', ''))}\n")
                cv_pdf.ln(1)

                cv_pdf.set_x(cv_pdf.l_margin)
                cv_pdf.set_font("Helvetica", "B", 8.8)
                cv_pdf.write(4.2, "Vacancy Skills: ")
                cv_pdf.set_font("Helvetica", "", 8.8)
                cv_pdf.write(4.2, f"{clean_text(skills_dict.get('targeted_technical_and_soft_skills', ''))}\n")
                cv_pdf.ln(1)

                # 10. Referees
                cv_pdf.draw_section_heading("Referees")
                for ref in PERMANENT_CV_SECTIONS["referees"]:
                    cv_pdf.set_x(cv_pdf.l_margin)
                    cv_pdf.set_font("Helvetica", "B", 9)
                    cv_pdf.cell(70, 4, clean_text(ref["name"]), align="L")
                    cv_pdf.set_font("Helvetica", "", 8.8)
                    cv_pdf.cell(avail_w - 70, 4, f"{clean_text(ref['phone'])} | {clean_text(ref['email'])}", align="R", new_x="LMARGIN", new_y="NEXT")
                    cv_pdf.set_x(cv_pdf.l_margin)
                    cv_pdf.set_font("Helvetica", "I", 8.5)
                    cv_pdf.cell(avail_w, 3.8, clean_text(ref["title"]), new_x="LMARGIN", new_y="NEXT")
                    cv_pdf.ln(1.5)

                cv_buf = io.BytesIO()
                cv_pdf.output(cv_buf)
                cv_pdf_data = cv_buf.getvalue()

                # -------------------------------------------------------------
                # BUILD COVER LETTER PDF (Includes Phone Number)
                # -------------------------------------------------------------
                cl_pdf = CompleteCVPDF(doc_type="Cover Letter")
                cl_pdf.add_page()
                cl_pdf.draw_cv_header()
                cl_pdf.draw_section_heading(f"Application for {selected_role}")
                
                cl_pdf.set_x(cl_pdf.l_margin)
                cl_pdf.set_font("Helvetica", "", 9.5)
                cl_pdf.set_text_color(30, 30, 30)
                cl_pdf.multi_cell(avail_w, 4.8, clean_text(data.get("cover_letter", "")), new_x="LMARGIN", new_y="NEXT")
                
                cl_buf = io.BytesIO()
                cl_pdf.output(cl_buf)
                cl_pdf_data = cl_buf.getvalue()

                # -------------------------------------------------------------
                # UI Results
                # -------------------------------------------------------------
                st.success(f"Tailored application generated for '{selected_role}'!")

                tab_rev, tab_cl = st.tabs(["📄 Tailored CV", "✉️ Cover Letter (with Phone Number)"])

                with tab_rev:
                    st.markdown("### Adapted Career Objective")
                    st.info(clean_text(data.get("tailored_career_objective", "")))

                    st.markdown("### Targeted Work Experience (By Organization)")
                    for org in data.get("tailored_experience", []):
                        with st.expander(f"📍 {clean_text(org.get('organization', ''))} — {clean_text(org.get('role', ''))}"):
                            for b in org.get("bullets", []):
                                st.write(f"• {clean_text(b)}")

                    st.download_button(
                        label="📥 Download Complete Tailored CV (PDF)",
                        data=cv_pdf_data,
                        file_name=f"Sudha_Panthi_CV_{selected_role.replace(' ', '_')}.pdf",
                        mime="application/pdf"
                    )

                with tab_cl:
                    st.subheader("Formal Cover Letter")
                    st.text_area("Cover Letter Preview:", value=clean_text(data.get("cover_letter", "")), height=320)
                    st.download_button(
                        label="📥 Download Cover Letter (PDF)",
                        data=cl_pdf_data,
                        file_name=f"Sudha_Panthi_Cover_Letter_{selected_role.replace(' ', '_')}.pdf",
                        mime="application/pdf"
                    )

            except Exception as e:
                st.error(f"Generation error: {e}")
