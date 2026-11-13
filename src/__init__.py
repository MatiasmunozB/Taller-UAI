"""Paquete de agentes del proyecto.

Al importarlo, Python valida HTTPS con los certificados del sistema operativo
(Windows, macOS o Linux) en vez de su lista propia (certifi). Así funciona en
equipos con antivirus o proxy que inspeccionan HTTPS y cuyo certificado solo
está instalado en el sistema; sin esto, Gemini y Telegram fallan con
CERTIFICATE_VERIFY_FAILED.
"""

import truststore

truststore.inject_into_ssl()
