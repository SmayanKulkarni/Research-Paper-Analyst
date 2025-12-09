import streamlit as st
import sys
import os
import json
from pathlib import Path

# Add backend to path so we can import services directly
sys.path.append(str(Path(__file__).parent.parent / "backend"))

# Import your actual backend logic
from app.services.pdf_parser_layout import parse_pdf_to_markdown
from app.crew.orchestrator import run_full_analysis
from app.services.paper_discovery import PaperDiscoveryService
from app.utils.logging import logger

st.set_page_config(
    page_title="Research Paper Analyst",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 Research Paper Analyst AI")
st.markdown("""
This tool uses a **Multi-Agent AI Crew** (powered by Llama 3.3 70B) to analyze research papers.
It checks for **Plagiarism**, **Citation Integrity**, **Structure**, and **Logic**.
""")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Groq API Key", type="password", help="Enter your Groq API Key if not set in environment.")
    if api_key:
        os.environ["GROQ_API_KEY"] = api_key
    
    st.info("System Status: Ready 🟢")
    st.markdown("---")
    st.markdown("### Agents Active:")
    st.checkbox("Proofreader", value=True, disabled=True)
    st.checkbox("Structure Analyst", value=True, disabled=True)
    st.checkbox("Consistency Checker", value=True, disabled=True)
    st.checkbox("Citation Verifier", value=True, disabled=True)
    st.checkbox("Plagiarism Detector", value=True, disabled=True)

# File Uploader
uploaded_file = st.file_uploader("Upload a Research Paper (PDF)", type=["pdf"])

if uploaded_file:
    # Save file temporarily
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, uploaded_file.name)
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.success(f"File '{uploaded_file.name}' uploaded successfully!")
    
    if st.button("🚀 Start Analysis", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: Discovery
            status_text.text("🔍 Phase 1/3: Discovering related papers on ArXiv...")
            progress_bar.progress(10)
            
            discovery_service = PaperDiscoveryService()
            # We catch errors here so analysis continues even if discovery fails
            try:
                found = discovery_service.find_similar_papers(file_path)
                st.toast(f"Found {len(found)} related papers!", icon="📚")
            except Exception as e:
                st.warning(f"Discovery warning: {e}")
            
            # Step 2: Parsing
            status_text.text("📄 Phase 2/3: Parsing document layout...")
            progress_bar.progress(30)
            
            parse_result = parse_pdf_to_markdown(file_path)
            if not parse_result["text"]:
                st.error("Failed to extract text from PDF.")
                st.stop()
                
            # Step 3: Analysis
            status_text.text("🤖 Phase 3/3: AI Agents are analyzing (this may take a minute)...")
            progress_bar.progress(50)
            
            # Run the Crew
            analysis = run_full_analysis(
                text=parse_result["text"],
                images=parse_result.get("images", [])
            )
            
            progress_bar.progress(100)
            status_text.text("✅ Analysis Complete!")
            
            # --- DISPLAY RESULTS ---
            
            # Create tabs for the report
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📝 Proofreading", 
                "🏗️ Structure", 
                "🔄 Consistency",
                "📖 Citations",
                "🕵️ Plagiarism"
            ])
            
            with tab1:
                st.subheader("Proofreading Report")
                st.markdown(analysis.get("proofreading", "No report available."))
            
            with tab2:
                st.subheader("Structure Analysis")
                st.markdown(analysis.get("structure", "No report available."))
                
            with tab3:
                st.subheader("Consistency Check")
                st.markdown(analysis.get("consistency", "No report available."))
                
            with tab4:
                st.subheader("Citation Verification")
                st.markdown(analysis.get("citations", "No report available."))
                
            with tab5:
                st.subheader("Plagiarism Check")
                st.markdown(analysis.get("plagiarism", "No report available."))
                
            # Allow download of raw JSON
            st.download_button(
                label="Download Full JSON Report",
                data=json.dumps(analysis, indent=2),
                file_name="analysis_report.json",
                mime="application/json"
            )
            
        except Exception as e:
            st.error(f"An error occurred during analysis: {str(e)}")
            logger.error(f"UI Error: {e}")