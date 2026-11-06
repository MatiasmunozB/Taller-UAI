"""Registra el webhook HTTPS de Telegram para la API desplegada."""

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
    secret = os.getenv("TELEGRAM_SECRET", "").strip()
    public_url = os.getenv("PUBLIC_URL", "").strip().rstrip("/")
    missing = [
        name
        for name, value in (
            ("TELEGRAM_TOKEN", token),
            ("TELEGRAM_SECRET", secret),
            ("PUBLIC_URL", public_url),
        )
        if not value
    ]
    if missing:
        print(f"Faltan variables en .env: {', '.join(missing)}", file=sys.stderr)
        return 2

    url = f"{public_url}/telegram"
    try:
        response = httpx.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json={"url": url, "secret_token": secret},
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
