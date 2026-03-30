"""
Alakazam Remote MCP Server
Gives any AI agent 3 tools: create_identity, read_inbox, read_sms.

Remote = hosted on the internet. Any agent connects via URL.
No download, no install, no config file. Just plug the URL.
"""

import json
import os
import httpx
from mcp.server.fastmcp import FastMCP

API_URL = os.environ.get("ALAKAZAM_API_URL", "https://www.alakazam.run")
MCP_PORT = int(os.environ.get("PORT", "8080"))

mcp = FastMCP(
    "Alakazam",
    instructions=(
        "You are connected to Alakazam, an agent identity service. "
        "Use create_identity() to get a real name, email, and phone number. "
        "Store the returned token — you need it for read_inbox() and read_sms(). "
        "Use read_inbox() to check for verification emails after signing up on a website. "
        "Use read_sms() to check for SMS verification codes."
    ),
    host="0.0.0.0",
    port=MCP_PORT,
)


@mcp.tool()
async def create_identity() -> str:
    """Create a new identity with a real name, email address, and phone number.
    Returns a token that you must store — use it with read_inbox() and read_sms().
    Call this when you need to sign up on a website or service."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_URL}/identities", timeout=30)
        if resp.status_code == 201:
            data = resp.json()
            return json.dumps({
                "token": data["token"],
                "name": data["name"],
                "email": data["email"],
                "phone": data["phone"],
                "instructions": "Store the token. Use it with read_inbox(token) and read_sms(token)."
            }, indent=2)
        else:
            return f"Error {resp.status_code}: {resp.text}"


@mcp.tool()
async def read_inbox(token: str) -> str:
    """Read all emails received by an identity.
    Pass the token you got from create_identity().
    Use this after signing up on a website to get verification codes or confirmation links."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_URL}/inbox",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            if data["count"] == 0:
                return "No emails yet. Wait a few seconds and try again."
            return json.dumps(data, indent=2)
        else:
            return f"Error {resp.status_code}: {resp.text}"


@mcp.tool()
async def read_sms(token: str) -> str:
    """Read all SMS messages received by an identity.
    Pass the token you got from create_identity().
    Use this to get SMS verification codes."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_URL}/sms",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            if data["count"] == 0:
                return "No SMS yet. Wait a few seconds and try again."
            return json.dumps(data, indent=2)
        else:
            return f"Error {resp.status_code}: {resp.text}"


if __name__ == "__main__":
    print(f"🚀 Alakazam MCP Server (remote) on port {MCP_PORT}")
    mcp.run(transport="streamable-http")
