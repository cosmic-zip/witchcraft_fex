import subprocess
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import time

load_dotenv()

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 25))


def send_email(message: str, status: str, name: str):
    msg = MIMEMultipart()
    msg["From"] = f"BACKEND STATUS {EMAIL_HOST_USER}"
    msg["To"] = f"Cosmic exists a container with status {status} container name: {name}"
    msg["Subject"] = message

    server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
    server.starttls()
    server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
    server.send_message(msg)
    server.quit()

def docker_report():
    cmd = [
        "curl",
        "--silent",
        "--unix-socket",
        "/var/run/docker.sock",
        "http://localhost/containers/json?all=true",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    containers = json.loads(result.stdout)

    status_map = {
        "created": 0,
        "restarting": 1,
        "running": 2,
        "removing": 3,
        "paused": 4,
        "exited": 5,
        "dead": 6,
    }

    data = []

    for c in containers:
        name = c["Names"][0] if c.get("Names") else None
        name = name.replace("/", "")
        state = c.get("State")
        status_text = c.get("Status")
        status_numeric = status_map.get(state, -1)

        out = (
            {
                "name": name,
                "id": c.get("Id"),
                "state": state,
                "status": status_text,
                "status_numeric": status_numeric,
            }
        )

        data.append(out)
          #aqui
        if state in ["restarting", "removing", "paused", "exited", "dead"]:
            print(str(out), state, name)
            send_email(str(out), state, name)
            time.sleep(5)

    output = {"data": data}

    # print(json.dumps(output))


    return output

docker_report()