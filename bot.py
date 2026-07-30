# bot.py
# Orquestador principal del sistema de gestión - CON PROCESAMIENTO DE RESPUESTA DE ASESOR

from flask import Flask, request
from areas.gestion_ventas import presupuesto, notificaciones, asesores, pagos
from areas.gestion_ventas.clientes import buscar_por_dni, crear_cliente
from utils import config
import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

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
    
    # === VERIFICAR SI ES RESPUESTA DE ASESOR ===
    if mensaje_lower.startswith("respuesta c-") or mensaje_lower.startswith("c-"):
        logger.info("   📞 Procesando respuesta de asesor")
        respuesta_asesor = asesores.procesar_respuesta_asesor(mensaje)
        if respuesta_asesor:
            # Enviar la respuesta al cliente
            codigo = respuesta_asesor["codigo"]
            respuesta_texto = respuesta_asesor["respuesta"]
            # Buscar el teléfono del cliente en CONSULTAS
            cliente_telefono = asesores.obtener_telefono_cliente(codigo)
            if cliente_telefono:
                # Enviar mensaje al cliente (usando Twilio)
                from twilio.rest import Client
                account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
                auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
                from_number = os.environ.get('TWILIO_WHATSAPP_NUMBER')
                
                if account_sid and auth_token and from_number:
                    client = Client(account_sid, auth_token)
                    client.messages.create(
                        from_=f'whatsapp:{from_number}',
                        body=f"📞 *Un asesor te responde:*\n{respuesta_texto}",
                        to=f'whatsapp:{cliente_telefono}'
                    )
                    logger.info(f"✅ Respuesta enviada al cliente {cliente_telefono}")
                    return "✅ Tu respuesta fue enviada al cliente."
                else:
                    logger.error("❌ Faltan variables de Twilio")
                    return "⚠️ Error al enviar la respuesta."
            else:
                logger.error(f"❌ No se encontró cliente para código {codigo}")
                return "⚠️ No se encontró la consulta."
        else:
            return no_entendido()
    
    # === VERIFICAR COMANDOS PRINCIPALES ===
    if mensaje_lower in ["hola", "buenos dias", "buenas tardes"]:
        logger.info("   ✅ Intención: Menú principal")
        sesiones[sender] = None
        return mostrar_menu()
    
    if mensaje_lower == "1" or mensaje_lower.startswith("presupuesto"):
        logger.info("   ✅ Intención: Presupuesto")
        sesiones[sender] = None
        return iniciar_presupuesto(sender, mensaje)
    
    if mensaje_lower == "2" or "estado" in mensaje_lower:
        logger.info("   ✅ Intención: Consultar estado")
        sesiones[sender] = None
        return consultar_estado(sender, mensaje)
    
    if mensaje_lower == "3" or "asesor" in mensaje_lower:
        logger.info("   ✅ Intención: Hablar con asesor")
        return iniciar_asesor(sender, mensaje)
    
    if mensaje_lower == "4" or "reclamo" in mensaje_lower:
        logger.info("   ✅ Intención: Reclamos o sugerencias")
        sesiones[sender] = None
        return "📝 *Reclamos y sugerencias*\n\nEscribí tu mensaje y lo vamos a revisar."
    
    if mensaje_lower == "0":
        logger.info("   ✅ Intención: Repetir menú")
        sesiones[sender] = None
        return mostrar_menu()
    
    # === VERIFICAR ESTADO DE SESIÓN ===
    estado_actual = sesiones.get(sender)
    
    if estado_actual == "esperando_consulta_asesor":
        logger.info(f"   📞 Procesando consulta de asesor de {sender}")
        respuesta = asesores.procesar_consulta(sender, mensaje)
        
        if "✅ *Consulta enviada*" in respuesta:
            sesiones[sender] = None
            logger.info(f"   📞 Consulta exitosa. Estado limpiado.")
        else:
            logger.info(f"   📞 La consulta falló. Manteniendo estado 'esperando_consulta_asesor' para {sender}")
        
        return respuesta
    
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
