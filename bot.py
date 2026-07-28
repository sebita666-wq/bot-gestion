# bot.py
# Orquestador principal del sistema de gestión - CON LOGS MEJORADOS

from flask import Flask, request
from areas.gestion_ventas import presupuesto, notificaciones, asesores, pagos
from areas.gestion_ventas.clientes import buscar_por_dni, crear_cliente
from utils import config
import os
import json

app = Flask(__name__)

# Ruta principal que recibe los mensajes de WhatsApp
@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    # Obtener datos del mensaje
    try:
        mensaje = request.values.get('Body', '').strip()
        sender = request.values.get('From', '')
        
        # === LOG DETALLADO DE ENTRADA ===
        print("=" * 60)
        print(f"📩 NUEVO MENSAJE RECIBIDO")
        print(f"   📱 Remitente: {sender}")
        print(f"   💬 Mensaje: '{mensaje}'")
        print(f"   📎 Datos completos: {dict(request.values)}")
        print("=" * 60)
        
        # Detectar intención y llamar al módulo correspondiente
        respuesta = procesar_mensaje(mensaje, sender)
        
        # === LOG DE RESPUESTA ===
        print(f"🤖 Respuesta del bot: {respuesta[:100]}..." if len(respuesta) > 100 else f"🤖 Respuesta del bot: {respuesta}")
        print("=" * 60)
        
        # Devolver la respuesta (en formato TwiML)
        from twilio.twiml.messaging_response import MessagingResponse
        resp = MessagingResponse()
        resp.message().body(respuesta)
        return str(resp)
    
    except Exception as e:
        # === LOG DE ERROR ===
        print(f"❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        return "Error interno", 500

def procesar_mensaje(mensaje, sender):
    """
    Procesa el mensaje y determina qué módulo debe responder.
    CON LOGS DETALLADOS.
    """
    print(f"🧠 Procesando mensaje: '{mensaje}' de {sender}")
    mensaje_lower = mensaje.lower().strip()
    
    # Menú principal
    if mensaje_lower in ["hola", "buenos dias", "buenas tardes"]:
        print("✅ Intención: Menú principal")
        return mostrar_menu()
    
    # Opción 1: Presupuesto
    if mensaje_lower == "1" or mensaje_lower.startswith("presupuesto"):
        print("✅ Intención: Presupuesto")
        return iniciar_presupuesto(sender, mensaje)
    
    # Opción 2: Consultar estado
    if mensaje_lower == "2" or "estado" in mensaje_lower:
        print("✅ Intención: Consultar estado")
        return consultar_estado(sender, mensaje)
    
    # Opción 3: Hablar con asesor
    if mensaje_lower == "3" or "asesor" in mensaje_lower:
        print("✅ Intención: Hablar con asesor")
        return iniciar_asesor(sender, mensaje)
    
    # Opción 4: Reclamos o sugerencias
    if mensaje_lower == "4" or "reclamo" in mensaje_lower:
        print("✅ Intención: Reclamos o sugerencias")
        return "📝 *Reclamos y sugerencias*\n\nEscribí tu mensaje y lo vamos a revisar."
    
    # Opción 0: Repetir menú
    if mensaje_lower == "0":
        print("✅ Intención: Repetir menú")
        return mostrar_menu()
    
    # Respuesta por defecto (no entendido)
    print("⚠️ Intención no reconocida")
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
    CON LOGS.
    """
    print(f"🔧 Iniciando presupuesto para {sender}")
    return """
🪑 *Vamos a tomar los datos de tu presupuesto.*

*Paso 1:* ¿Qué producto estás necesitando?
(Ej: *Mesa de roble, Silla rústica, Bajo mesada, Estante flotante, Mueble a medida*)

Respondé con el nombre del producto.
"""

def consultar_estado(sender, mensaje):
    """
    Consulta el estado de un presupuesto o pedido.
    CON LOGS.
    """
    print(f"🔍 Consultando estado para {sender}")
    return """
🔍 *Consultar estado de pedido*

Para consultar el estado de tu pedido, necesito tu **DNI** o **CUIT**.

➡️ *Ejemplo:* 20123456789
"""

def iniciar_asesor(sender, mensaje):
    """
    Inicia el flujo para hablar con un asesor.
    CON LOGS Y MANEJO DE ERRORES.
    """
    print(f"📞 Iniciando flujo de asesor para {sender}")
    try:
        # Simular una respuesta (en producción, aquí iría la lógica real)
        # Esto llama al módulo de asesores
        respuesta = asesores.procesar_solicitud(sender, mensaje)
        print(f"✅ Respuesta del módulo asesores: {respuesta[:50]}...")
        return respuesta
    except Exception as e:
        print(f"❌ Error en módulo asesores: {e}")
        # Si falla, mostramos un mensaje amable
        return """
📞 *Hablar con un asesor*

Estamos teniendo problemas técnicos. Por favor, intentá de nuevo más tarde.

Si es urgente, podés contactarnos directamente al +54 343 472-7811.

😊 Disculpá las molestias.
"""

# Punto de entrada de la aplicación
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🚀 Bot de gestión iniciado...")
    print(f"📡 Escuchando en el puerto {port}")
    print("✅ Logs detallados activados")
    app.run(host='0.0.0.0', port=port, debug=True)
