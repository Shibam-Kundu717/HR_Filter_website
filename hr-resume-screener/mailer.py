import os

import resend


def send_invitation(to_email: str, candidate_name: str, job_title: str):
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        return False

    resend.api_key = api_key
    params = {
        "from": "HR Team <onboarding@resend.dev>",
        "to": [to_email],
        "subject": f"Next Steps: {job_title} Application",
        "html": f"<h1>Hi {candidate_name},</h1><p>Congratulations! Your resume passed our initial skill requirements for <b>{job_title}</b>. We will be in touch shortly for an interview.</p>",
    }
    try:
        resend.Emails.send(params)
        return True
    except Exception:
        return False