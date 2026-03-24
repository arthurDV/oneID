"""
Agent Identity API — MVP v3
Donne une vraie identité à un agent en un seul appel.
Email (MailSlurp) + Téléphone (Twilio) + Nom généré.

Endpoints :
  POST /identities               → créer une identité complète
  GET  /identities               → lister toutes les identités
  GET  /identities/<id>/inbox    → lire les emails reçus
  GET  /identities/<id>/sms      → lire les SMS reçus
"""

import json
import uuid
import os
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

from names import generate_name
from config import MAILSLURP_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
from providers.email import create_inbox, get_emails, get_email_body
from providers.sms import buy_phone_number, get_sms_messages


def extract_code(text):
    """
    Cherche un code de vérification dans un texte.
    Couvre les patterns les plus courants : 4, 6, 8 chiffres.
    """
    # Patterns avec contexte explicite (priorité haute)
    contextual = re.findall(
        r'(?:code|verify|verification|confirm|otp|token)[^\d]{0,20}(\d{4,8})',
        text, re.IGNORECASE
    )
    if contextual:
        return contextual[0]

    # Codes 6 chiffres isolés (le plus courant)
    codes_6 = re.findall(r'\b(\d{6})\b', text)
    if codes_6:
        return codes_6[0]

    # Codes 4 chiffres isolés
    codes_4 = re.findall(r'\b(\d{4})\b', text)
    if codes_4:
        return codes_4[0]

    return None

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
IDENTITIES_FILE = os.path.join(DATA_DIR, "identities.json")
os.makedirs(DATA_DIR, exist_ok=True)

TWILIO_READY = TWILIO_ACCOUNT_SID != "COLLE_TON_ACCOUNT_SID_ICI"


# --- Storage ---

def load_identities():
    if not os.path.exists(IDENTITIES_FILE):
        return {}
    with open(IDENTITIES_FILE, "r") as f:
        return json.load(f)


def save_identities(identities):
    with open(IDENTITIES_FILE, "w") as f:
        json.dump(identities, f, indent=2)


# --- Handler ---

class AgentIdentityHandler(BaseHTTPRequestHandler):

    def _send_json(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, ensure_ascii=False).encode())

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    # ---------- GET ----------

    def do_GET(self):

        # GET /identities
        if self.path == "/identities":
            identities = load_identities()
            self._send_json(200, {"identities": list(identities.values())})
            return

        # GET /identities/<id>/inbox  — emails
        if self.path.startswith("/identities/") and self.path.endswith("/inbox"):
            identity_id = self.path.split("/")[2]
            identities = load_identities()

            if identity_id not in identities:
                self._send_json(404, {"error": "Identity not found"})
                return

            identity = identities[identity_id]
            inbox_id = identity.get("inbox_id")

            if not inbox_id:
                self._send_json(400, {"error": "No email inbox linked to this identity"})
                return

            try:
                emails = get_emails(MAILSLURP_API_KEY, inbox_id)
                self._send_json(200, {
                    "identity": {
                        "name": f"{identity['first_name']} {identity['last_name']}",
                        "email": identity["email"],
                    },
                    "emails": emails,
                    "count": len(emails),
                })
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        # GET /identities/<id>/verification-code
        if self.path.startswith("/identities/") and self.path.endswith("/verification-code"):
            identity_id = self.path.split("/")[2]
            identities = load_identities()

            if identity_id not in identities:
                self._send_json(404, {"error": "Identity not found"})
                return

            identity = identities[identity_id]
            candidates = []  # { code, from, channel, received_at }

            try:
                # Cherche dans les emails
                inbox_id = identity.get("inbox_id")
                if inbox_id:
                    emails = get_emails(MAILSLURP_API_KEY, inbox_id)
                    for email in emails:
                        body = get_email_body(MAILSLURP_API_KEY, email["id"])
                        full_text = f"{email.get('subject', '')} {body}"
                        code = extract_code(full_text)
                        if code:
                            candidates.append({
                                "code": code,
                                "from": email.get("from"),
                                "channel": "email",
                                "subject": email.get("subject"),
                                "received_at": email.get("received_at"),
                            })

                # Cherche dans les SMS
                phone = identity.get("phone")
                if phone and TWILIO_READY:
                    sms_list = get_sms_messages(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, phone)
                    for sms in sms_list:
                        code = extract_code(sms.get("body", ""))
                        if code:
                            candidates.append({
                                "code": code,
                                "from": sms.get("from"),
                                "channel": "sms",
                                "subject": None,
                                "received_at": sms.get("received_at"),
                            })

                if not candidates:
                    self._send_json(404, {"error": "No verification code found"})
                    return

                # Retourne le plus récent
                candidates.sort(key=lambda x: x.get("received_at") or "", reverse=True)
                self._send_json(200, candidates[0])

            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        # GET /identities/<id>/sms  — SMS
        if self.path.startswith("/identities/") and self.path.endswith("/sms"):
            identity_id = self.path.split("/")[2]
            identities = load_identities()

            if identity_id not in identities:
                self._send_json(404, {"error": "Identity not found"})
                return

            identity = identities[identity_id]
            phone = identity.get("phone")

            if not phone:
                self._send_json(400, {"error": "No phone number linked to this identity"})
                return

            try:
                messages = get_sms_messages(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, phone)
                self._send_json(200, {
                    "identity": {
                        "name": f"{identity['first_name']} {identity['last_name']}",
                        "phone": phone,
                    },
                    "sms": messages,
                    "count": len(messages),
                })
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        self._send_json(404, {"error": "Not found"})

    # ---------- POST ----------

    def do_POST(self):

        # POST /identities
        if self.path == "/identities":
            try:
                first_name, last_name = generate_name()

                # Email (MailSlurp)
                print(f"  → Email pour {first_name} {last_name}...")
                inbox = create_inbox(MAILSLURP_API_KEY, first_name, last_name)

                # Téléphone (Twilio — si configuré)
                phone = None
                phone_sid = None
                if TWILIO_READY:
                    print(f"  → Numéro de téléphone...")
                    sms = buy_phone_number(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                    phone = sms["phone"]
                    phone_sid = sms["phone_sid"]

                identity_id = str(uuid.uuid4())[:8]
                identity = {
                    "id": identity_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": inbox["email"],
                    "inbox_id": inbox["inbox_id"],
                    "phone": phone,
                    "phone_sid": phone_sid,
                    "created_at": datetime.now().isoformat(),
                    "status": "active",
                }

                identities = load_identities()
                identities[identity_id] = identity
                save_identities(identities)

                print(f"  ✅ {first_name} {last_name} — {inbox['email']} | {phone or 'pas de téléphone'}")
                self._send_json(201, identity)

            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        self._send_json(404, {"error": "Not found"})

    def log_message(self, format, *args):
        pass


# --- Start ---

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8888))
    host = "0.0.0.0"
    server = HTTPServer((host, port), AgentIdentityHandler)
    print(f"""
╔══════════════════════════════════════════╗
║     Agent Identity API — v3              ║
║                                          ║
║  🚀 http://localhost:{port}                ║
║                                          ║
║  POST /identities                → créer  ║
║  GET  /identities                → lister ║
║  GET  /identities/:id/inbox      → emails ║
║  GET  /identities/:id/sms        → SMS    ║
║  GET  /identities/:id/verification-code   ║
║                                          ║
║  Email  : {"✅ MailSlurp" if MAILSLURP_API_KEY != "COLLE_TA_CLE_MAILSLURP_ICI" else "⚠️  non configuré"}              ║
║  Téléphone : {"✅ Twilio  " if TWILIO_READY else "⚠️  non configuré"}              ║
╚══════════════════════════════════════════╝
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Serveur arrêté.")
        server.server_close()
