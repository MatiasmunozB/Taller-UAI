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
| `API_KEY` | Clave que exige `POST /chat` en la cabecera `X-API-Key`. |
| `DATABASE_URL` | Postgres donde se guarda la memoria de las conversaciones. Sin ella se usa RAM. |
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
python main.py router "me llamo Ana" --hilo prueba1
python main.py router --diagrama
```

`--saltos` muestra los nodos recorridos y el motivo; `--hilo NOMBRE` elige el `thread_id` (repítelo para continuar la misma conversación); `--diagrama` imprime el Mermaid sin llamar al modelo ni a la base.

## Memoria de las conversaciones

El grafo guarda cada conversación por `thread_id` (en la API, el `user_id` de `/chat`; en Telegram, el `chat_id`).

- **Con `DATABASE_URL`**, usa el checkpointer de Postgres de LangGraph (`PostgresSaver`): la memoria sobrevive a reinicios de Heroku y es la misma para la API y para `main.py`. Al arrancar crea sus tablas (`setup()`). Usa un pool de 1 a 2 conexiones por proceso, porque la base puede ser compartida, y comprueba cada conexión antes de usarla.
- **Sin `DATABASE_URL`, o si Postgres no responde al arrancar**, usa RAM (`MemorySaver`), registra el motivo en el log y la API sigue funcionando. En RAM la memoria se pierde al reiniciar.

`GET /health` indica cuál está en uso en el campo `memoria` (`"ram"` o `"postgres"`).

En local, agrega la URL a `.env`:

```
DATABASE_URL=postgresql://usuario:clave@host:5432/nombre_base
```

En Heroku, configúrala en *Config Vars* (si agregas el add-on Heroku Postgres, la crea automáticamente):

```powershell
heroku config:set DATABASE_URL="postgresql://usuario:clave@host:5432/nombre_base" -a $APP_NAME
```

Para revisar lo guardado:

```powershell
python scripts/ver_memoria.py            # lista hilos, cantidad de checkpoints y fecha del último
python scripts/ver_memoria.py prueba1    # mensajes de un hilo, en orden
```

## Levantar la API

```powershell
uvicorn api.app:app --reload --port 8000
```

La documentación interactiva está en <http://localhost:8000/docs>. Ejemplo para `/chat` en PowerShell:

```powershell
curl.exe -X POST "http://localhost:8000/chat" `
  -H "Content-Type: application/json" `
  -H "X-API-Key: TU_API_KEY" `
  -d '{"user_id":"cliente-123","texto":"¿tienen la polera azul en talla M?"}'
```

La respuesta incluye `ruta`, `motivo` y `respuesta`. El `user_id` se utiliza como `thread_id` para conservar la memoria de conversación.

## Clave de la API

`POST /chat` exige la cabecera `X-API-Key` con el valor de la variable de entorno `API_KEY`. Si falta o no coincide, responde `401`. `/health` sigue abierto y `/telegram` se protege con su propio `TELEGRAM_SECRET`. Si el servidor no tiene `API_KEY` configurada, `/chat` rechaza todas las solicitudes.

1. **Genera una clave** larga y aleatoria:

   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **En local**, agrégala a `.env` (nunca a `.env.example`):

   ```
   API_KEY=la-clave-generada
   ```

   Reinicia `uvicorn` para que la lea.

3. **En Heroku**, configúrala en *Settings → Config Vars* o con:

   ```powershell
   heroku config:set API_KEY="la-clave-generada" -a $APP_NAME
   ```

   Heroku reinicia la app automáticamente al cambiar una Config Var.

4. **Para probar desde Swagger**, abre `/docs`, pulsa *Authorize* (el candado), pega la clave y ejecuta `POST /chat`. En Bruno, define la variable secreta `apiKey` en el entorno (`local` o `heroku`).

## Correr las pruebas

```powershell
python -m pytest -q
python scripts/test_router.py
```

`tests/test_api.py` comprueba que `/chat` responde `401` sin clave y `200` con clave, que `/health` informa la memoria y que, si Postgres no responde, se usa RAM; usa un grafo falso y no toca la base ni el modelo. Las pruebas del router leen `tests/casos_router.json` y requieren `GOOGLE_API_KEY` porque evalúan el modelo real. La suite parametrizada acepta al menos 13 aciertos de 15; el script muestra la tabla, el porcentaje y los casos fallidos. Cada evaluación puede realizar hasta 15 llamadas al modelo.

## Desplegar en Heroku

Instala e inicia sesión con Heroku CLI. Desde la raíz del repositorio, define un nombre disponible para la app:

```powershell
$APP_NAME = "ecommerce-router-tu-nombre"
heroku login
heroku create $APP_NAME
heroku git:remote -a $APP_NAME
heroku config:set GOOGLE_API_KEY="TU_GOOGLE_API_KEY" API_KEY="TU_API_KEY" MODELO="gemini-3.5-flash-lite" -a $APP_NAME
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
