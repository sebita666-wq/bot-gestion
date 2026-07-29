# bot.py
# Orquestador principal del sistema de gestión (versión corregida)

from flask import Flask, request
from areas.gestion_ventas import presupuesto, notificaciones, asesores, pagos
from areas.gestion_ventas.clientes import buscar_por_dni, crear_cliente
from utils import config
import os

app = Flask(__name__)

# Ruta principal que recibe los mensajes de WhatsApp
@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    # Obtener datos del mensaje
    mensaje = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    
    print(f"📩 Mensaje de {sender}: {mensaje}")
    
    # Detectar intención y llamar al módulo correspondiente
    respuesta = procesar_mensaje(mensaje, sender)
    
    # Devolver la respuesta (en formato TwiML)
    from twilio.twiml.messaging_response import MessagingResponse
    resp = MessagingResponse()
    resp.message().body(respuesta)
    return str(resp)

def procesar_mensaje(mensaje, sender):
    """
    Procesa el mensaje y determina qué módulo debe responder.
    """
    mensaje_lower = mensaje.lower().strip()
    
    # Menú principal
    if mensaje_lower in ["hola", "buenos dias", "buenas tardes"]:
        return mostrar_menu()
    
    # Opción 1: Presupuesto
    if mensaje_lower == "1" or mensaje_lower.startswith("presupuesto"):
        return iniciar_presupuesto(sender, mensaje)
    
    # Opción 2: Consultar estado
    if mensaje_lower == "2" or "estado" in mensaje_lower:
        return consultar_estado(sender, mensaje)
    
    # Opción 3: Hablar con asesor
    if mensaje_lower == "3" or "asesor" in mensaje_lower:
        return iniciar_asesor(sender, mensaje)
    
    # Opción 4: Reclamos o sugerencias
    if mensaje_lower == "4" or "reclamo" in mensaje_lower:
        return "📝 *Reclamos y sugerencias*\n\nEscribí tu mensaje y lo vamos a revisar."
    
    # Opción 0: Repetir menú
    if mensaje_lower == "0":
        return mostrar_menu()
    
    # Respuesta por defecto (no entendido)
    return no_entendido()

def mostrar_menu():
    """
    Muestra el menú principal del bot de gestión.
    """
    return """
👋 *Menú principal*

1️⃣ Presupuesto
2️⃣ Consultar estado
3️⃣ Hablar con asesor
4️⃣ Reclamos o sugerencias
0️⃣ Repetir menú

📝 *Ejemplos:*
• 'Mesa de roble'
• 'Silla rústica'
• 'Bajo mesada a medida'

💬 Escribí 'Ayuda' para más detalles.
"""

def no_entendido():
    """
    Respuesta cuando el bot no entiende el mensaje.
    """
    return """
🤔 *No entendí lo que escribiste.*

✅ *Frases que funcionan:*
• 'Hola' para ver el menú
• '1' para pedir un presupuesto
• '2' para consultar el estado de tu pedido
• '3' para hablar con un asesor
• '4' para reclamos o sugerencias

💡 Escribí 'Ayuda' para más ejemplos.
"""

def iniciar_presupuesto(sender, mensaje):
    """
    Inicia el flujo de presupuesto para muebles.
    """
    return """
🪑 *Vamos a tomar los datos de tu presupuesto.*

*Paso 1:* ¿Qué producto estás necesitando?
(Ej: *Mesa de roble, Silla rústica, Bajo mesada, Estante flotante, Mueble a medida*)

Respondé con el nombre del producto.
"""

def consultar_estado(sender, mensaje):
    """
    Consulta el estado de un presupuesto o pedido.
    """
    return """
🔍 *Consultar estado de pedido*

Para consultar el estado de tu pedido, necesito tu **DNI** o **CUIT**.

➡️ *Ejemplo:* 20123456789
"""

def iniciar_asesor(sender, mensaje):
    """
    Inicia el flujo para hablar con un asesor.
    """
    return """
📞 *Hablar con un asesor*

Decime tu consulta y un asesor te va a responder por este mismo chat.

👉 Escribí tu mensaje:
"""

# Punto de entrada de la aplicación
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🚀 Bot de gestión iniciado...")
    print(f"📡 Escuchando en el puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
