"""
Alakazam — Agent Identity API
Give any AI agent a real identity in one API call.

One token = one identity. No IDs in URLs. Dead simple.

Endpoints:
  POST /identities    → create identity, get back a token
  GET  /inbox         → read emails (token required)
  GET  /sms           → read SMS (token required)
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
from auth import create_token, verify_token

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
IDENTITIES_FILE = os.path.join(DATA_DIR, "identities.json")
os.makedirs(DATA_DIR, exist_ok=True)

TWILIO_READY = bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN)


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

    def _get_identity(self):
        """Extract identity_id from JWT token. Returns (identity_id, identity_data) or (None, None)."""
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None, None
        token = auth[7:]
        payload = verify_token(token)
        if not payload:
            return None, None
        identity_id = payload.get("identity_id")
        if not identity_id:
            return None, None
        identities = load_identities()
        identity = identities.get(identity_id)
        if not identity:
            return None, None
        return identity_id, identity

    def _require_auth(self):
        """Check auth. Returns (identity_id, identity) or sends 401."""
        identity_id, identity = self._get_identity()
        if not identity:
            self._send_json(401, {
                "error": "Unauthorized",
                "message": "Missing or invalid token. Create an identity at POST /identities"
            })
            return None, None
        return identity_id, identity

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
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

        # GET /stats — protected count of identities created
        if self.path.startswith("/stats"):
            if "key=12345678!" not in self.path:
                self._send_json(401, {"error": "Unauthorized"})
                return
            identities = load_identities()
            self._send_json(200, {"identities_created": len(identities)})
            return

        # GET /inbox — read emails for this token's identity
        if self.path == "/inbox":
            identity_id, identity = self._require_auth()
            if not identity:
                return

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

        # GET /sms — read SMS for this token's identity
        if self.path == "/sms":
            identity_id, identity = self._require_auth()
            if not identity:
                return

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

        # POST /identities — create identity, return token
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
                token = create_token(identity_id)

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

                # return public info + token (never expose inbox_id or phone_sid)
                self._send_json(201, {
                    "token": token,
                    "name": f"{first_name} {last_name}",
                    "email": inbox["email"],
                    "phone": phone,
                })

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
║     Alakazam — Agent Identity API           ║
║                                          ║
║  🚀 http://localhost:{port}                ║
║                                          ║
║  POST /identities    → create + token    ║
║  GET  /inbox         → read emails       ║
║  GET  /sms           → read SMS          ║
║                                          ║
║  🔒 One token = one identity             ║
║                                          ║
║  Email : {"✅ MailSlurp" if MAILSLURP_API_KEY else "⚠️  not configured"}               ║
║  Phone : {"✅ Twilio  " if TWILIO_READY else "⚠️  not configured"}               ║
╚══════════════════════════════════════════╝
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped.")
        server.server_close()
