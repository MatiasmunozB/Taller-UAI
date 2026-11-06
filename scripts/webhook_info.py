"""Consulta a Telegram el estado actual del webhook."""

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def main() -> int:
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    if not token:
        print("Falta TELEGRAM_TOKEN en .env.", file=sys.stderr)
        return 2

    try:
        response = httpx.get(
            f"https://api.telegram.org/bot{token}/getWebhookInfo",
            timeout=20.0,
        )
    except httpx.HTTPError as exc:
        print(
            f"No se pudo contactar la API de Telegram ({type(exc).__name__}); "
            "se omitieron detalles para proteger el token.",
            file=sys.stderr,
        )
        return 1

    try:
        result = response.json()
    except ValueError:
        result = {"status_code": response.status_code, "body": response.text}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not response.is_success or not result.get("ok", False):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
