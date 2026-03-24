"""
Configuration — lit les clés depuis les variables d'environnement.
En local, crée un fichier .env.local (jamais committé sur GitHub).
Sur Railway, ajoute les variables dans le dashboard.
"""

import os

MAILSLURP_API_KEY  = os.environ.get("MAILSLURP_API_KEY", "")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN  = os.environ.get("TWILIO_AUTH_TOKEN", "")
