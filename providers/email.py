"""
Intégration MailSlurp — crée de vraies boîtes email et lit les messages reçus.
Doc : https://www.mailslurp.com/docs/
"""

import json
import urllib.request
import urllib.error

MAILSLURP_BASE = "https://api.mailslurp.com"


def create_inbox(api_key, first_name, last_name):
    """
    Crée une vraie boîte email pour l'agent.
    Retourne : { inbox_id, email }
    """
    url = f"{MAILSLURP_BASE}/inboxes"
    data = json.dumps({
        "name": f"{first_name} {last_name}",
    }).encode()

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            return {
                "inbox_id": result["id"],
                "email": result["emailAddress"],
            }
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise Exception(f"MailSlurp {e.code}: {body}")


def get_emails(api_key, inbox_id):
    """
    Lit les emails reçus dans la boîte de l'agent.
    Retourne une liste de messages avec le corps complet.
    """
    url = f"{MAILSLURP_BASE}/inboxes/{inbox_id}/emails"
    req = urllib.request.Request(
        url,
        headers={"x-api-key": api_key},
        method="GET",
    )

    with urllib.request.urlopen(req) as resp:
        emails = json.loads(resp.read())

    results = []
    for e in emails:
        body = get_email_body(api_key, e.get("id"))
        results.append({
            "id": e.get("id"),
            "from": e.get("from"),
            "subject": e.get("subject"),
            "body": body,
            "received_at": e.get("createdAt"),
        })
    return results


def get_email_body(api_key, email_id):
    """
    Récupère le contenu complet d'un email (corps du message).
    """
    url = f"{MAILSLURP_BASE}/emails/{email_id}"
    req = urllib.request.Request(
        url,
        headers={"x-api-key": api_key},
        method="GET",
    )

    with urllib.request.urlopen(req) as resp:
        email = json.loads(resp.read())
        return email.get("body", "") or ""
