# bot.py
# Orquestador principal - 100% Genérico (Comandos globales con prioridad)

from flask import Flask, request
from areas.gestion_ventas import presupuesto, notificaciones, asesores, pagos
from areas.gestion_ventas.clientes import buscar_por_dni
from utils import config
from utils.configuracion import obtener_configuracion
from googleapiclient.discovery import build
import os
import logging
import re
import gc

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

sesiones = {}
datos_temporales_presupuesto = {}
datos_accion_presupuesto = {}

@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    mensaje = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    logger.info(f"📩 Mensaje de {sender}: '{mensaje}'")
    
    try:
        respuesta = procesar_mensaje(mensaje, sender)
        from twilio.twiml.messaging_response import MessagingResponse
        resp = MessagingResponse()
        resp.message().body(respuesta)
        return str(resp)
    except Exception as e:
        logger.error(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return "Error interno", 500
    finally:
        gc.collect()

def procesar_mensaje(mensaje, sender):
    mensaje_lower = mensaje.lower().strip()
    mensaje_upper = mensaje.upper().strip()
    conf = obtener_configuracion()
    nombre = conf.get('nombre_negocio', 'Nuestro Negocio')
    
    # =========================================================
    # 1. RESPUESTAS DEL DUEÑO (Prioridad absoluta)
    # =========================================================
    if re.search(r'P[-]?\d{4}', mensaje_upper):
        return procesar_respuesta_presupuesto(mensaje, sender)
    if re.search(r'C[-]?\d{4}', mensaje_upper):
        return procesar_respuesta_asesor(mensaje, sender)
    
    # =========================================================
    # 2. COMANDOS GLOBALES (Prioridad absoluta SIEMPRE)
    # =========================================================
    if mensaje_lower in ["hola", "buenos dias", "buenas tardes", "menu", "menú", "0"]:
        sesiones[sender] = None
        datos_temporales_presupuesto.pop(sender, None)
        datos_accion_presupuesto.pop(sender, None)
        return mostrar_menu()
    
    if mensaje_lower == "cancelar":
        sesiones[sender] = None
        datos_temporales_presupuesto.pop(sender, None)
        datos_accion_presupuesto.pop(sender, None)
        return "❌ *Operación cancelada*\n\nHas salido del área actual.\n\n👉 Escribí MENU para volver."
    
    # =========================================================
    # 3. VERIFICAR ESTADO DE SESIÓN (Si el cliente está en medio de un flujo)
    # =========================================================
    estado = sesiones.get(sender)
    if estado:
        if estado == "esperando_producto": return p_producto(sender, mensaje)
        if estado == "esperando_personalizacion": return p_personalizacion(sender, mensaje)
        if estado == "esperando_dni": return p_dni(sender, mensaje)
        if estado == "esperando_nombre": return p_nombre(sender, mensaje)
        if estado == "esperando_telefono": return p_telefono(sender, mensaje)
        if estado == "esperando_accion": return p_accion(sender, mensaje)
        if estado == "esperando_modificacion": return p_modificacion(sender, mensaje)
        if estado == "esperando_forma_pago": return p_forma_pago(sender, mensaje)
        if estado == "esperando_cuotas": return p_cuotas(sender, mensaje)
        if estado == "esperando_consulta_asesor": return asesores.procesar_consulta(sender, mensaje)
        if estado == "esperando_dni_estado": return p_estado(sender, mensaje)

    # =========================================================
    # 4. OPCIONES DEL MENÚ PRINCIPAL
    # =========================================================
    if mensaje_lower in ["1", "presupuesto"]: return iniciar_presupuesto(sender)
    if mensaje_lower in ["2", "estado"]: return iniciar_estado(sender)
    if mensaje_lower in ["3", "asesor"]:
        sesiones[sender] = "esperando_consulta_asesor"
        return f"📞 *Hablar con un asesor de {nombre}*\n\nDecime tu consulta y te responderemos por aquí.\n\n👉 Escribí tu mensaje:"
    if mensaje_lower in ["4", "reclamo"]:
        sesiones[sender] = None
        return "📝 *Reclamos y sugerencias*\n\nEscribí tu mensaje y lo vamos a revisar."

    return no_entendido()

# (El resto de las funciones: procesar_respuesta_presupuesto, procesar_respuesta_asesor,
# iniciar_presupuesto, p_producto, p_personalizacion, p_dni, p_nombre, p_telefono, 
# crear_presupuesto_final, p_accion, p_modificacion, p_forma_pago, p_cuotas, 
# iniciar_estado, p_estado, mostrar_menu, no_entendido se mantienen EXACTAMENTE IGUAL 
# que en el mensaje anterior. No las repito para no hacer el mensaje kilométrico, 
# solo copiá el bloque de procesar_mensaje de arriba y reemplazalo en tu archivo).
