# Ecommerce Router

Proyecto en Python 3.12 con un agente LangGraph que clasifica mensajes de clientes y los dirige a `preventa`, `postventa` o `generica`. Incluye una API FastAPI, pruebas de enrutamiento y una colección de Bruno.

## Configuración local

En PowerShell, desde la raíz del proyecto:

```powershell
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
```

Edita `.env` y agrega tu `GOOGLE_API_KEY`. Si `.env` ya existe, no lo sobrescribas; edítalo directamente. Instala dependencias:

```powershell
python -m pip install -r requirements.txt
```

Variables disponibles:

| Variable | Uso |
| --- | --- |
| `GOOGLE_API_KEY` | Clave para invocar Gemini; no la subas a GitHub. |
| `MODELO` | Modelo de Gemini; por defecto `gemini-3.5-flash-lite`. |
| `THREAD_ID` | ID opcional de conversación para el CLI. |
| `TELEGRAM_TOKEN` | Token del bot, entregado por BotFather. |
| `TELEGRAM_SECRET` | Secreto que se configurará para el webhook de Telegram. |
| `PUBLIC_URL` | URL HTTPS pública, por ejemplo la URL de la app en Heroku. |

`.env.example` contiene nombres y valores de muestra, nunca credenciales reales. `.env`, entornos virtuales, cachés y datos locales están excluidos por `.gitignore`.

## Correr el router en local

Con el entorno virtual activado y `GOOGLE_API_KEY` configurada:

```powershell
python main.py router "¿tienen la polera azul en talla M?" --saltos
python main.py router --diagrama
```

`--saltos` muestra los nodos recorridos y el motivo; `--diagrama` imprime el Mermaid sin llamar al modelo.

## Levantar la API

```powershell
uvicorn api.app:app --reload --port 8000
```

La documentación interactiva está en <http://localhost:8000/docs>. Ejemplo para `/chat` en PowerShell:

```powershell
curl.exe -X POST "http://localhost:8000/chat" `
  -H "Content-Type: application/json" `
  -d '{"user_id":"cliente-123","texto":"¿tienen la polera azul en talla M?"}'
```

La respuesta incluye `ruta`, `motivo` y `respuesta`. El `user_id` se utiliza como `thread_id` para conservar la memoria de conversación.

## Correr las pruebas

```powershell
python -m pytest -q
python scripts/test_router.py
```

Las pruebas del router leen `tests/casos_router.json` y requieren `GOOGLE_API_KEY` porque evalúan el modelo real. La suite parametrizada acepta al menos 13 aciertos de 15; el script muestra la tabla, el porcentaje y los casos fallidos. Cada evaluación puede realizar hasta 15 llamadas al modelo.

## Desplegar en Heroku

Instala e inicia sesión con Heroku CLI. Desde la raíz del repositorio, define un nombre disponible para la app:

```powershell
$APP_NAME = "ecommerce-router-tu-nombre"
heroku login
heroku create $APP_NAME
heroku git:remote -a $APP_NAME
heroku config:set GOOGLE_API_KEY="TU_GOOGLE_API_KEY" MODELO="gemini-3.5-flash-lite" -a $APP_NAME
git push heroku main
```

El despliegue usa `Procfile`, `.python-version` y `requirements.txt`. Confirma la URL HTTPS asignada con:

```powershell
heroku apps:info -a $APP_NAME
heroku config:set PUBLIC_URL="https://$APP_NAME.herokuapp.com" -a $APP_NAME
heroku logs --tail -a $APP_NAME
```

Configura los secretos desde Heroku Config Vars (o con `heroku config:set`); no los guardes en archivos versionados.

## Conectar Telegram (webhook provisional)

1. En Telegram, habla con `@BotFather`, crea el bot con `/newbot` y copia el token en un lugar seguro.
2. Configura `TELEGRAM_TOKEN` y `TELEGRAM_SECRET` como Config Vars de Heroku:

   ```powershell
   heroku config:set TELEGRAM_TOKEN="TOKEN_DE_BOTFATHER" TELEGRAM_SECRET="SECRETO_LARGO" -a $APP_NAME
   ```

3. En PowerShell, registra el webhook HTTPS. Sustituye los valores de ejemplo por tus secretos y la URL real:

   ```powershell
   $env:TELEGRAM_TOKEN = "TOKEN_DE_BOTFATHER"
   $env:TELEGRAM_SECRET = "SECRETO_LARGO"
   $env:PUBLIC_URL = "https://$APP_NAME.herokuapp.com"
   $body = @{ url = "$($env:PUBLIC_URL)/telegram"; secret_token = $env:TELEGRAM_SECRET } | ConvertTo-Json
   Invoke-RestMethod -Method Post -Uri "https://api.telegram.org/bot$($env:TELEGRAM_TOKEN)/setWebhook" -ContentType "application/json" -Body $body
   Invoke-RestMethod -Uri "https://api.telegram.org/bot$($env:TELEGRAM_TOKEN)/getWebhookInfo"
   ```

   También puedes apuntar Bruno a Heroku seleccionando el entorno `heroku` en `bruno/environments/`.

**Estado actual:** `/telegram` es un cascarón que acepta JSON y devuelve `{"ok":true}`. Todavía no verifica el encabezado secreto de Telegram ni responde mensajes del bot. Registrar el webhook solo prueba la entrega al endpoint; completa esa lógica antes de usarlo como integración funcional o de producción.
