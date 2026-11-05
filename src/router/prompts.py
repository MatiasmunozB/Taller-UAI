"""Prompts y textos de respuesta del agente router."""

PROMPT_ROUTER = """Clasifica el último mensaje del cliente para un chat de ecommerce.

- preventa: intención de compra, preguntas por productos, precios, tallas, stock,
  promociones o formas de pago antes de comprar.
- postventa: queja, reclamo, seguimiento de un pedido ya hecho, devolución,
  cambio, garantía o producto dañado.
- Una queja por el precio o una pregunta por descuentos para comprar sigue
  siendo preventa.
- Si expresa que tiene un problema con un producto, sin intención de comprar,
  clasifica como postventa aunque no mencione un pedido.
- generica: temas ajenos al ecommerce (clima, chistes, preguntas generales) o
  saludos sin pedido.
- Si dudas entre preventa y postventa, fíjate si YA compró: si habla de un
  pedido existente, clasifica como postventa.

Devuelve la ruta más adecuada y un motivo breve de una frase."""

PROMPT_AGENTE_PREVENTA = (
    "Soy el agente de preventa. Recibí: {mensaje}. "
    "Pronto podré ayudarte con productos y compras."
)

PROMPT_AGENTE_POSTVENTA = (
    "Soy el agente de postventa. Recibí: {mensaje}. "
    "Pronto podré ayudarte con tu pedido."
)

RESPUESTA_GENERICA = (
    "¡Hola! Este chat es para consultas de nuestra tienda sobre productos y pedidos."
)
