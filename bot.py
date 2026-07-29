# bot.py
# Orquestador principal del sistema de gestión - CON LOGS EXTRA

from flask import Flask, request
from areas.gestion_ventas import presupuesto, notificaciones, asesores, pagos
from areas.gestion_ventas.clientes import buscar_por_dni, crear_cliente
from utils import config
import os
import sys
import logging

# === CONFIGURACIÓN DE LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# === DICCIONARIO DE SESIONES ===
sesiones = {}

@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    mensaje = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    
    logger.info(f"📩 NUEVO MENSAJE RECIBIDO")
    logger.info(f"   📱 Remitente: {sender}")
    logger.info(f"   💬 Mensaje: '{mensaje}'")
    
    try:
        respuesta = procesar_mensaje(mensaje, sender)
        logger.info(f"🤖 Respuesta enviada: {respuesta[:100]}..." if len(respuesta) > 100 else f"🤖 Respuesta enviada: {respuesta}")
        from twilio.twiml.messaging_response import MessagingResponse
        resp = MessagingResponse()
        resp.message().body(respuesta)
        return str(resp)
    except Exception as e:
        logger.error(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return "Error interno", 500

def procesar_mensaje(mensaje, sender):
    logger.info(f"🧠 Procesando mensaje: '{mensaje}' de {sender}")
    mensaje_lower = mensaje.lower().strip()
    
    # Verificar estado de sesión
    estado_actual = sesiones.get(sender)
    
    # Si el usuario está en el flujo de asesor
    if estado_actual == "esperando_consulta_asesor":
        logger.info(f"   📞 Procesando consulta de asesor de {sender}")
        logger.info(f"   📞 ANTES de llamar a asesores.procesar_consulta()")
        
        respuesta = asesores.procesar_consulta(sender, mensaje)
        
        logger.info(f"   📞 DESPUÉS de llamar a asesores.procesar_consulta()")
        logger.info(f"   📞 Respuesta recibida: {respuesta[:50]}...")
        
        sesiones[sender] = None  # Limpiar estado
        return respuesta
    
    # === MENÚ PRINCIPAL ===
    if mensaje_lower in ["hola", "buenos dias", "buenas tardes"]:
        logger.info("   ✅ Intención: Menú principal")
        sesiones[sender] = None
        return mostrar_menu()
    
    if mensaje_lower == "1" or mensaje_lower.startswith("presupuesto"):
        logger.info("   ✅ Intención: Presupuesto")
        return iniciar_presupuesto(sender, mensaje)
    
    if mensaje_lower == "2" or "estado" in mensaje_lower:
        logger.info("   ✅ Intención: Consultar estado")
        return consultar_estado(sender, mensaje)
    
    if mensaje_lower == "3" or "asesor" in mensaje_lower:
        logger.info("   ✅ Intención: Hablar con asesor")
        return iniciar_asesor(sender, mensaje)
    
    if mensaje_lower == "4" or "reclamo" in mensaje_lower:
        logger.info("   ✅ Intención: Reclamos o sugerencias")
        return "📝 *Reclamos y sugerencias*\n\nEscribí tu mensaje y lo vamos a revisar."
    
    if mensaje_lower == "0":
        logger.info("   ✅ Intención: Repetir menú")
        return mostrar_menu()
    
    logger.warning("   ⚠️ Intención no reconocida")
    return no_entendido()

def mostrar_menu():
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
    logger.info(f"   🔧 Iniciando presupuesto para {sender}")
    return """
🪑 *Vamos a tomar los datos de tu presupuesto.*

*Paso 1:* ¿Qué producto estás necesitando?
(Ej: *Mesa de roble, Silla rústica, Bajo mesada, Estante flotante, Mueble a medida*)

Respondé con el nombre del producto.
"""

def consultar_estado(sender, mensaje):
    logger.info(f"   🔍 Consultando estado para {sender}")
    return """
🔍 *Consultar estado de pedido*

Para consultar el estado de tu pedido, necesito tu **DNI** o **CUIT**.

➡️ *Ejemplo:* 20123456789
"""

def iniciar_asesor(sender, mensaje):
    logger.info(f"   📞 Iniciando flujo de asesor para {sender}")
    sesiones[sender] = "esperando_consulta_asesor"
    return """
📞 *Hablar con un asesor*

Decime tu consulta y un asesor te va a responder por este mismo chat.

👉 Escribí tu mensaje:
"""

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info("🚀 Bot de gestión iniciado...")
    logger.info(f"📡 Escuchando en el puerto {port}")
    logger.info("✅ Logs detallados activados")
    app.run(host='0.0.0.0', port=port, debug=False)
