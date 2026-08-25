import json
import os
import re

import pdfplumber
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

PROVIDER_CONFIG = {
    "OPENAI": {"api_key": "OPENAI_API_KEY", "base_url": "OPENAI_BASE_URL", "model": "OPENAI_MODEL", "default_model": "gpt-4o-mini"},
    "DEEPSEEK": {"api_key": "DEEPSEEK_API_KEY", "base_url": "DEEPSEEK_BASE_URL", "model": "DEEPSEEK_MODEL", "default_model": "deepseek-chat"},
    "GEMINI": {"api_key": "GEMINI_API_KEY", "base_url": "GEMINI_BASE_URL", "model": "GEMINI_MODEL", "default_model": "gemini-1.5-flash"},
    "GROK": {"api_key": "GROK_API_KEY", "base_url": "GROK_BASE_URL", "model": "GROK_MODEL", "default_model": "grok-2-latest"},
    "GROQ": {"api_key": "GROQ_API_KEY", "base_url": "GROQ_BASE_URL", "model": "GROQ_MODEL", "default_model": "llama-3.1-8b-instant"},
    "OPENROUTER": {"api_key": "OPENROUTER_API_KEY", "base_url": "OPENROUTER_BASE_URL", "model": "OPENROUTER_MODEL", "default_model": "openai/gpt-4o-mini"},
    "OLLAMA": {"api_key": "OLLAMA_API_KEY", "base_url": "OLLAMA_BASE_URL", "model": "OLLAMA_MODEL", "default_model": "llama3.2"},
    "ANTHROPIC": {"api_key": "ANTHROPIC_API_KEY", "base_url": "ANTHROPIC_BASE_URL", "model": "ANTHROPIC_MODEL", "default_model": "claude-3-haiku-20240307"},
}


def _get_provider_settings():
    for provider_name, config in PROVIDER_CONFIG.items():
        api_key = os.getenv(config["api_key"])
        if not api_key:
            continue

        base_url = os.getenv(config["base_url"], "")
        model = os.getenv(config["model"], config["default_model"])
        yield provider_name, api_key, base_url or None, model


def _clean_skills(skills):
    cleaned = []
    seen = set()
    for skill in skills:
        value = str(skill).strip()
        if not value:
            continue
        normalized = re.sub(r"\s+", " ", value)
        if normalized.lower() not in seen:
            seen.add(normalized.lower())
            cleaned.append(normalized)
    return cleaned


def _fallback_parse_resume(resume_text: str) -> dict:
    text = resume_text or ""
    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    email = email_match.group(0) if email_match else ""

    name_match = re.search(r"(?im)^\s*(?:Name|Full Name)\s*[:\-]?\s*([A-Z][A-Za-z' .-]+)\s*$", text)
    name = name_match.group(1).strip() if name_match else ""
    if not name:
        first_line = text.splitlines()[0].strip() if text.splitlines() else ""
        name = first_line[:80] if first_line else "Applicant"

    skill_keywords = [
        "python", "fastapi", "docker", "aws", "azure", "gcp", "javascript", "typescript",
        "react", "node", "sql", "postgresql", "mongodb", "redis", "kubernetes", "linux",
        "machine learning", "data science", "pandas", "numpy", "flask", "django", "java",
        "c++", "c#", "go", "rust", "git", "terraform", "ci/cd", "html", "css", "rest api",
        "api", "pytest", "tensorflow", "pytorch", "spark", "etl", "tableau", "power bi"
    ]

    found_skills = []
    text_lower = text.lower()
    for skill in skill_keywords:
        if skill.lower() in text_lower:
            found_skills.append(skill)

    return {
        "name": name,
        "email": email,
        "skills": _clean_skills(found_skills)
    }


def _call_openai_compatible(provider_name: str, api_key: str, base_url: str, model: str, prompt: str):
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError(f"{provider_name} returned empty content")
    return json.loads(content)


def _call_anthropic(api_key: str, base_url: str, model: str, prompt: str):
    url = f"{base_url.rstrip('/')}/messages"
    response = requests.post(
        url,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    text = payload["content"][0]["text"]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(text.strip("```json").strip("```"))


def extract_text_from_pdf(pdf_path: str) -> str:
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


def parse_resume(resume_text: str) -> dict:
    prompt = f"""
    Extract the following details from this resume text as a JSON object:
    - name (string)
    - email (string)
    - skills (list of strings)

    Resume Text:
    {resume_text}
    """

    for provider_name, api_key, base_url, model in _get_provider_settings():
        try:
            if provider_name == "ANTHROPIC":
                return _call_anthropic(api_key, base_url, model, prompt)
            if base_url:
                return _call_openai_compatible(provider_name, api_key, base_url, model, prompt)
        except Exception:
            continue

    return _fallback_parse_resume(resume_text)