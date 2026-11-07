# bot.py
# Orquestador principal - 100% Genérico (Prompts solo DNI)

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
    media_url = request.values.get('MediaUrl0', '')
    media_type = request.values.get('MediaContentType0', '')
    
    logger.info(f"📩 Mensaje de {sender}: '{mensaje}' | Media: {media_type}")

    if media_url:
        return procesar_media(sender, media_url, media_type)
    
    try:
        respuesta = procesar_mensaje(mensaje, sender)
        from twilio.twiml.messaging_response import MessagingResponse
        resp = MessagingResponse()
        resp.message().body(respuesta)
        return str(resp)
    except Exception as e:
        logger.error(f"❌ ERROR: {e}")
        return "Error interno", 500
    finally:
        gc.collect()

def procesar_mensaje(mensaje, sender):
    mensaje_lower = mensaje.lower().strip()
    mensaje_upper = mensaje.upper().strip()
    conf = obtener_configuracion()
    nombre = conf.get('nombre_negocio', 'Nuestro Negocio')
    
    # 1. RESPUESTAS DEL DUEÑO
    if re.search(r'P[-]?\d{4}', mensaje_upper):
        return procesar_respuesta_presupuesto(mensaje, sender)
    if re.search(r'C[-]?\d{4}', mensaje_upper):
        return procesar_respuesta_asesor(mensaje, sender)
    
    # 2. COMANDOS GLOBALES
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
    
    # 3. VERIFICAR ESTADO DE SESIÓN
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
        if estado == "esperando_dni_pendiente": return p_dni_pendiente(sender, mensaje)

    # 4. OPCIONES DEL MENÚ PRINCIPAL
    if mensaje_lower in ["1", "presupuesto"]: return iniciar_presupuesto(sender)
    if mensaje_lower in ["2", "estado"]: return iniciar_estado(sender)
    if mensaje_lower in ["3", "asesor"]:
        sesiones[sender] = "esperando_consulta_asesor"
        return f"📞 *Hablar con un asesor de {nombre}*\n\nDecime tu consulta y te responderemos por aquí.\n\n👉 Escribí tu mensaje:"
    if mensaje_lower in ["4", "reclamo"]:
        sesiones[sender] = None
        return "📝 *Reclamos y sugerencias*\n\nEscribí tu mensaje y lo vamos a revisar."
    
    if mensaje_lower in ["5", "pendientes"]:
        sesiones[sender] = "esperando_dni_pendiente"
        return "🔍 Para buscar tus presupuestos pendientes, por favor escribí tu DNI (sin puntos ni guiones):"

    return no_entendido()

# ... (Las funciones procesar_respuesta_presupuesto y procesar_respuesta_asesor 
# se mantienen exactamente igual que antes).

# --- FLUJO DE PRESUPUESTO ---
def iniciar_presupuesto(sender):
    sesiones[sender] = "esperando_producto"
    datos_temporales_presupuesto[sender] = {}
    conf = obtener_configuracion()
    nombre = conf.get('nombre_negocio', 'Nuestro Negocio')
    return f"""
📝 *Presupuesto en {nombre} - Paso 1/3*

¿Qué producto estás necesitando?
*Ejemplos:* Mesa de roble, Silla rústica, Bajo mesada.

💡 *Tip:* En cualquier momento podés escribir CANCELAR para salir.

👉 Escribí el nombre y detalles del producto:
"""

def p_producto(sender, mensaje):
    datos_temporales_presupuesto[sender]["producto"] = mensaje
    sesiones[sender] = "esperando_personalizacion"
    return "🎨 *Presupuesto - Paso 2/3*\n\n✨ ¿Qué personalización necesitas?\n👉 Escribí los detalles:"

def p_personalizacion(sender, mensaje):
    datos_temporales_presupuesto[sender]["personalizacion"] = mensaje
    sesiones[sender] = "esperando_dni"
    return "📋 *Presupuesto - Paso 3/3*\n\n🆔 Escribí tu **DNI** (sin puntos ni guiones):"

def p_dni(sender, mensaje):
    if not mensaje.isdigit() or len(mensaje) < 7:
        return "❌ *DNI inválido*\n👉 Escribilo de nuevo o CANCELAR:"
    datos_temporales_presupuesto[sender]["dni"] = mensaje
    cliente = buscar_por_dni(mensaje)
    if cliente: 
        return crear_presupuesto_final(sender, cliente)
    
    sesiones[sender] = "esperando_nombre"
    return "👤 *Cliente nuevo*\n\n📝 ¿Cuál es tu nombre completo?\n👉 Escribí tu nombre:"

def p_nombre(sender, mensaje):
    datos_temporales_presupuesto[sender]["nombre"] = mensaje
    sesiones[sender] = "esperando_telefono"
    return "📞 *Un paso más*\n\n📱 ¿Cuál es tu teléfono?\n👉 Escribilo:"

def p_telefono(sender, mensaje):
    numero_real = sender.replace('whatsapp:', '').strip()
    datos_temporales_presupuesto[sender]["telefono"] = numero_real
    
    cliente = {
        "dni": datos_temporales_presupuesto[sender].get("dni", ""),
        "nombre": datos_temporales_presupuesto[sender].get("nombre", ""),
        "telefono": numero_real
    }
    return crear_presupuesto_final(sender, cliente)

def crear_presupuesto_final(sender, cliente):
    try:
        datos = datos_temporales_presupuesto.get(sender, {})
        producto = datos.get("producto", "")
        personalizacion = datos.get("personalizacion", "")
        conf = obtener_configuracion()
        nombre = conf.get('nombre_negocio', 'Nuestro Negocio')
        
        resultado = presupuesto.crear_presupuesto(
            sender=sender, producto=producto, personalizacion=personalizacion,
            dni=cliente.get("dni"), nombre=cliente.get("nombre"), telefono=cliente.get("telefono")
        )
        sesiones[sender] = None
        datos_temporales_presupuesto.pop(sender, None)
        
        if resultado and resultado.get("estado"):
            num = resultado["numero"]
            notificaciones.notificar_nuevo_presupuesto(num, resultado["cliente"], producto, personalizacion)
            return f"""
✅ *Presupuesto creado con éxito*

📋 *Número:* {num}
👤 Cliente: {resultado['cliente']['nombre']}
📦 Producto: {producto}

📌 Un asesor de {nombre} lo revisará y te responderá pronto.

👉 Escribí MENU para volver al inicio.
"""
        else:
            return f"❌ Error al guardar: {resultado.get('error', 'Desconocido')}"
            
    except Exception as e:
        logger.error(f"❌ CRASH EVITADO en crear_presupuesto_final: {e}")
        sesiones[sender] = None
        return f"❌ Error interno, enviame esto: {str(e)}"

# ... (Las funciones p_accion, p_modificacion, p_forma_pago, p_cuotas se mantienen igual).

# --- OPCIÓN 5 ---
def p_dni_pendiente(sender, mensaje):
    if not mensaje.isdigit() or len(mensaje) < 7:
        return "❌ *DNI inválido*\n👉 Escribilo de nuevo (sin puntos ni guiones) o CANCELAR:"
    
    pendientes = presupuesto.obtener_presupuestos_pendientes(mensaje)
    sesiones[sender] = None
    
    if not pendientes:
        return "📋 No encontramos presupuestos pendientes para ese DNI.\n\n👉 Escribí MENU para volver."
    
    p = pendientes[-1]
    sesiones[sender] = "esperando_accion"
    datos_accion_presupuesto[sender] = {"numero": p["numero"]}
    
    return f"""
📋 *Presupuesto pendiente encontrado*

Número: *{p['numero']}*
Producto: {p['producto']}
💰 Precio: ${p['precio']}

📌 ¿Qué querés hacer?

1️⃣ Aceptar el presupuesto
2️⃣ Rechazar el presupuesto
3️⃣ Solicitar modificaciones

👉 Escribí el número de la opción que desees.
"""

# --- ESTADO ---
def iniciar_estado(sender):
    sesiones[sender] = "esperando_dni_estado"
    return "🔍 *Consultar estado*\n\n👉 Escribí tu **DNI** (sin puntos ni guiones):"

def p_estado(sender, mensaje):
    if not mensaje.isdigit() or len(mensaje) < 7:
        return "❌ *DNI inválido*\n👉 Escribilo de nuevo:"
    pedidos = presupuesto.obtener_presupuestos_por_dni(mensaje)
    sesiones[sender] = None
    if not pedidos: return "🔍 *No se encontraron pedidos*\n\nNo encontramos pedidos asociados a este DNI.\n\n👉 Escribí MENU para volver."
    
    msj = "🔍 *Tus pedidos:*\n\n"
    for p in pedidos:
        msj += f"📋 *{p['numero']}*\n📦 {p['producto']}\n📌 {p['estado']}\n---\n"
    return msj

# --- UTILS ---
def mostrar_menu():
    conf = obtener_configuracion()
    nombre = conf.get('nombre_negocio', 'Nuestro Negocio')
    return f"""
👋 *Bienvenido a {nombre}*

1️⃣ Presupuesto
2️⃣ Consultar estado
3️⃣ Hablar con asesor
4️⃣ Reclamos
5️⃣ Ver presupuestos pendientes
0️⃣ Repetir menú

💬 Escribí 'Ayuda' para más detalles.
"""

def no_entendido():
    return "🤔 *No entendí.*\n\n✅ Escribí 'Hola' o 'MENU' para ver las opciones."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
