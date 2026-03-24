"""
Intégration Twilio — achète un vrai numéro de téléphone et lit les SMS reçus.
Doc : https://www.twilio.com/docs/phone-numbers
"""

import json
import urllib.request
import urllib.parse
import base64

TWILIO_BASE = "https://api.twilio.com/2010-04-01"


def _auth_header(account_sid, auth_token):
    """Crée l'en-tête d'authentification Twilio (Basic Auth)."""
    credentials = f"{account_sid}:{auth_token}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


def buy_phone_number(account_sid, auth_token, country="US"):
    """
    Achète un vrai numéro de téléphone via Twilio.
    Retourne : { phone_number, sid }
    """

    # Étape 1 — chercher un numéro disponible
    search_url = f"{TWILIO_BASE}/Accounts/{account_sid}/AvailablePhoneNumbers/{country}/Local.json?SmsEnabled=true&Limit=1"
    req = urllib.request.Request(
        search_url,
        headers={"Authorization": _auth_header(account_sid, auth_token)},
        method="GET",
    )
    with urllib.request.urlopen(req) as resp:
        results = json.loads(resp.read())

    available = results.get("available_phone_numbers", [])
    if not available:
        raise Exception("Aucun numéro disponible dans ce pays.")

    phone_number = available[0]["phone_number"]

    # Étape 2 — acheter ce numéro
    buy_url = f"{TWILIO_BASE}/Accounts/{account_sid}/IncomingPhoneNumbers.json"
    body = urllib.parse.urlencode({"PhoneNumber": phone_number}).encode()

    req = urllib.request.Request(
        buy_url,
        data=body,
        headers={
            "Authorization": _auth_header(account_sid, auth_token),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())

    return {
        "phone": result["phone_number"],
        "phone_sid": result["sid"],
    }


def get_sms_messages(account_sid, auth_token, phone_number):
    """
    Lit les SMS reçus sur un numéro Twilio.
    Retourne une liste de messages.
    """
    url = f"{TWILIO_BASE}/Accounts/{account_sid}/Messages.json?To={urllib.parse.quote(phone_number)}&Direction=inbound"
    req = urllib.request.Request(
        url,
        headers={"Authorization": _auth_header(account_sid, auth_token)},
        method="GET",
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())

    return [
        {
            "id": m["sid"],
            "from": m["from"],
            "body": m["body"],
            "received_at": m["date_sent"],
        }
        for m in result.get("messages", [])
    ]
