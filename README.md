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

## Conectar Telegram

1. En Telegram, habla con `@BotFather`, envía `/newbot` y copia el token. Guárdalo en `.env` como `TELEGRAM_TOKEN` y elige un valor secreto para `TELEGRAM_SECRET`. No subas `.env` a GitHub.

   Configura ambos valores en Heroku:

   ```powershell
   heroku config:set TELEGRAM_TOKEN="TOKEN_DE_BOTFATHER" TELEGRAM_SECRET="SECRETO_LARGO" -a $APP_NAME
   ```

2. Publica el código actualizado en GitHub y en Heroku:

   ```powershell
   git add api/app.py scripts/set_webhook.py scripts/webhook_info.py README.md
   git commit -m "conecta webhook de Telegram"
   git push origin main
   git push heroku main
   ```

3. Configura `PUBLIC_URL` con el dominio HTTPS de Heroku. Asegúrate de que `.env` local también tenga el mismo `TELEGRAM_TOKEN`, `TELEGRAM_SECRET` y `PUBLIC_URL`; los scripts de administración cargan esas variables desde `.env`.

   ```powershell
   heroku config:set PUBLIC_URL="https://$APP_NAME.herokuapp.com" -a $APP_NAME
   python scripts/set_webhook.py
   python scripts/webhook_info.py
   ```

   `set_webhook.py` registra `PUBLIC_URL/telegram` y envía `TELEGRAM_SECRET` a Telegram. `webhook_info.py` muestra la URL registrada, las actualizaciones pendientes y cualquier último error.

4. Abre los logs y envía al bot los seis mensajes usados para probar el router. Cada línea de log de Telegram debe indicar la ruta esperada:

   ```powershell
   heroku logs --tail -a $APP_NAME
   ```

   | Mensaje | Ruta esperada |
   | --- | --- |
   | `¿tienen la polera azul en talla M?` | `preventa` |
   | `mi pedido 4521 llegó roto` | `postventa` |
   | `hola` | `generica` |
   | `¿cuánto cuesta el envío a Valparaíso?` | `preventa` |
   | `quiero devolver unas zapatillas` | `postventa` |
   | `¿qué hora es en Tokio?` | `generica` |

5. Si el bot no responde, revisa que el webhook de `webhook_info.py` apunte a `https://<dominio-heroku>/telegram`, que `TELEGRAM_SECRET` coincida entre `.env` y Heroku, que `TELEGRAM_TOKEN` sea el token correcto de BotFather y que no haya errores recientes en `heroku logs --tail`.

Para probar antes del despliegue, ejecuta la API local y abre un túnel HTTPS con `cloudflared tunnel --url http://localhost:8000`. Usa la URL HTTPS que entrega Cloudflare como `PUBLIC_URL` en `.env`, y luego corre `python scripts/set_webhook.py`.
