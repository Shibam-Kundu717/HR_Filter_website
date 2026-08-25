import os
import shutil

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse

from mailer import send_invitation
from parser import extract_text_from_pdf, parse_resume
from ranker import rank_candidate

app = FastAPI(title="HR Resume Screener API")


@app.get("/", response_class=HTMLResponse)
def home():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/screen-resume/")
async def screen_resume(
    job_title: str = Form(...),
    required_skills: str = Form(...),
    file: UploadFile = File(...),
):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        text = extract_text_from_pdf(temp_path)
        candidate = parse_resume(text)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    req_list = [s.strip() for s in required_skills.split(",") if s.strip()]
    ranking = rank_candidate(req_list, candidate.get("skills", []))

    email_sent = False
    if ranking["is_qualified"] and candidate.get("email"):
        email_sent = send_invitation(candidate["email"], candidate.get("name", "Applicant"), job_title)

    return {
        "candidate": candidate,
        "ranking": ranking,
        "email_sent": email_sent,
    }