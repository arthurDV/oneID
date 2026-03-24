"""
Demo v2 — Agent Identity API avec vrai email MailSlurp.
"""

import json
import urllib.request

BASE = "http://localhost:8888"


def api(method, path):
    req = urllib.request.Request(
        f"{BASE}{path}",
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def pp(label, data):
    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"{'='*50}")
    print(json.dumps(data, indent=2, ensure_ascii=False))


print("\n🚀 Agent Identity API — Demo v2\n")

# 1. Créer une identité avec un vrai email
agent = api("POST", "/identities")
pp("1. Identité créée", agent)

agent_id = agent["id"]
email = agent["email"]
name = f"{agent['first_name']} {agent['last_name']}"

print(f"""
{'='*50}
  📬 L'agent {name} a un vrai email :
     {email}

  👉 Envoie un email à cette adresse depuis
     ta boîte mail personnelle pour tester !

  Puis relance : python3 demo.py --inbox {agent_id}
{'='*50}
""")

# 2. Lire l'inbox (vide pour l'instant)
inbox = api("GET", f"/identities/{agent_id}/inbox")
pp(f"2. Inbox de {name}", inbox)
