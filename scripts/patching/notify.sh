#!/usr/bin/env bash
# Shared email sender for patch notifications.
# Usage: notify.sh <subject> <body>
set -euo pipefail

eval "$(SOPS_AGE_KEY_FILE=/root/.age/key.txt /usr/local/bin/sops --decrypt --input-type dotenv --output-type dotenv /root/homelab/secrets/gmail.sops)"

SUBJECT="${1:?Usage: notify.sh <subject> <body>}"
BODY="${2:?}"

python3 - <<PYEOF
import smtplib, os
from email.mime.text import MIMEText

user = os.environ['GMAIL_USER']
password = os.environ['GMAIL_APP_PASSWORD']

msg = MIMEText("""$BODY""")
msg['Subject'] = """$SUBJECT"""
msg['From'] = user
msg['To'] = user

with smtplib.SMTP('smtp.gmail.com', 587) as s:
    s.starttls()
    s.login(user, password)
    s.sendmail(user, user, msg.as_string())
PYEOF
