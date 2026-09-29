import ast
import json
import os
import re
from google import genai
from google.genai import types
from google.genai import errors

class CodeSnippetGenerator:
    def __init__(self, examples_file: str = "few_shot_data.json"):
        self.client = genai.Client()
        self.examples = self._load_examples(examples_file)

    def _load_examples(self, filepath: str) -> list[dict]:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _get_dynamic_fallback_models(self) -> list[str]:
        """Dynamically fetches available generative models, strictly filtering out restricted previews."""
        try:
            available_models = []
            for m in self.client.models.list():
                if m.supported_actions and "generateContent" in m.supported_actions:
                    name = m.name.replace("models/", "")
                    
                    # STRICT FILTER: Only standard flash/pro models. NO previews, NO image models, NO experimental.
                    is_valid_base = "flash" in name or "pro" in name
                    is_not_restricted = all(bad_word not in name for bad_word in ["preview", "experimental", "image", "vision"])
                    
                    if is_valid_base and is_not_restricted:
                        available_models.append(name)
            
            available_models.sort(reverse=True)
            return available_models[:4] if available_models else ["gemini-3.8-flash"]
        except Exception:
            return ["gemini-3.8-flash", "gemini-3.8-flash-lite"]

    def _build_prompt(self, user_requirement: str, error_feedback: str = None) -> str:
        prompt_parts = [
            "You are an expert Python developer. Generate clean, executable Python code based on the requirement.",
            "Rules: Output ONLY valid Python code wrapped inside a ```python block.",
            "### Standard Examples:\n"
        ]
        
        for ex in self.examples:
            prompt_parts.append(f"Requirement: {ex['requirement']}\n```python\n{ex['code']}\n```\n")
        
        prompt_parts.append(f"### Target Requirement:\nRequirement: {user_requirement}\n")

        if error_feedback:
            prompt_parts.append(f"\nSyntax Error to fix:\n{error_feedback}\nPlease fix it and output corrected code.")

        return "\n".join(prompt_parts)

    def _extract_code(self, raw_response: str) -> str:
        match = re.search(r"```python\s*(.*?)\s*```", raw_response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return raw_response.strip().replace("```", "")

    def validate_syntax(self, code_str: str) -> tuple[bool, str]:
        try:
            ast.parse(code_str)
            return True, "Valid Python Syntax"
        except SyntaxError as e:
            return False, f"SyntaxError at line {e.lineno}: {e.msg}"

    def generate_code(self, requirement: str, max_retries: int = 2) -> dict:
        dynamic_models = self._get_dynamic_fallback_models()
        error_context = None
        last_api_error = ""
        
        for attempt in range(max_retries + 1):
            prompt = self._build_prompt(requirement, error_context)
            
            code = None
            is_valid = False
            validation_msg = ""
            successful_model = ""

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
                    break # Successfully got a response, break out of the model loop
                    
                except (errors.ServerError, errors.ClientError) as e:
                    # We now catch BOTH 503 Server Errors AND 429 Quota errors and gracefully skip to the next model!
                    last_api_error = str(e)
                    continue
                except Exception as e:
                    last_api_error = str(e)
                    continue

            # If 'code' is still None, every single model in the fallback list failed
            if code is None:
                return {
                    "code": "",
                    "is_valid": False,
                    "message": f"All available models failed or hit quota limits. Last error: {last_api_error}"
                }

            if is_valid:
                return {
                    "code": code, 
                    "is_valid": True, 
                    "message": f"Success! ({validation_msg} via {successful_model})"
                }
            else:
                error_context = validation_msg 

        return {"code": code, "is_valid": False, "message": "Failed to generate valid syntax after multiple attempts."}