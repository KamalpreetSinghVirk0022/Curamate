import streamlit as st
from services.ai_service import generate_analysis
from config.prompts import SPECIALIST_PROMPTS
from utils.pdf_extractor import extract_text_from_pdf
from config.sample_data import SAMPLE_REPORT
from config.app_config import MAX_UPLOAD_SIZE_MB
import re
from typing import List, Tuple


def show_analysis_form():
    # Initialize report source in session state for new sessions
    if 'current_session' in st.session_state and 'report_source' not in st.session_state:
        st.session_state.report_source = "Upload PDF"
    
    report_source = st.radio(
        "Choose report source",
        ["Upload PDF", "Use Sample PDF"],
        index=0 if st.session_state.get('report_source') == "Upload PDF" else 1,
        horizontal=True,
        key='report_source'
    )

    pdf_contents = get_report_contents(report_source)
            
    if pdf_contents:  
        render_patient_form(pdf_contents)

def parse_ai_response(content: str) -> Tuple[str, List[str]]:
    """Parses the AI's text output to find risk category and health risks."""
    risk_category = "No Risk" # Default
    health_risks = []
    
    
    category_match = re.search(
        r"Risk Category:\s*(.*?):", 
        content,
        re.IGNORECASE | re.DOTALL 
    )
    if category_match:
        risk_category = category_match.group(1).strip()
    
    # Find Potential Health Risks
    risks_match = re.search(
        r"Potential Health Risks:\s*(.*?)\s*Recommendations:", 
        content, 
        re.IGNORECASE | re.DOTALL
    )
    if risks_match:
        risks_block = risks_match.group(1)
        
        # Find all bullet points
        health_risks_raw = re.findall(
            r"^\s*(.*?)\s*\(", 
            risks_block, 
            re.MULTILINE
        )
        
        health_risks = [
            risk.strip().replace(":", "") for risk in health_risks_raw
            if risk.strip() and "Analysis generated" not in risk
        ]

    return risk_category, health_risks

def get_report_contents(report_source):
    if report_source == "Upload PDF":
        uploaded_file = st.file_uploader(
            f"Upload blood report PDF (Max {MAX_UPLOAD_SIZE_MB}MB)", 
            type=['pdf'],
            help=f"Maximum file size: {MAX_UPLOAD_SIZE_MB}MB. Only PDF files containing medical reports are supported"
        )
        if uploaded_file:
            file_size_mb = uploaded_file.size / (1024 * 1024)  
            if file_size_mb > MAX_UPLOAD_SIZE_MB:
                st.error(f"File size ({file_size_mb:.1f}MB) exceeds the {MAX_UPLOAD_SIZE_MB}MB limit.")
                return None
                
            if uploaded_file.type != 'application/pdf':
                st.error("Please upload a valid PDF file.")
                return None
                
            pdf_contents = extract_text_from_pdf(uploaded_file)
            if isinstance(pdf_contents, str) and (
                pdf_contents.startswith(("File size exceeds", "Invalid file type", "Error validating")) or
                pdf_contents.startswith("The uploaded file") or
                "error" in pdf_contents.lower()
            ):
                st.error(pdf_contents)
                return None
            with st.expander("View Extracted Report"):
                st.text(pdf_contents)
            return pdf_contents
    else:
        with st.expander("View Sample Report"):
            st.text(SAMPLE_REPORT)
        return SAMPLE_REPORT
    return None

def render_patient_form(pdf_contents):
    with st.form("analysis_form"):
        patient_name = st.text_input("Patient Name")
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Age", min_value=0, max_value=120)
        with col2:
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        
        if st.form_submit_button("Analyze Report"):
            handle_form_submission(patient_name, age, gender, pdf_contents)

def handle_form_submission(patient_name, age, gender, pdf_contents):
    if not all([patient_name, age, gender]):
        st.error("Please fill in all fields")
        return

    can_analyze, error_msg = generate_analysis(None, None, check_only=True)
    if not can_analyze:
        st.error(error_msg)
        st.stop()
        return

    with st.spinner("Analyzing report..."):
        st.session_state.auth_service.save_chat_message(
            st.session_state.current_session['id'],
            f"Analyzing report for patient: {patient_name}"
        )
        
        result = generate_analysis({
            "patient_name": patient_name,
            "age": age,
            "gender": gender,
            "report": pdf_contents
        }, SPECIALIST_PROMPTS["comprehensive_analyst"])
        
        if result["success"]:
            content = result["content"]
            if "model_used" in result:
                model_info = f"\n\n*Analysis generated using {result['model_used']}*"
                content += model_info
                
            st.session_state.auth_service.save_chat_message(
                st.session_state.current_session['id'],
                content,
                role='assistant'
            )
            
         
            risk_category, health_risks = parse_ai_response(content)
            
            st.warning(f"DEBUG: Parsed Risk Category = '{risk_category}'")
            st.info(f"DEBUG: Parsed Health Risks = {health_risks}")
            
            if "high" in risk_category.lower():
                st.session_state.show_booking_form = True
                st.session_state.health_risks_for_booking = health_risks
                st.session_state.user_details_for_booking = {
                    "name": patient_name,
                    "age": age,
                    "gender": gender
                }
            else:
                st.error("DEBUG: `if 'high' in risk_category` was FALSE. Booking page not triggered.")

            st.rerun() 
        else:
            st.error(result["error"])
            st.stop()
