import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

from help_tools.helpers import log_line

BASE_RESULT_URL = "https://gitlab.com/magix.ai/survey-results/-/blob/master/results/results_{analysis_name}.zip"

def send_email_results(recipients: list[str], result_name: str):
    if recipients is not None and isinstance(recipients, str):
        recipients = [recipients]
    if recipients is None or len(recipients) == 0:
        log_line("No recipient email addresses provided.")
        return
    if result_name is None or result_name == "":
        log_line("No result name provided.")
        return
    host, port, sender, password = _get_email_credentials_from_env()
    if sender is None or sender == "":
        log_line("No sender email address provided.")
        return
    if password is None or password == "":
        log_line("No password email address provided.")
        return
    if host is None or host == "" or port is None:
        log_line("Host connection details missing.")
        return

    msg = EmailMessage()
    msg['Subject'] = 'Article Analysis Results'
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    message = """
Your article analysis results are ready and available on the following URL:
{url}
    """
    msg.set_content(message.format(url=_get_result_url(result_name)))
    try:
        with smtplib.SMTP_SSL(host, port) as smtp:
            smtp.login(user=sender, password=password)
            smtp.send_message(msg)
        log_line('Email sent successfully.')
    except smtplib.SMTPException as e:
        log_line("Error occured while sending message to: ", ",".join(recipients))



def _get_result_url(result_name: str) -> str:
    return BASE_RESULT_URL.format(analysis_name=result_name)

def _get_email_credentials_from_env():
    load_dotenv()
    email_host = os.environ.get("EMAIL_HOST", "")
    email_port = int(os.environ.get("EMAIL_PORT", 465))
    email_user = os.environ.get("EMAIL_USER")
    email_pass = os.environ.get("EMAIL_PASS")
    return email_host, email_port, email_user, email_pass
