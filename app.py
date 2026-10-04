import streamlit as st
import os
from generator import CodeSnippetGenerator
from fpdf import FPDF

st.set_page_config(page_title="GenAI Code Generator", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

def create_pdf(requirement_text, code_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(0, 10, "Auto-Generated Python Snippet", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)
    pdf.set_font("Helvetica", style="B", size=12)
    pdf.cell(0, 10, "Feature Requirement:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 6, requirement_text)
    pdf.ln(5)
    pdf.set_font("Helvetica", style="B", size=12)
    pdf.cell(0, 10, "Executable Code:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Courier", size=10)
    safe_code = code_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, safe_code)
    return bytes(pdf.output())

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg", width=50)
    st.header("⚙️ Configuration")
    
    api_key = st.text_input("Gemini API Key", type="password", placeholder="Enter API Key...")
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key
        
    st.markdown("[🔑 Create API Key](https://aistudio.google.com/app/apikey)")
    st.divider()

st.title("⚡ Enterprise RAG Code Generator")
st.markdown("Retrieves enterprise coding standards from a FAISS vector knowledge base using LangChain, generating syntactically verified Python boilerplate.")
st.divider()

col1, col2 = st.columns([1, 1.2], gap="large")

with col1:
    st.subheader("📝 Input Requirement")
    requirement_input = st.text_area("Describe the Python function you need:", height=200, placeholder="e.g., Write a function to calculate the frequency of words in a string...")
    generate_btn = st.button("🚀 Generate Verified Code", use_container_width=True, type="primary")

with col2:
    st.subheader("💻 Output Console")
    if generate_btn:
        if not requirement_input.strip():
            st.warning("⚠️ Please enter a requirement first.")
        elif not os.environ.get("GEMINI_API_KEY"):
            st.error("⚠️ Please enter your API key in the sidebar.")
        else:
            with st.spinner("🔍 Running Hybrid RAG Search & Generating Code..."):
                generator = CodeSnippetGenerator()
                result = generator.generate_code(requirement_input)
                
                if result["is_valid"]:
                    st.success(result["message"])
                    st.code(result["code"], language="python")
                    st.divider()
                    
                    d_col1, d_col2 = st.columns(2)
                    pdf_bytes = create_pdf(requirement_input, result["code"])
                    d_col1.download_button(label="📄 Download PDF", data=pdf_bytes, file_name="snippet.pdf", mime="application/pdf", use_container_width=True)
                    d_col2.download_button(label="🐍 Download .py", data=result["code"], file_name="snippet.py", mime="text/x-python", use_container_width=True)
                else:
                    st.error(f"❌ {result['message']}")