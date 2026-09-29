import streamlit as st
import os
from generator import CodeSnippetGenerator
from fpdf import FPDF

# 1. UI Configuration
st.set_page_config(
    page_title="GenAI Code Generator", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Helper function to generate PDF bytes
def create_pdf(requirement_text, code_text):
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(0, 10, "Auto-Generated Python Snippet", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)
    
    # Requirement Section
    pdf.set_font("Helvetica", style="B", size=12)
    pdf.cell(0, 10, "Feature Requirement:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 6, requirement_text)
    pdf.ln(5)
    
    # Code Section
    pdf.set_font("Helvetica", style="B", size=12)
    pdf.cell(0, 10, "Executable Code:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Courier", size=10) # Monospace font for code
    
    # Replace unsupported characters for standard PDF rendering
    safe_code = code_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, safe_code)
    
    return bytes(pdf.output())

# 2. Sidebar Configuration
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg", width=50)
    st.header("⚙️ Configuration")
    
    # API Key Input
    api_key = st.text_input("Gemini API Key", type="password", placeholder="Enter your key here...")
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key
        
    # Helpful link to generate the key
    st.markdown("Don't have a key?  \n[🔑 Create a Gemini API Key here](https://aistudio.google.com/app/apikey)")
    
    st.divider()
    st.markdown("**Architecture:**")
    st.markdown("- Few-Shot Prompting\n- AST Syntax Validation\n- Dynamic Model Failover")

# 3. Main Dashboard Header
st.title("⚡ Enterprise Code Snippet Generator")
st.markdown("Transform natural language feature requirements into standardized, syntactically verified Python boilerplate.")
st.divider()

# 4. Split Layout for Better UI (Input on left, Output on right)
col1, col2 = st.columns([1, 1.2], gap="large")

with col1:
    st.subheader("📝 Input Requirement")
    requirement_input = st.text_area(
        "Describe the Python function you need:",
        height=200,
        placeholder="e.g., Write a function that takes a Pandas DataFrame and returns summary statistics for all numeric columns..."
    )
    
    generate_btn = st.button("🚀 Generate Verified Code", use_container_width=True, type="primary")

with col2:
    st.subheader("💻 Output Console")
    
    if generate_btn:
        if not requirement_input.strip():
            st.warning("⚠️ Please enter a requirement first.")
        elif not os.environ.get("GEMINI_API_KEY"):
            st.error("⚠️ Please enter your API key in the sidebar.")
        else:
            with st.spinner("Analyzing requirement and generating syntax..."):
                generator = CodeSnippetGenerator()
                result = generator.generate_code(requirement_input)
                
                if result["is_valid"]:
                    st.success(result["message"])
                    
                    # Display the code
                    st.code(result["code"], language="python")
                    
                    # Download Buttons row
                    st.divider()
                    st.markdown("#### 📥 Download Assets")
                    
                    d_col1, d_col2 = st.columns(2)
                    
                    # Button 1: Download as PDF
                    pdf_bytes = create_pdf(requirement_input, result["code"])
                    d_col1.download_button(
                        label="📄 Download as PDF",
                        data=pdf_bytes,
                        file_name="generated_snippet.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                    # Button 2: Download as Python script (Developer standard)
                    d_col2.download_button(
                        label="🐍 Download as .py",
                        data=result["code"],
                        file_name="generated_snippet.py",
                        mime="text/x-python",
                        use_container_width=True
                    )
                else:
                    st.error(f"❌ {result['message']}")