import ast
import json
import os
import re

# Native Google SDK for Generation
from google import genai
from google.genai import types
from google.genai import errors

# LangChain for RAG & FAISS Vector Search
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

class CodeSnippetGenerator:
    def __init__(self, db_file: str = "knowledge_base.json"):
        # 1. RAG Setup: Local HuggingFace & FAISS
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_store = self._build_langchain_vectorstore(db_file)
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 2}) if self.vector_store else None
        
        # 2. LLM Setup: Native Google GenAI Client
        self.client = genai.Client()

    def _build_langchain_vectorstore(self, filepath: str):
        if not os.path.exists(filepath):
            return None
            
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        docs = [Document(page_content=item["requirement"], metadata={"code": item["code"]}) for item in data]
        if docs:
            return FAISS.from_documents(docs, self.embeddings)
        return None

    def _get_dynamic_fallback_models(self) -> list[str]:
        """Dynamically queries the API to get models available to YOUR specific key."""
        try:
            available_models = []
            for m in self.client.models.list():
                if m.supported_actions and "generateContent" in m.supported_actions:
                    name = m.name.replace("models/", "")
                    is_valid_base = "flash" in name or "pro" in name
                    is_not_restricted = all(bad_word not in name for bad_word in ["preview", "experimental", "image", "vision"])
                    
                    if is_valid_base and is_not_restricted:
                        available_models.append(name)
            
            available_models.sort(reverse=True)
            return available_models[:4] if available_models else ["gemini-1.5-flash"]
        except Exception:
            return ["gemini-1.5-flash"]

    def _build_prompt(self, user_requirement: str, retrieved_docs: list[Document], error_feedback: str = None) -> str:
        prompt_parts = [
            "You are an expert Python developer. Generate clean, executable Python code based on the requirement.",
            "Rules: Output ONLY valid Python code wrapped inside a ```python block.",
            "### Retrieved Context (Use these similar examples as style guides):\n"
        ]
        
        if retrieved_docs:
            for doc in retrieved_docs:
                prompt_parts.append(f"Requirement: {doc.page_content}\n```python\n{doc.metadata['code']}\n```\n")
        
        prompt_parts.append(f"### Target Requirement:\nRequirement: {user_requirement}\n")

        if error_feedback:
            prompt_parts.append(f"\nSyntax Error to fix:\n{error_feedback}\nPlease fix it and output corrected code.")

        return "\n".join(prompt_parts)

    def _extract_code(self, raw_response: str) -> str:
        match = re.search(r"```python\s*(.*?)\s*```", raw_response, re.DOTALL)
        return match.group(1).strip() if match else raw_response.strip().replace("```", "")

    def validate_syntax(self, code_str: str) -> tuple[bool, str]:
        try:
            ast.parse(code_str)
            return True, "Valid Python Syntax"
        except SyntaxError as e:
            return False, f"SyntaxError at line {e.lineno}: {e.msg}"

    def generate_code(self, requirement: str, max_retries: int = 2) -> dict:
        # 1. Fetch live models dynamically to prevent 404s
        dynamic_models = self._get_dynamic_fallback_models()
        
        # 2. LangChain RAG Retrieval
        retrieved_docs = self.retriever.invoke(requirement) if self.retriever else []
        
        error_context = None
        last_error = ""
        
        # Outer loop: AST Self-Healing
        for attempt in range(max_retries + 1):
            prompt = self._build_prompt(requirement, retrieved_docs, error_context)
            code = None
            is_valid = False
            validation_msg = ""
            successful_model = ""

            # Inner loop: Dynamic Model Failover via Native SDK
            for model_name in dynamic_models:
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(temperature=0.2)
                    )
                    
                    code = self._extract_code(response.text)
                    is_valid, validation_msg = self.validate_syntax(code)
                    successful_model = model_name
                    break
                    
                except (errors.ServerError, errors.ClientError) as e:
                    last_error = str(e)
                    continue
                except Exception as e:
                    last_error = str(e)
                    continue

            if code is None:
                return {"code": "", "is_valid": False, "message": f"All fallback models failed. Last error: {last_error}"}

            if is_valid:
                return {"code": code, "is_valid": True, "message": f"Success via {successful_model} (Hybrid LangChain RAG)"}
            else:
                error_context = validation_msg 

        return {"code": code, "is_valid": False, "message": "Failed to generate valid syntax."}