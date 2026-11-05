# bot.py
# Orquestador principal del sistema de gestión - VERSIÓN DINÁMICA (LEE CONFIGURACIÓN)

from flask import Flask, request
from areas.gestion_ventas import presupuesto, notificaciones, asesores, pagos
from areas.gestion_ventas.clientes import buscar_por_dni
from utils import config
from utils.configuracion import obtener_configuracion
from googleapiclient.discovery import build
import os
import logging
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Diccionarios en memoria para guardar el estado de las conversaciones
sesiones = {}
datos_temporales_presupuesto = {}
datos_accion_presupuesto = {}

# ============================================================
# RUTA DE WHATSAPP (WEBHOOK)
# ============================================================

@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    mensaje = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    
    logger.info(f"📩 NUEVO MENSAJE RECIBIDO")
    logger.info(f"   📱 Remitente: {sender}")
    logger.info(f"   💬 Mensaje: '{mensaje}'")
    
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

# ============================================================
# PROCESAMIENTO PRINCIPAL
# ============================================================

def procesar_mensaje(mensaje, sender):
    logger.info(f"🧠 Procesando mensaje: '{mensaje}' de {sender}")
    mensaje_lower = mensaje.lower().strip()
    mensaje_upper = mensaje.upper().strip()
    
    # 1. VERIFICAR SI ES RESPUESTA DEL DUEÑO (P-XXXX o C-XXXX)
    if re.search(r'P[-]?\d{4}', mensaje_upper):
        return procesar_respuesta_presupuesto(mensaje, sender)
    if re.search(r'C[-]?\d{4}', mensaje_upper):
        return procesar_respuesta_asesor(mensaje, sender)
    
    # 2. VERIFICAR COMANDOS GLOBALES
    if mensaje_lower in ["hola", "buenos dias", "buenas tardes", "menu", "menú", "0"]:
        sesiones[sender] = None
        datos_temporales_presupuesto.pop(sender, None)
        datos_accion_presupuesto.pop(sender, None)
        return mostrar_menu()
    
    if mensaje_lower == "cancelar":
        sesiones[sender] = None
        datos_temporales_presupuesto.pop(sender, None)
        datos_accion_presupuesto.pop(sender, None)
        return cancelar_flujo()
    
    # 3. VERIFICAR ESTADO DE SESIÓN ACTUAL
    estado_actual = sesiones.get(sender)
    if estado_actual:
        if estado_actual == "esperando_producto": return p_producto(sender, mensaje)
        if estado_actual == "esperando_personalizacion": return p_personalizacion(sender, mensaje)
        if estado_actual == "esperando_dni": return p_dni(sender, mensaje)
        if estado_actual == "esperando_nombre": return p_nombre(sender, mensaje)
        if estado_actual == "esperando_telefono": return p_telefono(sender, mensaje)
        
        if estado_actual == "esperando_accion": return p_accion(sender, mensaje)
        if estado_actual == "esperando_modificacion": return p_modificacion(sender, mensaje)
        if estado_actual == "esperando_forma_pago": return p_forma_pago(sender, mensaje)
        
        if estado_actual == "esperando_consulta_asesor": 
            return asesores.procesar_consulta(sender, mensaje)
        
        if estado_actual == "esperando_dni_estado": return p_estado(sender, mensaje)

    # 4. VERIFICAR OPCIONES DEL MENÚ PRINCIPAL
    if mensaje_lower == "1" or mensaje_lower == "presupuesto":
        return iniciar_presupuesto(sender)
    if mensaje_lower == "2" or mensaje_lower == "estado":
        return iniciar_estado(sender)
    if mensaje_lower == "3" or mensaje_lower == "asesor":
        sesiones[sender] = "esperando_consulta_asesor"
        return "📞 *Hablar con un asesor*\n\nDecime tu consulta y un asesor te va a responder por este mismo chat.\n\n👉 Escribí tu mensaje:"
    if mensaje_lower == "4" or mensaje_lower == "reclamo":
        sesiones[sender] = None
        return "📝 *Reclamos y sugerencias*\n\nEscribí tu mensaje y lo vamos a revisar."

    return no_entendido()

# ============================================================
# RESPUESTAS DEL DUEÑO
# ============================================================

def procesar_respuesta_presupuesto(mensaje, sender):
    codigo_match = re.search(r'P[-]?(\d{4})', mensaje.upper())
    if not codigo_match: return no_entendido()
    codigo = f"P-{codigo_match.group(1)}"
    
    partes = re.split(r'P[-]?\d{4}\s*[:]?\s*', mensaje, maxsplit=1)
    respuesta_texto = partes[1].strip() if len(partes) > 1 else ""
    
    if not respuesta_texto:
        return "⚠️ No escribiste el presupuesto. Usá el formato: P0001 (tu mensaje)"
    
    pedido = presupuesto.obtener_presupuesto(codigo)
    if not pedido:
        notificaciones.notificar_error_respuesta(codigo)
        return f"⚠️ No se encontró el presupuesto {codigo}."
    
    # Extracción inteligente del precio
    precio_match = re.search(r'\$\s*(\d{1,3}(?:\.\d{3})*|\d+)', respuesta_texto)
    if not precio_match:
        numeros = re.findall(r'\d{1,3}(?:\.\d{3})*|\d+', respuesta_texto)
        if numeros:
            precio_str = max(numeros, key=lambda x: int(x.replace('.', '')))
            presupuesto.actualizar_precio(codigo, precio_str.replace('.', ''))
    else:
        precio_str = precio_match.group(1).replace('.', '')
        presupuesto.actualizar_precio(codigo, precio_str)

    presupuesto.actualizar_estado(codigo, presupuesto.ESTADOS["ENVIADO"])
    notificaciones.notificar_respuesta_dueño(codigo, respuesta_texto)
    
    pedido_actualizado = presupuesto.obtener_presupuesto(codigo)
    notificaciones.notificar_presupuesto_cliente(codigo, pedido_actualizado, respuesta_texto)
    
    telefono_cliente = pedido_actualizado['telefono'].replace('whatsapp:', '')
    sesiones[telefono_cliente] = "esperando_accion"
    datos_accion_presupuesto[telefono_cliente] = {"numero": codigo}
    
    return "✅ Tu respuesta fue enviada al cliente."

def procesar_respuesta_asesor(mensaje, sender):
    codigo_match = re.search(r'C[-]?(\d{4})', mensaje.upper())
    if not codigo_match: return no_entendido()
    codigo = f"C-{codigo_match.group(1)}"
    
    partes = re.split(r'C[-]?\d{4}\s*[:]?\s*', mensaje, maxsplit=1)
    respuesta_texto = partes[1].strip() if len(partes) > 1 else ""
    
    if not respuesta_texto:
        return "⚠️ No escribiste el mensaje. Usá el formato: C0001 (tu mensaje)"
    
    cliente_telefono = asesores.obtener_telefono_cliente(codigo)
    if not cliente_telefono:
        notificaciones.notificar_error_respuesta(codigo)
        return "⚠️ No se encontró la consulta."
    
    notificaciones.enviar_whatsapp(cliente_telefono, f"📞 *Un asesor te responde:*\n{respuesta_texto}")
    
    try:
        service = build('sheets', 'v4', credentials=config.CREDENTIALS)
        result = service.spreadsheets().values().get(spreadsheetId=config.SPREADSHEETS["CONSULTAS"], range='A:F').execute()
        datos = result.get('values', [])
        for i, fila in enumerate(datos):
            if len(fila) > 0 and fila[0] == codigo:
                service.spreadsheets().values().update(
                    spreadsheetId=config.SPREADSHEETS["CONSULTAS"],
                    range=f'E{i+1}', valueInputOption='USER_ENTERED', body={'values': [["Respondida"]]}
                ).execute()
                break
    except Exception as e:
        logger.error(f"Error actualizando CONSULTAS: {e}")

    notificaciones.enviar_whatsapp(sender, f"✅ *Tu respuesta fue enviada al cliente*\n\n📋 Consulta: {codigo}")
    return "✅ Tu respuesta fue enviada al cliente."

# ============================================================
# FLUJO DE PRESUPUESTO (PASO A PASO)
# ============================================================

def iniciar_presupuesto(sender):
    sesiones[sender] = "esperando_producto"
    datos_temporales_presupuesto[sender] = {}
    conf = obtener_configuracion()
    nombre = conf.get('nombre_negocio', 'nuestro negocio')
    return f"""
🪑 *Presupuesto en {nombre} - Paso 1/3*

📦 ¿Qué producto estás necesitando?
*Ejemplos:* Mesa de roble, Silla rústica, Bajo mesada.

💡 *Tip:* En cualquier momento podés escribir CANCELAR para salir.

👉 Escribí el nombre y detalles del producto:
"""

def p_producto(sender, mensaje):
    datos_temporales_presupuesto[sender]["producto"] = mensaje
    sesiones[sender] = "esperando_personalizacion"
    return """
🎨 *Presupuesto - Paso 2/3*

✨ ¿Qué personalización necesitas para este producto?
*Ejemplos:* Medidas, color, terminación, tipo de madera.

👉 Escribí los detalles de personalización:
"""

def p_personalizacion(sender, mensaje):
    datos_temporales_presupuesto[sender]["personalizacion"] = mensaje
    sesiones[sender] = "esperando_dni"
    return """
📋 *Presupuesto - Paso 3/3*

🆔 Para crear tu presupuesto, necesito tu DNI o CUIT.
⚠️ *Importante:* Escribilo sin puntos ni guiones. Ej: 20123456789

👉 Escribí tu número de documento:
"""

def p_dni(sender, mensaje):
    if not mensaje.isdigit() or len(mensaje) < 7:
        return "❌ *DNI inválido*\n\nDebe tener al menos 7 dígitos y solo números.\n👉 Escribilo de nuevo o CANCELAR:"
    
    datos_temporales_presupuesto[sender]["dni"] = mensaje
    cliente = buscar_por_dni(mensaje)
    
    if cliente:
        return crear_presupuesto_final(sender, cliente)
    
    sesiones[sender] = "esperando_nombre"
    return """
👤 *Cliente nuevo*

No encontré tu DNI. Necesito unos datos más:
📝 ¿Cuál es tu nombre completo?

👉 Escribí tu nombre y apellido:
"""

def p_nombre(sender, mensaje):
    datos_temporales_presupuesto[sender]["nombre"] = mensaje
    sesiones[sender] = "esperando_telefono"
    return """
📞 *Un paso más*

📱 ¿Cuál es tu número de teléfono?
*Ejemplo:* 3434123456

👉 Escribí tu teléfono:
"""

def p_telefono(sender, mensaje):
    if not mensaje.isdigit() or len(mensaje) < 7:
        return "❌ *Teléfono inválido*\n\nDebe tener al menos 7 dígitos y solo números.\n👉 Escribilo de nuevo:"
    
    datos_temporales_presupuesto[sender]["telefono"] = mensaje
    cliente = {
        "dni": datos_temporales_presupuesto[sender].get("dni", ""),
        "nombre": datos_temporales_presupuesto[sender].get("nombre", ""),
        "telefono": datos_temporales_presupuesto[sender].get("telefono", "")
    }
    return crear_presupuesto_final(sender, cliente)

def crear_presupuesto_final(sender, cliente):
    datos = datos_temporales_presupuesto.get(sender, {})
    producto = datos.get("producto", "")
    personalizacion = datos.get("personalizacion", "")
    conf = obtener_configuracion()
    nombre_negocio = conf.get('nombre_negocio', 'nuestro negocio')
    
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

📌 *¿Qué sigue?*
Un asesor de {nombre_negocio} lo revisará y te responderá por este chat en las próximas 24 horas hábiles.

👉 Escribí MENU para volver al inicio.
💡 Podés salir tranquilo, igual te llegará la respuesta.
"""
    else:
        return "❌ Hubo un error al guardar el presupuesto. Intentá de nuevo más tarde."

# ============================================================
# ACCIONES DEL CLIENTE
# ============================================================

def p_accion(sender, mensaje):
    datos = datos_accion_presupuesto.get(sender, {})
    numero = datos.get("numero")
    if not numero: return mostrar_menu()
    
    pedido = presupuesto.obtener_presupuesto(numero)
    if not pedido: return "❌ Presupuesto no encontrado."

    if mensaje == "1": # Aceptar
        presupuesto.actualizar_estado(numero, presupuesto.ESTADOS["ACEPTADO"])
        notificaciones.notificar_aceptacion_cliente(numero, {"nombre": pedido["nombre"], "telefono": pedido["telefono"]}, pedido)
        sesiones[sender] = "esperando_forma_pago"
        return pagos.mostrar_opciones_pago()

    elif mensaje == "2": # Rechazar
        presupuesto.actualizar_estado(numero, presupuesto.ESTADOS["RECHAZADO"])
        notificaciones.notificar_rechazo_cliente(numero, {"nombre": pedido["nombre"], "telefono": pedido["telefono"]}, pedido)
        sesiones[sender] = None
        datos_accion_presupuesto.pop(sender, None)
        return """
❌ *Presupuesto rechazado*

Entendemos que no se ajusta a lo que buscabas.

📌 ¿Qué querés hacer?
1️⃣ Pedir un presupuesto nuevo
2️⃣ Hablar con un asesor
3️⃣ Volver al menú

👉 Escribí el número de la opción:
"""

    elif mensaje == "3": # Modificar
        sesiones[sender] = "esperando_modificacion"
        return """
✏️ *Solicitar modificaciones*

Contanos qué cambios te gustaría hacer (ej: precio, material, medidas).

👉 Escribí los cambios que deseas:
"""

    elif mensaje == "4": # Asesor
        sesiones[sender] = "esperando_consulta_asesor"
        datos_accion_presupuesto.pop(sender, None)
        return "📞 *Hablar con un asesor*\n\nDecime tu consulta y un asesor te responderá por aquí.\n\n👉 Escribí tu mensaje:"
    
    return "❌ Opción no válida. Elegí 1, 2, 3 o 4."

def p_modificacion(sender, mensaje):
    datos = datos_accion_presupuesto.get(sender, {})
    numero = datos.get("numero")
    pedido = presupuesto.obtener_presupuesto(numero)
    
    presupuesto.guardar_modificacion(numero, mensaje)
    presupuesto.actualizar_estado(numero, presupuesto.ESTADOS["MODIFICADO"])
    notificaciones.notificar_modificacion_cliente(numero, {"nombre": pedido["nombre"], "telefono": pedido["telefono"]}, pedido, mensaje)
    
    sesiones[sender] = None
    datos_accion_presupuesto.pop(sender, None)
    return """
✅ *Modificaciones enviadas*

Un asesor revisará tus cambios y te responderá por este chat.

👉 Escribí MENU para volver al inicio.
"""

def p_forma_pago(sender, mensaje):
    datos = datos_accion_presupuesto.get(sender, {})
    numero = datos.get("numero")
    pedido = presupuesto.obtener_presupuesto(numero)
    conf = obtener_configuracion()
    
    if mensaje == "1":
        forma = "Transferencia bancaria"
        msg = pagos.transferencia(pedido, conf)
    elif mensaje == "2":
        forma = "Efectivo"
        msg = pagos.efectivo(pedido, conf)
    elif mensaje == "3":
        forma = "Cuotas de la casa"
        msg = pagos.cuotas(pedido, conf)
    else:
        return "❌ Opción no válida. Elegí 1, 2 o 3."
    
    presupuesto.actualizar_forma_pago(numero, forma)
    notificaciones.notificar_forma_pago(numero, {"nombre": pedido["nombre"], "telefono": pedido["telefono"]}, pedido, forma)
    
    sesiones[sender] = None
    datos_accion_presupuesto.pop(sender, None)
    return msg

# ============================================================
# CONSULTAR ESTADO
# ============================================================

def iniciar_estado(sender):
    sesiones[sender] = "esperando_dni_estado"
    return """
🔍 *Consultar estado de pedido*

Para consultar el estado de tu pedido, necesito tu *DNI* o *CUIT*.

👉 Escribí tu número de documento:
"""

def p_estado(sender, mensaje):
    if not mensaje.isdigit() or len(mensaje) < 7:
        return "❌ *DNI inválido*\n\nDebe tener al menos 7 dígitos y solo números.\n👉 Escribilo de nuevo:"
    
    pedidos = presupuesto.obtener_presupuestos_por_dni(mensaje)
    sesiones[sender] = None
    
    if not pedidos:
        return "🔍 No encontramos pedidos asociados a este DNI.\n\n👉 Escribí MENU para volver."
    
    msj = "🔍 *Estado de tus pedidos:*\n\n"
    for p in pedidos:
        msj += f"📋 *Pedido {p['numero']}*\n📦 {p['producto']}\n📌 Estado: *{p['estado']}*\n📅 {p['fecha']}\n---\n"
    
    msj += "👉 Escribí MENU para volver al inicio."
    return msj

# ============================================================
# UTILIDADES
# ============================================================

def mostrar_menu():
    conf = obtener_configuracion()
    nombre = conf.get('nombre_negocio', 'nuestro negocio')
    return f"""
👋 *Bienvenido a {nombre}*

1️⃣ Presupuesto
2️⃣ Consultar estado
3️⃣ Hablar con asesor
4️⃣ Reclamos o sugerencias
0️⃣ Repetir menú

📝 *Ejemplos:* Mesa de roble, Silla rústica.

💬 Escribí 'Ayuda' para más detalles.
"""

def cancelar_flujo():
    return """
❌ *Operación cancelada*

Has salido del área actual.

👋 *Menú principal*
1️⃣ Presupuesto | 2️⃣ Consultar estado | 3️⃣ Asesor | 4️⃣ Reclamos

👉 Escribí el número de la opción:
"""

def no_entendido():
    return """
🤔 *No entendí lo que escribiste.*

✅ *Opciones válidas:*
• 'Hola' para ver el menú
• '1' para pedir un presupuesto
• '2' para consultar el estado
• '3' para hablar con un asesor
• '4' para reclamos

💡 Escribí 'Ayuda' o 'MENU'.
"""

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info("🚀 Bot de gestión iniciado...")
    app.run(host='0.0.0.0', port=port, debug=False)
