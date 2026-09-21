import streamlit as st
from groq import Groq
from PIL import Image
from fpdf import FPDF
import json
import base64
import io

# -------------------------------------------------------------------------
# 1. Styled PDF Builder (Replicating Sudha's Exact 3-Page CV Layout)
# -------------------------------------------------------------------------
class CompleteCVPDF(FPDF):
    def __init__(self, doc_type="CV"):
        super().__init__(format="A4", unit="mm")
        self.doc_type = doc_type
        self.set_margins(16, 14, 16)
        self.set_auto_page_break(auto=True, margin=15)

    def draw_cv_header(self):
        """Header matching Page 1 of Sudha's CV"""
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(20, 20, 20)
        self.cell(100, 8, "SUDHA PANTHI", ln=False)
        
        self.set_font("Helvetica", "", 9)
        self.set_text_color(60, 60, 60)
        contact_x = 120
        self.set_x(contact_x)
        self.cell(0, 4, "+977-9860906707", ln=True, align="R")
        self.set_x(contact_x)
        self.cell(0, 4, "Sudha.panthee@gmail.com", ln=True, align="R")
        self.set_x(contact_x)
        self.cell(0, 4, "linkedin.com/in/sudha-panthi-10aa801b0", ln=True, align="R")
        self.ln(4)

    def draw_section_heading(self, title):
        """Heading with horizontal divider line"""
        self.ln(2.5)
        self.set_font("Helvetica", "B", 11.5)
        self.set_text_color(15, 15, 15)
        self.cell(0, 5, title, ln=True)
        
        curr_y = self.get_y()
        self.set_draw_color(40, 40, 40)
        self.set_line_width(0.35)
        self.line(self.l_margin, curr_y, self.w - self.r_margin, curr_y)
        self.ln(2.5)

    def draw_org_block(self, org_name, location, role_title, dates, bullets):
        """Organization Block (Org/Location + Role/Dates + Hyphen Bullets)"""
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(20, 20, 20)
        self.cell(115, 4.5, org_name, ln=False)
        self.set_font("Helvetica", "", 9)
        self.cell(0, 4.5, location, ln=True, align="R")

        self.set_font("Helvetica", "I", 9)
        self.cell(115, 4.5, role_title, ln=False)
        self.set_font("Helvetica", "", 9)
        self.cell(0, 4.5, dates, ln=True, align="R")
        self.ln(0.8)

        self.set_font("Helvetica", "", 8.8)
        self.set_text_color(35, 35, 35)
        for bullet in bullets:
            self.set_x(self.l_margin)
            self.cell(4, 4.2, "-", ln=False)
            self.multi_cell(0, 4.2, f" {bullet}")
        self.ln(1.8)

    def draw_two_col_entry(self, left_bold, left_sub, right_txt, right_sub=""):
        """Two-column layout for Education, Leadership, Workshops, etc."""
        self.set_font("Helvetica", "B", 9.5)
        self.set_text_color(20, 20, 20)
        self.cell(120, 4.2, left_bold, ln=False)
        self.set_font("Helvetica", "", 9)
        self.cell(0, 4.2, right_txt, ln=True, align="R")

        if left_sub or right_sub:
            self.set_font("Helvetica", "", 8.8)
            self.set_text_color(50, 50, 50)
            self.cell(120, 4.2, left_sub, ln=False)
            self.cell(0, 4.2, right_sub, ln=True, align="R")
        self.ln(1)

    def footer(self):
        """Page Footer: Sudha Panthi - Email: ... | X | P a g e"""
        self.set_y(-12)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(90, 90, 90)
        self.cell(100, 8, "Sudha Panthi - Email: Sudha.panthee@gmail.com", ln=False, align="L")
        self.cell(0, 8, f"{self.page_no()} | P a g e", ln=False, align="R")


def clean_text(txt):
    """Sanitizes unicode to Latin-1 compatible characters for standard PDF fonts"""
    if not txt:
        return ""
    replacements = {
        "’": "'", "‘": "'", "“": '"', "”": '"', 
        "–": "-", "—": "-", "…": "...", "•": "-"
    }
    for k, v in replacements.items():
        txt = txt.replace(k, v)
    return txt.encode("latin-1", "replace").decode("latin-1")


# -------------------------------------------------------------------------
# 2. Permanent CV Database (Included in every generated CV)
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
        {"inst": "Tribhuvan University, Institute of Agriculture and Animal Science", "deg": "Bachelors of Science in Agriculture * Percentage: 75.38% (IDF Scholarship)", "loc": "Lamjung, Nepal", "yr": "2020-2024"},
        {"inst": "St. Xavier's College", "deg": "High School * GPA: 3.22", "loc": "Maitighar, Kathmandu", "yr": "2016-2018"},
        {"inst": "SOS Hermann Gmeiner School", "deg": "Higher Secondary * GPA: 3.8", "loc": "Sanothimi, Bhaktapur", "yr": "2016"}
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
# 3. Streamlit Interface & Groq Execution
# -------------------------------------------------------------------------
st.set_page_config(page_title="Sudha Panthi - Application Matcher", layout="wide")

st.title("🌱 NGO/INGO Application Generator")
st.caption("⚡ Powered by Groq (14,400 free requests/day)")

# Retrieve API Key from Secrets or Sidebar
raw_key = st.secrets.get("GROQ_API_KEY", None)
if not raw_key:
    raw_key = st.sidebar.text_input("Groq API Key (starts with gsk_):", type="password")
    st.sidebar.caption("Get a free key from console.groq.com/keys")

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

col_in, col_btn = st.columns([1.2, 1.8])
with col_in:
    if "Paste" in input_mode:
        vacancy_text = st.text_area(
            "Paste Job Vacancy / TOR text here:",
            placeholder="Paste Job Title, Organization, Duties, and Requirements here...",
            height=300
        )
    else:
        up_file = st.file_uploader("Upload Vacancy Notice (JPG, PNG)", type=["jpg", "jpeg", "png"])
        if up_file:
            uploaded_image_bytes = up_file.getvalue()
            st.image(uploaded_image_bytes, caption="Uploaded Notice", use_container_width=True)

with col_btn:
    has_input = (bool(vacancy_text.strip()) if "Paste" in input_mode else uploaded_image_bytes is not None)
    
    if st.button("Generate Complete Tailored Application", type="primary", disabled=not has_input):
        if not api_key:
            st.warning("Please provide your Groq API key (starts with gsk_) to proceed.")
        else:
            with st.spinner("Connecting to Groq and generating your application..."):
                try:
                    client = Groq(api_key=api_key)

                    system_prompt = """
                    You are an expert HR recruitment specialist for national and international NGOs in Nepal.
                    Tailor Sudha Panthi's application documents based on the provided vacancy.

                    CRITICAL CONSTRAINTS:
                    1. Work experience bullets MUST strictly remain under their authentic organizations:
                       - Nepal Development Research Institute (Feb-May 2025)
                       - National Agriculture Research Centre (2023-2024)
                       - Global Peace Foundation (June 2023-Feb 2024)
                       - Harihar Women Savings and Loan Cooperatives Limited (April-May 2024)
                    2. Do NOT invent duties or swap them between organizations.
                    3. Output MUST be valid JSON only.

                    JSON Structure:
                    {
                        "vacancy_details": {
                            "job_title": "string",
                            "organization": "string"
                        },
                        "tailored_career_objective": "3-5 lines aligned to vacancy keywords",
                        "tailored_skills": {
                            "computer": "Microsoft Office, Adobe Photoshop, Adobe Illustrator, Arc-GIS, RStudio, GenStat, SPSS, Kobo Toolbox",
                            "languages": "Nepali (Native), English (Fluent)",
                            "targeted_technical_and_soft_skills": "5-8 prioritized competencies"
                        },
                        "tailored_experience": [
                            {
                                "organization": "Nepal Development Research Institute",
                                "location": "Sanepa, Lalitpur",
                                "role": "Field Researcher, MATSYA Project (Modernising Aquaculture in Nepal)",
                                "dates": "February-May,2025",
                                "bullets": ["string"]
                            },
                            {
                                "organization": "National Agriculture Research Centre, Government of Nepal (Agronomy Division)",
                                "location": "Khumaltar, Lalitpur",
                                "role": "Research Assistant",
                                "dates": "2023-2024",
                                "bullets": ["string"]
                            },
                            {
                                "organization": "Global Peace Foundation",
                                "location": "Nepal",
                                "role": "Fellowship, Global Peacebuilders Leadership Program",
                                "dates": "June 2023-February 2024",
                                "bullets": ["string"]
                            },
                            {
                                "organization": "Harihar Women Savings and Loan Cooperatives Limited",
                                "location": "Pokhara, Nepal",
                                "role": "Trainer",
                                "dates": "April 29-May 5,2024",
                                "bullets": ["string"]
                            }
                        ],
                        "cover_letter": "Complete professional 1-page cover letter formally addressed to the hiring committee"
                    }
                    """

                    if "Paste" in input_mode:
                        selected_model = "llama-3.3-70b-versatile"
                        messages = [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"VACANCY TEXT:\n{vacancy_text}"}
                        ]
                    else:
                        selected_model = "llama-3.2-11b-vision-preview"
                        base64_image = base64.b64encode(uploaded_image_bytes).decode("utf-8")
                        messages = [
                            {"role": "system", "content": system_prompt},
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Analyze this vacancy image and return JSON:"},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                                ]
                            }
                        ]

                    response = client.chat.completions.create(
                        model=selected_model,
                        messages=messages,
                        response_format={"type": "json_object"},
                        temperature=0.2
                    )

                    raw_json = response.choices[0].message.content.strip()
                    data = json.loads(raw_json)

                    # -------------------------------------------------------------
                    # BUILD FULL CV PDF (All Sections Included)
                    # -------------------------------------------------------------
                    cv_pdf = CompleteCVPDF(doc_type="CV")
                    cv_pdf.add_page()
                    cv_pdf.draw_cv_header()
                    
                    # 1. Career Objective
                    cv_pdf.draw_section_heading("Career Objective")
                    cv_pdf.set_font("Helvetica", "", 9)
                    cv_pdf.set_text_color(30, 30, 30)
                    cv_pdf.multi_cell(0, 4.3, clean_text(data["tailored_career_objective"]))
                    cv_pdf.ln(1)

                    # 2. Experience
                    cv_pdf.draw_section_heading("Experience")
                    for org in data["tailored_experience"]:
                        if org.get("bullets"):
                            cv_pdf.draw_org_block(
                                clean_text(org["organization"]),
                                clean_text(org["location"]),
                                clean_text(org["role"]),
                                clean_text(org["dates"]),
                                [clean_text(b) for b in org["bullets"]]
                            )

                    # 3. Publication
                    cv_pdf.draw_section_heading("Publication")
                    cv_pdf.set_font("Helvetica", "", 8.8)
                    cv_pdf.multi_cell(0, 4.2, clean_text(PERMANENT_CV_SECTIONS["publication"]))
                    cv_pdf.ln(1)

                    # 4. Projects
                    cv_pdf.draw_section_heading("Projects")
                    cv_pdf.set_font("Helvetica", "", 8.8)
                    for proj in PERMANENT_CV_SECTIONS["projects"]:
                        cv_pdf.cell(4, 4.2, "-", ln=False)
                        cv_pdf.multi_cell(0, 4.2, f" {clean_text(proj)}")
                    cv_pdf.ln(1)

                    # 5. Education
                    cv_pdf.draw_section_heading("Education")
                    for edu in PERMANENT_CV_SECTIONS["education"]:
                        cv_pdf.draw_two_col_entry(
                            clean_text(edu["inst"]),
                            clean_text(edu["deg"]),
                            clean_text(edu["loc"]),
                            clean_text(edu["yr"])
                        )

                    # 6. Leadership Activities
                    cv_pdf.draw_section_heading("Leadership Activities")
                    for lead in PERMANENT_CV_SECTIONS["leadership"]:
                        cv_pdf.set_font("Helvetica", "B", 9.5)
                        cv_pdf.cell(120, 4.5, clean_text(lead["org"]), ln=False)
                        cv_pdf.set_font("Helvetica", "", 9)
                        cv_pdf.cell(0, 4.5, clean_text(lead["loc"]), ln=True, align="R")
                        for r_title, r_desc in lead["roles"]:
                            cv_pdf.set_font("Helvetica", "I", 8.8)
                            cv_pdf.cell(0, 4, clean_text(r_title), ln=True)
                            cv_pdf.set_font("Helvetica", "", 8.6)
                            cv_pdf.multi_cell(0, 4, f"  {clean_text(r_desc)}")
                        cv_pdf.ln(1)

                    # 7. Trainings and Workshops
                    cv_pdf.draw_section_heading("Trainings and Workshops")
                    for tr_title, tr_org in PERMANENT_CV_SECTIONS["trainings"]:
                        cv_pdf.draw_two_col_entry(clean_text(tr_title), "", clean_text(tr_org), "")

                    # 8. Volunteering
                    cv_pdf.draw_section_heading("Volunteering")
                    for vol_title, vol_org in PERMANENT_CV_SECTIONS["volunteering"]:
                        cv_pdf.draw_two_col_entry(clean_text(vol_title), "", clean_text(vol_org), "")

                    # 9. Skills
                    cv_pdf.draw_section_heading("Skills")
                    cv_pdf.set_font("Helvetica", "B", 8.8)
                    cv_pdf.cell(28, 4.2, "Computer:", ln=False)
                    cv_pdf.set_font("Helvetica", "", 8.8)
                    cv_pdf.multi_cell(0, 4.2, clean_text(data["tailored_skills"]["computer"]))

                    cv_pdf.set_font("Helvetica", "B", 8.8)
                    cv_pdf.cell(28, 4.2, "Language:", ln=False)
                    cv_pdf.set_font("Helvetica", "", 8.8)
                    cv_pdf.multi_cell(0, 4.2, clean_text(data["tailored_skills"]["languages"]))

                    cv_pdf.set_font("Helvetica", "B", 8.8)
                    cv_pdf.cell(28, 4.2, "Vacancy Skills:", ln=False)
                    cv_pdf.set_font("Helvetica", "", 8.8)
                    cv_pdf.multi_cell(0, 4.2, clean_text(data["tailored_skills"]["targeted_technical_and_soft_skills"]))
                    cv_pdf.ln(1)

                    # 10. Referees
                    cv_pdf.draw_section_heading("Referees")
                    for ref in PERMANENT_CV_SECTIONS["referees"]:
                        cv_pdf.set_font("Helvetica", "B", 9)
                        cv_pdf.cell(70, 4, clean_text(ref["name"]), ln=False)
                        cv_pdf.set_font("Helvetica", "", 8.8)
                        cv_pdf.cell(0, 4, f"{clean_text(ref['phone'])} | {clean_text(ref['email'])}", ln=True)
                        cv_pdf.set_font("Helvetica", "I", 8.5)
                        cv_pdf.cell(0, 3.8, clean_text(ref["title"]), ln=True)
                        cv_pdf.ln(1.5)

                    cv_buf = io.BytesIO()
                    cv_pdf.output(cv_buf)
                    cv_pdf_data = cv_buf.getvalue()

                    # -------------------------------------------------------------
                    # BUILD COVER LETTER PDF
                    # -------------------------------------------------------------
                    cl_pdf = CompleteCVPDF(doc_type="Cover Letter")
                    cl_pdf.add_page()
                    cl_pdf.draw_cv_header()
                    cl_pdf.draw_section_heading(f"Application for {clean_text(data['vacancy_details']['job_title'])}")
                    cl_pdf.set_font("Helvetica", "", 9.5)
                    cl_pdf.set_text_color(30, 30, 30)
                    cl_pdf.multi_cell(0, 4.8, clean_text(data["cover_letter"]))
                    
                    cl_buf = io.BytesIO()
                    cl_pdf.output(cl_buf)
                    cl_pdf_data = cl_buf.getvalue()

                    # -------------------------------------------------------------
                    # UI Review & Showcase
                    # -------------------------------------------------------------
                    st.success(f"Tailored via Groq ({selected_model}) for: {data['vacancy_details']['job_title']} at {data['vacancy_details']['organization']}")

                    tab_review, tab_cl, tab_cv_preview = st.tabs([
                        "🔍 Review Work Done (Tailored Sections)", 
                        "✉️ Cover Letter", 
                        "📄 Full CV Details"
                    ])

                    with tab_review:
                        st.markdown("### 1. Adapted Career Objective")
                        st.info(data["tailored_career_objective"])

                        st.markdown("### 2. Vacancy-Targeted Skills")
                        col_s1, col_s2 = st.columns(2)
                        with col_s1:
                            st.write(f"**Software / Tools:** {data['tailored_skills']['computer']}")
                            st.write(f"**Languages:** {data['tailored_skills']['languages']}")
                        with col_s2:
                            st.write(f"**Prioritized Competencies:** {data['tailored_skills']['targeted_technical_and_soft_skills']}")

                        st.markdown("### 3. Tailored Experience Bullets (By Organization)")
                        for org in data["tailored_experience"]:
                            with st.expander(f"📍 {org['organization']} — {org['role']}"):
                                for b in org["bullets"]:
                                    st.write(f"• {b}")

                        st.download_button(
                            label="📥 Download Complete Tailored CV (PDF)",
                            data=cv_pdf_data,
                            file_name=f"Sudha_Panthi_Complete_CV_{data['vacancy_details']['job_title'].replace(' ', '_')}.pdf",
                            mime="application/pdf"
                        )

                    with tab_cl:
                        st.subheader("Formal Cover Letter")
                        st.text_area("Cover Letter Preview:", value=data["cover_letter"], height=300)
                        st.download_button(
                            label="📥 Download Cover Letter (PDF)",
                            data=cl_pdf_data,
                            file_name=f"Sudha_Panthi_Cover_Letter_{data['vacancy_details']['job_title'].replace(' ', '_')}.pdf",
                            mime="application/pdf"
                        )

                    with tab_cv_preview:
                        st.markdown("#### Permanent Sections Included in the Output PDF:")
                        st.write("✔️ **Publication:** American Journal of Applied Statistics and Economics (DOI: 10.54536/ajase.v5i2.6848)")
                        st.write("✔️ **6 Research & Field Projects**")
                        st.write("✔️ **Full Education History** (IAAS TU M.Sc., B.Sc., St. Xavier's, SOS Hermann Gmeiner)")
                        st.write("✔️ **Leadership Roles** (TSAN Lamjung Campus & SOS'ian Club)")
                        st.write("✔️ **13 Trainings & Workshops** (CARITAS, FAO, Power Shift Nepal, etc.)")
                        st.write("✔️ **5 Volunteering Records**")
                        st.write("✔️ **3 Referees** (Dr. Mahesh Jaisi, Bhimsen Chaulagain, Bambie Gordon Panta)")

                except Exception as e:
                    st.error(f"Error processing document: {e}")
