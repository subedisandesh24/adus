import streamlit as st
import google.generativeai as genai
from PIL import Image
from fpdf import FPDF
import json
import io

# -------------------------------------------------------------------------
# 1. Custom PDF Engine (Matches Sudha's Original CV Styling Exactly)
# -------------------------------------------------------------------------
class StyledCVPDF(FPDF):
    def __init__(self, doc_type="CV"):
        super().__init__(format="A4", unit="mm")
        self.doc_type = doc_type
        self.set_margins(18, 16, 18)

    def draw_cv_header(self):
        """Header matching page 1 of your CV"""
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(20, 20, 20)
        
        # Candidate Name on Left
        self.cell(100, 10, "SUDHA PANTHI", ln=False)
        
        # Contact Details on Right
        self.set_font("Helvetica", "", 9)
        self.set_text_color(50, 50, 50)
        contact_x = 120
        self.set_x(contact_x)
        self.cell(0, 4, "+977-9860906707", ln=True, align="R")
        self.set_x(contact_x)
        self.cell(0, 4, "Sudha.panthee@gmail.com", ln=True, align="R")
        self.set_x(contact_x)
        self.cell(0, 4, "linkedin.com/in/sudha-panthi-10aa801b0", ln=True, align="R")
        self.ln(6)

    def draw_section_heading(self, title):
        """Section title with horizontal divider matching CV style"""
        self.ln(3)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(15, 15, 15)
        self.cell(0, 6, title, ln=True)
        # Black divider line spanning full width
        curr_y = self.get_y()
        self.set_draw_color(30, 30, 30)
        self.set_line_width(0.4)
        self.line(self.l_margin, curr_y, self.w - self.r_margin, curr_y)
        self.ln(3)

    def draw_org_block(self, org_name, location, role_title, dates, bullets):
        """Organization Block (Org & Location on Top, Role & Dates Below)"""
        # Line 1: Organization (Bold Left) | Location (Right)
        self.set_font("Helvetica", "B", 10.5)
        self.set_text_color(20, 20, 20)
        self.cell(115, 5, org_name, ln=False)
        self.set_font("Helvetica", "", 9.5)
        self.cell(0, 5, location, ln=True, align="R")

        # Line 2: Role / Project (Italic/Regular Left) | Dates (Right)
        self.set_font("Helvetica", "I", 9.5)
        self.cell(115, 5, role_title, ln=False)
        self.set_font("Helvetica", "", 9.5)
        self.cell(0, 5, dates, ln=True, align="R")
        self.ln(1)

        # Line 3: Bullet points with standard indentation
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(35, 35, 35)
        for bullet in bullets:
            self.set_x(self.l_margin)
            self.cell(4, 4.5, "-", ln=False)
            self.multi_cell(0, 4.5, f" {bullet}")
        self.ln(2.5)

    def footer(self):
        """Footer matching 'Sudha Panthi - Email: Sudha.panthee@gmail.com  X | P a g e'"""
        self.set_y(-12)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(80, 80, 80)
        
        # Left footer
        self.cell(100, 8, "Sudha Panthi - Email: Sudha.panthee@gmail.com", ln=False, align="L")
        # Right footer
        self.cell(0, 8, f"{self.page_no()} | P a g e", ln=False, align="R")


def clean_text(txt):
    """Sanitize typography for standard PDF font rendering"""
    replacements = {
        "’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "..."
    }
    for k, v in replacements.items():
        txt = txt.replace(k, v)
    return txt.encode("latin-1", "replace").decode("latin-1")


# -------------------------------------------------------------------------
# 2. Sudha Panthi's Exact Resume Knowledge Base
# -------------------------------------------------------------------------
CANDIDATE_PROFILE = """
CANDIDATE: SUDHA PANTHI
Contact: Sudha.panthee@gmail.com | 977-9860906707 | Lalitpur/Kathmandu, Nepal
LinkedIn: linkedin.com/in/sudha-panthi-10aa801b0

AUTHENTIC WORK EXPERIENCE (DO NOT ALTER OR SHIFT BETWEEN ORGANIZATIONS):
1. Organization: Nepal Development Research Institute
   Location: Sanepa, Lalitpur
   Role: Field Researcher, MATSYA Project (Modernising Aquaculture in Nepal)
   Dates: February-May,2025
   Authentic Duties:
   - Performed Key Informant Interviews (KII) with fish farmers, traders, officers, breeders and other stakeholders related to fishery.
   - Facilitated Focus Group Discussions (FGDs) to assess challenges and opportunities in the fisheries sector.
   - Conducted door-to-door visits to collect data on fisheries and aquaculture practices using structured close and open-ended questionnaires.
   - Transcribed the interviews to prepare a report.
   - Collected and managed survey data using Kobo Toolbox.

2. Organization: National Agriculture Research Centre, Government of Nepal (Agronomy Division)
   Location: Khumaltar, Lalitpur
   Role: Research Assistant
   Dates: 2023-2024
   Authentic Duties:
   - Provided guidance to Junior Technical Assistants (JTA) on field activities.
   - Conducted regular meetings with the supervisor to report on wheat research progress.
   - Designed and executed experiment on pipeline variety of wheat.
   - Collected data from the field, laboratory and literature.
   - Recorded, analysed, and interpreted agronomic data.
   - Prepared research reports based on field observations and data analysis.

3. Organization: Global Peace Foundation
   Location: Nepal
   Role: Fellowship, Global Peacebuilders Leadership Program
   Dates: June 2023-February 2024
   Authentic Duties:
   - Identified community needs through priority matrix, preference ranking, and log frame to design targeted training programs.
   - Organized and implemented a moral and innovative leadership training program in a school in Lamjung, benefiting 70 participants.
   - Facilitated Capacity Building of Peacebuilders on 'Achieving Food Security by Reducing Food Waste.'
   - Conducted training on menstrual hygiene and sustainable environment practices at SOS Hermann Gmeiner School, benefiting 75 students.
   - Implemented the project 'Building a Path for Organic Community' by providing training on efficient water management systems, insect pest control using the Integrated Pest Management (IPM) approach, nursery bed preparation, and preparation of jhol mol (liquid fertilizer) in a remote village of Tanahu, benefiting 36 local people.

4. Organization: Harihar Women Savings and Loan Cooperatives Limited
   Location: Pokhara, Nepal
   Role: Trainer
   Dates: April 29-May 5,2024
   Authentic Duties:
   - Delivered 7 days training on off season vegetable cultivation, and pest and insect management
   - Specific crop-based practical demonstration on management practices

EDUCATION:
- M.Sc. in Agriculture (2025-Present), IAAS, Tribhuvan University
- B.Sc. in Agriculture (2020-2024), IAAS, Tribhuvan University (Percentage: 75.38%, IDF Scholarship)

SKILLS:
- Tools: Kobo Toolbox, Arc-GIS, RStudio, GenStat, SPSS, Microsoft Office
- Competencies: Field surveys, FGD/KII facilitation, IPM, GESI, Community Training, Agronomic trials
"""

# -------------------------------------------------------------------------
# 3. Streamlit Application
# -------------------------------------------------------------------------
st.set_page_config(page_title="Sudha Panthi - Vacancy Matcher", layout="wide")
st.title("🎯 NGO/INGO Vacancy Application Matcher")
st.write("Upload a vacancy announcement. Generates a tailored Cover Letter and a CV matching your exact document layout.")

api_key = st.sidebar.text_input("Gemini API Key:", type="password")
st.sidebar.caption("Get an API key from [Google AI Studio](https://aistudio.google.com/)")

uploaded_file = st.file_uploader("Upload Vacancy Notice Image (JPG, PNG)", type=["jpg", "jpeg", "png"])

if uploaded_file and api_key:
    genai.configure(api_key=api_key)
    image = Image.open(uploaded_file)

    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(image, caption="Uploaded Vacancy Notice", use_container_width=True)

    with col2:
        if st.button("Generate Tailored Application", type="primary"):
            with st.spinner("Analyzing vacancy notice and matching your profile..."):
                try:
                    model = genai.GenerativeModel("gemini-1.5-flash", generation_config={"response_mime_type": "application/json"})

                    prompt = f"""
                    You are an expert HR recruiter for international NGOs (UN, USAID, FCDO, CARE, Save the Children) in Nepal.
                    Analyze this job vacancy image and tailor Sudha Panthi's application.
                    
                    Return a JSON object with this EXACT structure:
                    {{
                        "vacancy_details": {{
                            "job_title": "string",
                            "organization": "string"
                        }},
                        "tailored_career_objective": "A 3-5 line customized career objective tailored specifically to the themes, requirements, and keywords of this vacancy (e.g. food security, survey research, climate resilience, community training), written in the original CV's voice.",
                        "tailored_experience": [
                            {{
                                "organization": "Nepal Development Research Institute",
                                "location": "Sanepa, Lalitpur",
                                "role": "Field Researcher, MATSYA Project (Modernising Aquaculture in Nepal)",
                                "dates": "February-May,2025",
                                "bullets": ["List of relevant bullets for this role matching the vacancy keywords"]
                            }},
                            {{
                                "organization": "National Agriculture Research Centre, Government of Nepal (Agronomy Division)",
                                "location": "Khumaltar, Lalitpur",
                                "role": "Research Assistant",
                                "dates": "2023-2024",
                                "bullets": ["List of relevant bullets for this role"]
                            }},
                            {{
                                "organization": "Global Peace Foundation",
                                "location": "Nepal",
                                "role": "Fellowship, Global Peacebuilders Leadership Program",
                                "dates": "June 2023-February 2024",
                                "bullets": ["List of relevant bullets for this role"]
                            }},
                            {{
                                "organization": "Harihar Women Savings and Loan Cooperatives Limited",
                                "location": "Pokhara, Nepal",
                                "role": "Trainer",
                                "dates": "April 29-May 5,2024",
                                "bullets": ["List of relevant bullets for this role"]
                            }}
                        ],
                        "cover_letter": "Complete professional 1-page cover letter formally addressed to the organization, referencing the specific vacancy, connecting her actual work at NDRI, NARC, and Global Peace Foundation directly to the required responsibilities."
                    }}

                    CRITICAL CONSTRAINTS:
                    1. The work experience bullets MUST be strictly grounded in her authentic duties. DO NOT invent duties or swap them between organizations.
                    2. Tone must be professional, evidence-backed, and aligned with standard INGO recruitment expectations in Nepal.

                    CANDIDATE PROFILE:
                    {CANDIDATE_PROFILE}
                    """

                    response = model.generate_content([prompt, image])
                    data = json.loads(response.text)

                    # -----------------------------------------------------
                    # Build PDF 1: Tailored CV Section (Exact Matching Style)
                    # -----------------------------------------------------
                    cv_pdf = StyledCVPDF(doc_type="CV")
                    cv_pdf.add_page()
                    cv_pdf.draw_cv_header()
                    
                    # Career Objective
                    cv_pdf.draw_section_heading("Career Objective")
                    cv_pdf.set_font("Helvetica", "", 9.5)
                    cv_pdf.set_text_color(30, 30, 30)
                    cv_pdf.multi_cell(0, 4.5, clean_text(data["tailored_career_objective"]))
                    cv_pdf.ln(2)

                    # Experience
                    cv_pdf.draw_section_heading("Experience")
                    for org in data["tailored_experience"]:
                        if org["bullets"]:
                            cv_pdf.draw_org_block(
                                clean_text(org["organization"]),
                                clean_text(org["location"]),
                                clean_text(org["role"]),
                                clean_text(org["dates"]),
                                [clean_text(b) for b in org["bullets"]]
                            )
                    
                    cv_pdf_bytes = io.BytesIO()
                    cv_pdf.output(cv_pdf_bytes)
                    cv_pdf_data = cv_pdf_bytes.getvalue()

                    # -----------------------------------------------------
                    # Build PDF 2: Cover Letter (Matching Header & Footer Style)
                    # -----------------------------------------------------
                    cl_pdf = StyledCVPDF(doc_type="Cover Letter")
                    cl_pdf.add_page()
                    cl_pdf.draw_cv_header()
                    cl_pdf.draw_section_heading(f"Application for {clean_text(data['vacancy_details']['job_title'])}")
                    
                    cl_pdf.set_font("Helvetica", "", 9.5)
                    cl_pdf.set_text_color(30, 30, 30)
                    cl_pdf.multi_cell(0, 4.8, clean_text(data["cover_letter"]))
                    
                    cl_pdf_bytes = io.BytesIO()
                    cl_pdf.output(cl_pdf_bytes)
                    cl_pdf_data = cl_pdf_bytes.getvalue()

                    # -----------------------------------------------------
                    # UI Presentation & Downloads
                    # -----------------------------------------------------
                    st.success(f"Matched successfully for: {data['vacancy_details']['job_title']} at {data['vacancy_details']['organization']}")

                    tab_cv, tab_cl = st.tabs(["📄 Tailored CV Section (Objective & Experience)", "✉️ Tailored Cover Letter"])

                    with tab_cv:
                        st.subheader("Customized Career Objective")
                        st.info(data["tailored_career_objective"])
                        
                        st.subheader("Targeted Experience Bullets (Strictly by Org)")
                        for org in data["tailored_experience"]:
                            with st.expander(f"{org['organization']} — {org['role']}"):
                                for b in org["bullets"]:
                                    st.write(f"• {b}")

                        st.download_button(
                            label="📥 Download Tailored CV Experience (PDF - Matching Style)",
                            data=cv_pdf_data,
                            file_name=f"Sudha_Panthi_CV_{data['vacancy_details']['job_title'].replace(' ', '_')}.pdf",
                            mime="application/pdf"
                        )

                    with tab_cl:
                        st.subheader("Formal Cover Letter")
                        st.text_area("Cover Letter Preview:", value=data["cover_letter"], height=320)
                        st.download_button(
                            label="📥 Download Cover Letter (PDF - Matching Style)",
                            data=cl_pdf_data,
                            file_name=f"Sudha_Panthi_Cover_Letter_{data['vacancy_details']['job_title'].replace(' ', '_')}.pdf",
                            mime="application/pdf"
                        )

                except Exception as e:
                    st.error(f"Error processing document: {e}")

elif not api_key:
    st.info("Please enter your Gemini API key in the left sidebar to start.")s
