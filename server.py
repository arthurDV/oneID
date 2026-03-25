"""
Droid — Agent Identity API
Give any AI agent a real identity in one API call.
Email (MailSlurp) + Phone (Twilio) + Generated name.

Endpoints:
  POST /identities            → create an identity
  GET  /identities            → list all identities
  GET  /identities/<id>/inbox → read all received emails (full body)
  GET  /identities/<id>/sms   → read all received SMS
"""

import json
import uuid
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

from names import generate_name
from config import MAILSLURP_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
from providers.email import create_inbox, get_emails
from providers.sms import buy_phone_number, get_sms_messages

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
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, ensure_ascii=False).encode())

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ---------- GET ----------

    def do_GET(self):

        # GET / — landing page
        if self.path == "/" or self.path == "/index.html":
            html_path = os.path.join(os.path.dirname(__file__), "index.html")
            with open(html_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content)
            return

        # GET /identities
        if self.path == "/identities":
            identities = load_identities()
            self._send_json(200, {"identities": list(identities.values())})
            return

        # GET /identities/<id>/inbox — full email content
        if self.path.startswith("/identities/") and self.path.endswith("/inbox"):
            identity_id = self.path.split("/")[2]
            identities = load_identities()

            if identity_id not in identities:
                self._send_json(404, {"error": "Identity not found"})
                return

            identity = identities[identity_id]
            inbox_id = identity.get("inbox_id")

            if not inbox_id:
                self._send_json(400, {"error": "No email inbox linked"})
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

        # GET /identities/<id>/sms — full SMS content
        if self.path.startswith("/identities/") and self.path.endswith("/sms"):
            identity_id = self.path.split("/")[2]
            identities = load_identities()

            if identity_id not in identities:
                self._send_json(404, {"error": "Identity not found"})
                return

            identity = identities[identity_id]
            phone = identity.get("phone")

            if not phone:
                self._send_json(400, {"error": "No phone number linked"})
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

                print(f"  → Email pour {first_name} {last_name}...")
                inbox = create_inbox(MAILSLURP_API_KEY, first_name, last_name)

                phone = None
                phone_sid = None
                if TWILIO_READY:
                    try:
                        print(f"  → Numéro de téléphone...")
                        sms = buy_phone_number(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                        phone = sms["phone"]
                        phone_sid = sms["phone_sid"]
                    except Exception as e:
                        print(f"  ⚠️  Téléphone non disponible : {e}")

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

                print(f"  ✅ {first_name} {last_name} — {inbox['email']} | {phone or 'no phone'}")
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
    server = HTTPServer(("0.0.0.0", port), AgentIdentityHandler)
    print(f"""
╔══════════════════════════════════════════╗
║     Droid — Agent Identity API           ║
║                                          ║
║  🚀 http://localhost:{port}                ║
║                                          ║
║  POST /identities            → create    ║
║  GET  /identities            → list      ║
║  GET  /identities/:id/inbox  → emails    ║
║  GET  /identities/:id/sms    → SMS       ║
║                                          ║
║  Email : {"✅ MailSlurp" if MAILSLURP_API_KEY != "COLLE_TA_CLE_MAILSLURP_ICI" else "⚠️  not configured"}               ║
║  Phone : {"✅ Twilio  " if TWILIO_READY else "⚠️  not configured"}               ║
╚══════════════════════════════════════════╝
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped.")
        server.server_close()
