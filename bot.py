# bot.py
# Orquestador principal del sistema de gestión - VERSIÓN CORREGIDA

from flask import Flask, request
from areas.gestion_ventas import presupuesto, notificaciones, asesores, pagos
from areas.gestion_ventas.clientes import buscar_por_dni, crear_cliente
from utils import config
from googleapiclient.discovery import build
import os
import sys
import logging
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

sesiones = {}

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

# ============================================================
# PROCESAMIENTO PRINCIPAL
# ============================================================

def procesar_mensaje(mensaje, sender):
    logger.info(f"🧠 Procesando mensaje: '{mensaje}' de {sender}")
    mensaje_lower = mensaje.lower().strip()
    mensaje_upper = mensaje.upper().strip()
    
    # === VERIFICAR ESTADO DE SESIÓN PRIMERO ===
    # Esto evita que palabras como "presupuesto" dentro del flujo de asesor
    # activen el flujo de presupuesto
    estado_actual = sesiones.get(sender)
    
    if estado_actual:
        # Presupuesto
        if estado_actual == "esperando_producto_presupuesto":
            return procesar_producto_presupuesto(sender, mensaje)
        elif estado_actual == "esperando_personalizacion_presupuesto":
            return procesar_personalizacion_presupuesto(sender, mensaje)
        elif estado_actual == "esperando_dni_presupuesto":
            return procesar_dni_presupuesto(sender, mensaje)
        elif estado_actual == "esperando_nombre_presupuesto":
            return procesar_nombre_presupuesto(sender, mensaje)
        elif estado_actual == "esperando_telefono_presupuesto":
            return procesar_telefono_presupuesto(sender, mensaje)
        elif estado_actual == "esperando_accion_presupuesto":
            return procesar_accion_presupuesto(sender, mensaje)
        elif estado_actual == "esperando_modificacion_presupuesto":
            return procesar_modificacion_presupuesto(sender, mensaje)
        elif estado_actual == "esperando_forma_pago":
            return procesar_forma_pago(sender, mensaje)
        
        # Asesor
        elif estado_actual == "esperando_consulta_asesor":
            return procesar_consulta_asesor(sender, mensaje)
        
        # Estado
        elif estado_actual == "esperando_dni_estado":
            return procesar_dni_estado(sender, mensaje)
    
    # === VERIFICAR SI ES RESPUESTA DE ASESOR (C-XXXX) ===
    if mensaje_upper.startswith("RESPUESTA C-") or mensaje_upper.startswith("C-"):
        return procesar_respuesta_asesor(mensaje, sender)
    
    # === VERIFICAR SI ES RESPUESTA DE PRESUPUESTO (P-XXXX) ===
    if mensaje_upper.startswith("RESPUESTA P-") or mensaje_upper.startswith("P-"):
        return procesar_respuesta_presupuesto(mensaje, sender)
    
    # === VERIFICAR SI ES RESPUESTA SIMPLE (P0001 o C0005) ===
    codigo_presupuesto = extraer_codigo_presupuesto(mensaje_upper)
    if codigo_presupuesto:
        return procesar_respuesta_presupuesto_simple(mensaje, sender, codigo_presupuesto)
    
    codigo_consulta = extraer_codigo_consulta(mensaje_upper)
    if codigo_consulta:
        return procesar_respuesta_asesor_simple(mensaje, sender, codigo_consulta)
    
    # === VERIFICAR COMANDOS PRINCIPALES ===
    if mensaje_lower in ["hola", "buenos dias", "buenas tardes"]:
        logger.info("   ✅ Intención: Menú principal")
        sesiones[sender] = None
        return mostrar_menu()
    
    # CORREGIDO: Solo detecta "presupuesto" exacto, no cualquier mensaje que contenga la palabra
    if mensaje_lower == "1" or mensaje_lower == "presupuesto":
        logger.info("   ✅ Intención: Presupuesto")
        return iniciar_presupuesto(sender)
    
    if mensaje_lower == "2" or mensaje_lower == "estado" or "estado" in mensaje_lower:
        logger.info("   ✅ Intención: Consultar estado")
        sesiones[sender] = None
        return consultar_estado(sender)
    
    if mensaje_lower == "3" or mensaje_lower == "asesor":
        logger.info("   ✅ Intención: Hablar con asesor")
        return iniciar_asesor(sender)
    
    if mensaje_lower == "4" or mensaje_lower == "reclamo" or mensaje_lower == "sugerencia":
        logger.info("   ✅ Intención: Reclamos o sugerencias")
        sesiones[sender] = None
        return "📝 *Reclamos y sugerencias*\n\nEscribí tu mensaje y lo vamos a revisar."
    
    if mensaje_lower == "0" or mensaje_lower == "menu" or mensaje_lower == "menú":
        logger.info("   ✅ Intención: Volver al menú")
        sesiones[sender] = None
        return mostrar_menu()
    
    if mensaje_lower == "cancelar":
        logger.info("   ✅ Intención: Cancelar")
        sesiones[sender] = None
        return cancelar_flujo()
    
    logger.warning("   ⚠️ Intención no reconocida")
    return no_entendido()

# ============================================================
# FUNCIONES DE EXTRACCIÓN DE CÓDIGOS
# ============================================================

def extraer_codigo_presupuesto(texto):
    """Extrae un código de presupuesto (P-0001 o P0001) del texto."""
    match = re.search(r'P[-]?(\d{4})', texto)
    if match:
        return f"P-{match.group(1)}"
    return None

def extraer_codigo_consulta(texto):
    """Extrae un código de consulta (C-0001 o C0001) del texto."""
    match = re.search(r'C[-]?(\d{4})', texto)
    if match:
        return f"C-{match.group(1)}"
    return None

# ============================================================
# PROCESAMIENTO DE RESPUESTAS DEL DUEÑO
# ============================================================

def procesar_respuesta_asesor(mensaje, sender):
    """Procesa respuesta del dueño a consulta (C-XXXX)."""
    logger.info("   📞 Procesando respuesta de asesor a consulta")
    
    codigo = extraer_codigo_consulta(mensaje)
    if not codigo:
        return no_entendido()
    
    partes = re.split(r'C[-]?\d{4}\s*[:]?\s*', mensaje, maxsplit=1)
    if len(partes) < 2:
        return "⚠️ No se encontró el mensaje. Usá el formato: C0001 (tu mensaje)"
    
    respuesta_texto = partes[1].strip()
    if not respuesta_texto:
        return "⚠️ No escribiste ningún mensaje. Usá el formato: C0001 (tu mensaje)"
    
    cliente_telefono = asesores.obtener_telefono_cliente(codigo)
    if not cliente_telefono:
        notificaciones.notificar_error_respuesta(codigo)
        return "⚠️ No se encontró la consulta."
    
    sender_clean = sender.replace('whatsapp:', '') if sender.startswith('whatsapp:') else sender
    cliente_clean = cliente_telefono.replace('whatsapp:', '') if cliente_telefono.startswith('whatsapp:') else cliente_telefono
    
    if sender_clean == cliente_clean:
        return "✅ Mensaje registrado. (No te enviamos el mensaje a ti mismo como cliente)"
    
    from twilio.rest import Client
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    from_number = os.environ.get('TWILIO_WHATSAPP_NUMBER')
    
    if not account_sid or not auth_token or not from_number:
        return "⚠️ Error al enviar la respuesta."
    
    client = Client(account_sid, auth_token)
    
    # CORREGIDO: Evitar doble prefijo whatsapp:
    if cliente_telefono.startswith('whatsapp:'):
        to = cliente_telefono
    else:
        to = f'whatsapp:{cliente_telefono}'
    
    client.messages.create(
        from_=f'whatsapp:{from_number}',
        body=f"📞 *Un asesor te responde:*\n{respuesta_texto}",
        to=to
    )
    logger.info(f"✅ Respuesta enviada al cliente {cliente_telefono}")
    
    # ✅ NUEVO: Enviar confirmación al asesor
    try:
        client.messages.create(
            from_=f'whatsapp:{from_number}',
            body=f"✅ *Tu respuesta fue enviada al cliente*\n\n📋 Consulta: {codigo}\n📩 El cliente ya recibió tu mensaje.",
            to=sender
        )
        logger.info(f"✅ Confirmación enviada al asesor {sender}")
    except Exception as e:
        logger.error(f"❌ Error al enviar confirmación al asesor: {e}")
    
    # Actualizar estado en CONSULTAS
    try:
        service = build('sheets', 'v4', credentials=config.CREDENTIALS)
        result = service.spreadsheets().values().get(
            spreadsheetId=config.SPREADSHEETS["CONSULTAS"],
            range='A:F'
        ).execute()
        datos = result.get('values', [])
        
        for i, fila in enumerate(datos):
            if len(fila) > 0 and fila[0] == codigo:
                fila_excel = i + 1
                rango_celda = f'E{fila_excel}'
                body = {'values': [["Respondida"]]}
                service.spreadsheets().values().update(
                    spreadsheetId=config.SPREADSHEETS["CONSULTAS"],
                    range=rango_celda,
                    valueInputOption='USER_ENTERED',
                    body=body
                ).execute()
                logger.info(f"✅ Consulta {codigo} marcada como Respondida")
                break
    except Exception as e:
        logger.error(f"❌ Error al actualizar estado: {e}")
    
    return "✅ Tu respuesta fue enviada al cliente."

def procesar_respuesta_presupuesto(mensaje, sender):
    """Procesa respuesta del dueño a presupuesto (P-XXXX)."""
    logger.info("   📞 Procesando respuesta de asesor a presupuesto")
    
    codigo = extraer_codigo_presupuesto(mensaje)
    if not codigo:
        return no_entendido()
    
    partes = re.split(r'P[-]?\d{4}\s*[:]?\s*', mensaje, maxsplit=1)
    if len(partes) < 2:
        return "⚠️ No se encontró el mensaje. Usá el formato: P0001 (tu mensaje)"
    
    respuesta_texto = partes[1].strip()
    if not respuesta_texto:
        return "⚠️ No escribiste ningún mensaje. Usá el formato: P0001 (tu mensaje)"
    
    pedido = presupuesto.obtener_presupuesto(codigo)
    if not pedido:
        notificaciones.notificar_error_respuesta(codigo)
        return f"⚠️ No se encontró el presupuesto {codigo}."
    
    sender_clean = sender.replace('whatsapp:', '') if sender.startswith('whatsapp:') else sender
    cliente_clean = pedido['telefono'].replace('whatsapp:', '') if pedido['telefono'].startswith('whatsapp:') else pedido['telefono']
    
    if sender_clean == cliente_clean:
        return "✅ Mensaje registrado. (No te enviamos el mensaje a ti mismo como cliente)"
    
    precio_match = re.search(r'[\$]?(\d{1,3}(?:\.\d{3})*|\d+)', respuesta_texto)
    if precio_match:
        precio_str = precio_match.group(1).replace('.', '')
        try:
            precio = int(precio_str)
            presupuesto.actualizar_precio(codigo, str(precio))
            logger.info(f"✅ Precio actualizado: ${precio}")
        except:
            pass
    
    presupuesto.actualizar_estado(codigo, presupuesto.ESTADOS["ENVIADO"])
    notificaciones.notificar_respuesta_dueño(codigo, respuesta_texto)
    notificaciones.notificar_presupuesto_cliente(codigo, pedido, respuesta_texto, es_modificacion=False)
    
    return "✅ Tu respuesta fue enviada al cliente."

def procesar_respuesta_presupuesto_simple(mensaje, sender, codigo):
    """Procesa respuesta simple del dueño (P0001 mensaje)."""
    logger.info(f"   📞 Procesando respuesta simple de presupuesto: {codigo}")
    
    partes = re.split(r'P[-]?\d{4}\s*[:]?\s*', mensaje, maxsplit=1)
    if len(partes) < 2:
        return "⚠️ No se encontró el mensaje. Usá el formato: P0001 (tu mensaje)"
    
    respuesta_texto = partes[1].strip()
    if not respuesta_texto:
        return "⚠️ No escribiste ningún mensaje. Usá el formato: P0001 (tu mensaje)"
    
    pedido = presupuesto.obtener_presupuesto(codigo)
    if not pedido:
        notificaciones.notificar_error_respuesta(codigo)
        return f"⚠️ No se encontró el presupuesto {codigo}."
    
    sender_clean = sender.replace('whatsapp:', '') if sender.startswith('whatsapp:') else sender
    cliente_clean = pedido['telefono'].replace('whatsapp:', '') if pedido['telefono'].startswith('whatsapp:') else pedido['telefono']
    
    if sender_clean == cliente_clean:
        return "✅ Mensaje registrado. (No te enviamos el mensaje a ti mismo como cliente)"
    
    precio_match = re.search(r'[\$]?(\d{1,3}(?:\.\d{3})*|\d+)', respuesta_texto)
    if precio_match:
        precio_str = precio_match.group(1).replace('.', '')
        try:
            precio = int(precio_str)
            presupuesto.actualizar_precio(codigo, str(precio))
            logger.info(f"✅ Precio actualizado: ${precio}")
        except:
            pass
    
    presupuesto.actualizar_estado(codigo, presupuesto.ESTADOS["ENVIADO"])
    notificaciones.notificar_respuesta_dueño(codigo, respuesta_texto)
    notificaciones.notificar_presupuesto_cliente(codigo, pedido, respuesta_texto, es_modificacion=False)
    
    return "✅ Tu respuesta fue enviada al cliente."

def procesar_respuesta_asesor_simple(mensaje, sender, codigo):
    """Procesa respuesta simple del asesor (C0005 mensaje)."""
    logger.info(f"   📞 Procesando respuesta simple de consulta: {codigo}")
    
    partes = re.split(r'C[-]?\d{4}\s*[:]?\s*', mensaje, maxsplit=1)
    if len(partes) < 2:
        return "⚠️ No se encontró el mensaje. Usá el formato: C0005 (tu mensaje)"
    
    respuesta_texto = partes[1].strip()
    if not respuesta_texto:
        return "⚠️ No escribiste ningún mensaje. Usá el formato: C0005 (tu mensaje)"
    
    cliente_telefono = asesores.obtener_telefono_cliente(codigo)
    if not cliente_telefono:
        notificaciones.notificar_error_respuesta(codigo)
        return "⚠️ No se encontró la consulta."
    
    sender_clean = sender.replace('whatsapp:', '') if sender.startswith('whatsapp:') else sender
    cliente_clean = cliente_telefono.replace('whatsapp:', '') if cliente_telefono.startswith('whatsapp:') else cliente_telefono
    
    if sender_clean == cliente_clean:
        return "✅ Mensaje registrado. (No te enviamos el mensaje a ti mismo como cliente)"
    
    from twilio.rest import Client
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    from_number = os.environ.get('TWILIO_WHATSAPP_NUMBER')
    
    if not account_sid or not auth_token or not from_number:
        return "⚠️ Error al enviar la respuesta."
    
    client = Client(account_sid, auth_token)
    
    # CORREGIDO: Evitar doble prefijo whatsapp:
    if cliente_telefono.startswith('whatsapp:'):
        to = cliente_telefono
    else:
        to = f'whatsapp:{cliente_telefono}'
    
    client.messages.create(
        from_=f'whatsapp:{from_number}',
        body=f"📞 *Un asesor te responde:*\n{respuesta_texto}",
        to=to
    )
    logger.info(f"✅ Respuesta enviada al cliente {cliente_telefono}")
    
    # ✅ NUEVO: Enviar confirmación al asesor
    try:
        client.messages.create(
            from_=f'whatsapp:{from_number}',
            body=f"✅ *Tu respuesta fue enviada al cliente*\n\n📋 Consulta: {codigo}\n📩 El cliente ya recibió tu mensaje.",
            to=sender
        )
        logger.info(f"✅ Confirmación enviada al asesor {sender}")
    except Exception as e:
        logger.error(f"❌ Error al enviar confirmación al asesor: {e}")
    
    # Actualizar estado en CONSULTAS
    try:
        service = build('sheets', 'v4', credentials=config.CREDENTIALS)
        result = service.spreadsheets().values().get(
            spreadsheetId=config.SPREADSHEETS["CONSULTAS"],
            range='A:F'
        ).execute()
        datos = result.get('values', [])
        
        for i, fila in enumerate(datos):
            if len(fila) > 0 and fila[0] == codigo:
                fila_excel = i + 1
                rango_celda = f'E{fila_excel}'
                body = {'values': [["Respondida"]]}
                service.spreadsheets().values().update(
                    spreadsheetId=config.SPREADSHEETS["CONSULTAS"],
                    range=rango_celda,
                    valueInputOption='USER_ENTERED',
                    body=body
                ).execute()
                logger.info(f"✅ Consulta {codigo} marcada como Respondida")
                break
    except Exception as e:
        logger.error(f"❌ Error al actualizar estado: {e}")
    
    return "✅ Tu respuesta fue enviada al cliente."

# ============================================================
# FLUJO DE PRESUPUESTO (TODAS LAS FUNCIONES)
# ============================================================

def iniciar_presupuesto(sender):
    logger.info(f"📝 Iniciando presupuesto para {sender}")
    sesiones[sender] = "esperando_producto_presupuesto"
    
    return """
🪑 *Presupuesto - Paso 1/3*

📦 ¿Qué producto estás necesitando?

*Ejemplos:*
• Mesa de roble de 1.20m
• Silla rústica con respaldo alto
• Bajo mesada a medida
• Estante flotante de 80cm
• Mueble a medida

💡 *Tip:* En cualquier momento podés escribir CANCELAR para salir del presupuesto.

👉 Escribí el nombre y detalles del producto:
"""

def procesar_producto_presupuesto(sender, mensaje):
    logger.info(f"📝 Producto recibido: {mensaje}")
    sesiones[sender] = "esperando_personalizacion_presupuesto"
    
    if not hasattr(procesar_producto_presupuesto, 'datos_temporales'):
        procesar_producto_presupuesto.datos_temporales = {}
    procesar_producto_presupuesto.datos_temporales[sender] = {"producto": mensaje}
    
    return """
🎨 *Presupuesto - Paso 2/3*

✨ ¿Qué personalización necesitas para este producto?

*Ejemplos:*
• Medidas: 180cm x 90cm x 75cm
• Color: Nogal oscuro
• Terminación: Mate
• Tipo de madera: Roble macizo

👉 Escribí los detalles de personalización:
"""

def procesar_personalizacion_presupuesto(sender, mensaje):
    logger.info(f"📝 Personalización recibida: {mensaje}")
    sesiones[sender] = "esperando_dni_presupuesto"
    
    if hasattr(procesar_producto_presupuesto, 'datos_temporales') and sender in procesar_producto_presupuesto.datos_temporales:
        procesar_producto_presupuesto.datos_temporales[sender]["personalizacion"] = mensaje
    
    return """
📋 *Presupuesto - Paso 3/3*

🆔 Para crear tu presupuesto, necesito tu DNI o CUIT.

⚠️ *Importante:* Escribilo sin puntos ni guiones.
*Ejemplo:* 20123456789

👉 Escribí tu número de documento:
"""

def procesar_dni_presupuesto(sender, mensaje):
    logger.info(f"📝 DNI recibido: {mensaje}")
    
    if not mensaje.isdigit() or len(mensaje) < 7:
        return """
❌ *DNI inválido*

El DNI debe tener al menos 7 dígitos y solo números.

👉 Escribí tu DNI nuevamente o CANCELAR para salir:
"""
    
    cliente = buscar_por_dni(mensaje)
    
    if cliente:
        return crear_presupuesto_final(sender, cliente)
    else:
        sesiones[sender] = "esperando_nombre_presupuesto"
        
        if hasattr(procesar_producto_presupuesto, 'datos_temporales') and sender in procesar_producto_presupuesto.datos_temporales:
            procesar_producto_presupuesto.datos_temporales[sender]["dni"] = mensaje
        
        return """
👤 *Cliente nuevo*

No encontré tu DNI en el sistema. Necesito algunos datos más:

📝 ¿Cuál es tu nombre completo?

👉 Escribí tu nombre y apellido:
"""

def procesar_nombre_presupuesto(sender, mensaje):
    logger.info(f"📝 Nombre recibido: {mensaje}")
    sesiones[sender] = "esperando_telefono_presupuesto"
    
    if hasattr(procesar_producto_presupuesto, 'datos_temporales') and sender in procesar_producto_presupuesto.datos_temporales:
        procesar_producto_presupuesto.datos_temporales[sender]["nombre"] = mensaje
    
    return """
📞 *Un paso más*

📱 ¿Cuál es tu número de teléfono?

*Ejemplo:* 3434123456

👉 Escribí tu teléfono:
"""

def procesar_telefono_presupuesto(sender, mensaje):
    logger.info(f"📝 Teléfono recibido: {mensaje}")
    
    if not mensaje.isdigit() or len(mensaje) < 7:
        return """
❌ *Teléfono inválido*

El teléfono debe tener al menos 7 dígitos y solo números.

👉 Escribí tu teléfono nuevamente:
"""
    
    if hasattr(procesar_producto_presupuesto, 'datos_temporales') and sender in procesar_producto_presupuesto.datos_temporales:
        procesar_producto_presupuesto.datos_temporales[sender]["telefono"] = mensaje
        datos = procesar_producto_presupuesto.datos_temporales[sender]
        
        cliente = {
            "dni": datos.get("dni", ""),
            "nombre": datos.get("nombre", ""),
            "telefono": datos.get("telefono", "")
        }
        
        return crear_presupuesto_final(sender, cliente)
    
    return "❌ Error: No se encontraron los datos del presupuesto."

def crear_presupuesto_final(sender, cliente):
    if hasattr(procesar_producto_presupuesto, 'datos_temporales') and sender in procesar_producto_presupuesto.datos_temporales:
        datos = procesar_producto_presupuesto.datos_temporales[sender]
        
        producto = datos.get("producto", "")
        personalizacion = datos.get("personalizacion", "")
        dni = cliente.get("dni") if isinstance(cliente, dict) else cliente.get("dni", "")
        
        del procesar_producto_presupuesto.datos_temporales[sender]
        
        if isinstance(cliente, dict) and "nombre" in cliente and "telefono" in cliente:
            resultado = presupuesto.crear_presupuesto(
                sender=sender,
                producto=producto,
                personalizacion=personalizacion,
                dni=dni,
                nombre=cliente["nombre"],
                telefono=cliente["telefono"]
            )
        else:
            resultado = presupuesto.crear_presupuesto(
                sender=sender,
                producto=producto,
                personalizacion=personalizacion,
                dni=cliente["dni"]
            )
        
        if resultado and resultado.get("estado"):
            numero_presupuesto = resultado["numero"]
            cliente_data = resultado["cliente"]
            
            notificaciones.notificar_nuevo_presupuesto(
                numero_presupuesto=numero_presupuesto,
                datos_cliente=cliente_data,
                producto=producto,
                personalizacion=personalizacion
            )
            
            sesiones[sender] = None
            
            return f"""
✅ *Presupuesto creado con éxito*

📋 *Número de presupuesto:* {numero_presupuesto}

👤 Cliente: {cliente_data['nombre']}
📞 Teléfono: {cliente_data['telefono']}
📦 Producto: {producto}
🎨 Personalización: {personalizacion}

📌 *¿Qué sigue?*
Un asesor revisará tu solicitud y te responderá por este mismo chat dentro de las próximas 24 horas hábiles.

👉 Escribí MENU para volver al inicio.
💡 Podés salir tranquilo, igual te llegará la respuesta del asesor.

¡Gracias por confiar en Carpintería Radi! 🪑
"""
        else:
            sesiones[sender] = None
            return """
❌ *Error al crear el presupuesto*

Hubo un problema al guardar tu solicitud. Por favor, intentá de nuevo más tarde.

😊 Disculpá las molestias.
"""
    
    return "❌ Error: No se encontraron los datos del presupuesto."

# ============================================================
# PROCESAMIENTO DE ACCIONES DEL CLIENTE
# ============================================================

def procesar_accion_presupuesto(sender, mensaje):
    logger.info(f"📝 Procesando acción de presupuesto: {mensaje}")
    
    if not hasattr(procesar_accion_presupuesto, 'datos_presupuesto'):
        return "❌ Error: No se encontró el presupuesto."
    
    if sender not in procesar_accion_presupuesto.datos_presupuesto:
        return "❌ Error: No se encontró el presupuesto."
    
    datos = procesar_accion_presupuesto.datos_presupuesto[sender]
    numero_presupuesto = datos["numero"]
    pedido = presupuesto.obtener_presupuesto(numero_presupuesto)
    
    if not pedido:
        return "❌ Error: No se encontró el presupuesto."
    
    if mensaje == "1":
        presupuesto.actualizar_estado(numero_presupuesto, presupuesto.ESTADOS["ACEPTADO"])
        notificaciones.notificar_aceptacion_cliente(numero_presupuesto, {"nombre": pedido["nombre"], "telefono": pedido["telefono"]}, pedido)
        
        sesiones[sender] = "esperando_forma_pago"
        if not hasattr(procesar_forma_pago, 'datos_presupuesto'):
            procesar_forma_pago.datos_presupuesto = {}
        procesar_forma_pago.datos_presupuesto[sender] = {"numero": numero_presupuesto}
        
        return """
✅ *Presupuesto aceptado*

¡Excelente decisión! Tu presupuesto fue aceptado.

💰 Ahora elegí cómo querés pagar:

1️⃣ Transferencia bancaria
2️⃣ Pago en efectivo (10% de descuento)
3️⃣ Cuotas de la casa (sin interés)

👉 Escribí el número de la opción que desees.
"""
    
    elif mensaje == "2":
        presupuesto.actualizar_estado(numero_presupuesto, presupuesto.ESTADOS["RECHAZADO"])
        notificaciones.notificar_rechazo_cliente(numero_presupuesto, {"nombre": pedido["nombre"], "telefono": pedido["telefono"]}, pedido)
        
        sesiones[sender] = None
        if sender in procesar_accion_presupuesto.datos_presupuesto:
            del procesar_accion_presupuesto.datos_presupuesto[sender]
        
        return """
❌ *Presupuesto rechazado*

Entendemos que el presupuesto no se ajusta a lo que buscabas.

📌 ¿Qué querés hacer?
1️⃣ Pedir un presupuesto nuevo
2️⃣ Hablar con un asesor
3️⃣ Volver al menú principal

👉 Escribí el número de la opción que desees.
"""
    
    elif mensaje == "3":
        sesiones[sender] = "esperando_modificacion_presupuesto"
        
        return """
✏️ *Solicitar modificaciones*

Contanos qué cambios te gustaría hacer en el presupuesto:

*Ejemplos:*
• El precio es muy alto
• Quiero un material diferente
• Necesito cambiar las medidas

👉 Escribí los cambios que deseas:
"""
    
    elif mensaje == "4":
        sesiones[sender] = None
        if sender in procesar_accion_presupuesto.datos_presupuesto:
            del procesar_accion_presupuesto.datos_presupuesto[sender]
        return iniciar_asesor(sender)
    
    else:
        return """
❌ *Opción no válida*

Elegí una de las siguientes opciones:
1️⃣ Aceptar
2️⃣ Rechazar
3️⃣ Modificar
4️⃣ Asesor

👉 Escribí el número de la opción que desees.
"""

def procesar_modificacion_presupuesto(sender, mensaje):
    logger.info(f"📝 Modificación recibida: {mensaje}")
    
    if not hasattr(procesar_accion_presupuesto, 'datos_presupuesto'):
        return "❌ Error: No se encontró el presupuesto."
    
    if sender not in procesar_accion_presupuesto.datos_presupuesto:
        return "❌ Error: No se encontró el presupuesto."
    
    datos = procesar_accion_presupuesto.datos_presupuesto[sender]
    numero_presupuesto = datos["numero"]
    pedido = presupuesto.obtener_presupuesto(numero_presupuesto)
    
    if not pedido:
        return "❌ Error: No se encontró el presupuesto."
    
    presupuesto.guardar_modificacion(numero_presupuesto, mensaje)
    presupuesto.actualizar_estado(numero_presupuesto, presupuesto.ESTADOS["MODIFICADO"])
    
    notificaciones.notificar_modificacion_cliente(
        numero_presupuesto,
        {"nombre": pedido["nombre"], "telefono": pedido["telefono"]},
        pedido,
        mensaje
    )
    
    sesiones[sender] = None
    if sender in procesar_accion_presupuesto.datos_presupuesto:
        del procesar_accion_presupuesto.datos_presupuesto[sender]
    
    return """
✅ *Modificaciones enviadas*

Tu solicitud de cambios para el presupuesto fue enviada.

📌 *¿Qué sigue?*
Un asesor revisará tus solicitudes y te responderá por este mismo chat.

👉 Escribí MENU para volver al inicio.
💡 Podés salir tranquilo, igual te llegará la respuesta.
"""

def procesar_forma_pago(sender, mensaje):
    logger.info(f"📝 Forma de pago recibida: {mensaje}")
    
    if not hasattr(procesar_forma_pago, 'datos_presupuesto'):
        return "❌ Error: No se encontró el presupuesto."
    
    if sender not in procesar_forma_pago.datos_presupuesto:
        return "❌ Error: No se encontró el presupuesto."
    
    numero_presupuesto = procesar_forma_pago.datos_presupuesto[sender]["numero"]
    pedido = presupuesto.obtener_presupuesto(numero_presupuesto)
    
    if not pedido:
        return "❌ Error: No se encontró el presupuesto."
    
    if mensaje == "1":
        forma_pago = "Transferencia bancaria"
        presupuesto.actualizar_forma_pago(numero_presupuesto, forma_pago)
        notificaciones.notificar_forma_pago(numero_presupuesto, {"nombre": pedido["nombre"], "telefono": pedido["telefono"]}, pedido, forma_pago)
        
        sesiones[sender] = None
        del procesar_forma_pago.datos_presupuesto[sender]
        
        return f"""
💰 *Transferencia bancaria*

Datos para transferir:  
🏦 *Banco Nación*  
📌 *CBU:* 1234567890123456789012  
📌 *Alias:* CARPINTERIA.RADI  
📌 *Monto:* ${pedido['precio']}

Una vez que hagas la transferencia, enviá el comprobante por este chat.

👉 Escribí MENU para volver al inicio.

¡Gracias por confiar en Carpintería Radi! 🪑
"""
    
    elif mensaje == "2":
        precio_original = int(pedido['precio']) if pedido['precio'] else 0
        descuento = int(precio_original * 10 / 100)
        precio_final = precio_original - descuento
        
        forma_pago = f"Efectivo (10% descuento - ${precio_final})"
        presupuesto.actualizar_forma_pago(numero_presupuesto, forma_pago)
        notificaciones.notificar_forma_pago(numero_presupuesto, {"nombre": pedido["nombre"], "telefono": pedido["telefono"]}, pedido, forma_pago)
        
        sesiones[sender] = None
        del procesar_forma_pago.datos_presupuesto[sender]
        
        return f"""
💰 *Pago en efectivo*

Precio original: ${precio_original}
🎉 Descuento por pago en efectivo: 10%
💰 Total a pagar: ${precio_final}

📍 Podés pasar por nuestro taller:
Av. San Martín 123, Paraná
⏰ Lunes a viernes de 9 a 18 hs.

📌 *¿Qué sigue?*
Un asesor se pondrá en contacto para coordinar el retiro o entrega.

👉 Escribí MENU para volver al inicio.

¡Gracias por confiar en Carpintería Radi! 🪑
"""
    
    elif mensaje == "3":
        sesiones[sender] = "esperando_cuotas_presupuesto"
        
        return f"""
💰 *Pago en cuotas de la casa*

Precio total: ${pedido['precio']}

¿En cuántas cuotas querés pagar?  
3️⃣ *3 cuotas*  
6️⃣ *6 cuotas*  
12️⃣ *12 cuotas*

👉 Escribí el número de cuotas que deseas:
"""
    
    else:
        return """
❌ *Opción no válida*

Elegí una de las siguientes opciones:
1️⃣ Transferencia bancaria
2️⃣ Pago en efectivo (10% descuento)
3️⃣ Cuotas de la casa

👉 Escribí el número de la opción que desees.
"""

# ============================================================
# FUNCIONES DE MENÚ Y UTILIDADES
# ============================================================

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

def cancelar_flujo():
    return """
❌ *Presupuesto cancelado*

Has salido del área de presupuestos.

👋 *Menú principal*

1️⃣ Presupuesto
2️⃣ Consultar estado
3️⃣ Hablar con asesor
4️⃣ Reclamos o sugerencias
0️⃣ Repetir menú

👉 Escribí el número de la opción que desees.
"""

def consultar_estado(sender):
    logger.info(f"   🔍 Consultando estado para {sender}")
    sesiones[sender] = "esperando_dni_estado"
    return """
🔍 *Consultar estado de pedido*

Para consultar el estado de tu pedido, necesito tu **DNI** o **CUIT**.

➡️ *Ejemplo:* 20123456789
"""

def procesar_dni_estado(sender, mensaje):
    logger.info(f"🔍 DNI recibido para estado: {mensaje}")
    
    if not mensaje.isdigit() or len(mensaje) < 7:
        return """
❌ *DNI inválido*

El DNI debe tener al menos 7 dígitos y solo números.

👉 Escribí tu DNI nuevamente:
"""
    
    pedidos = presupuesto.obtener_presupuestos_por_dni(mensaje)
    
    if not pedidos:
        sesiones[sender] = None
        return """
🔍 *No se encontraron pedidos*

No encontramos pedidos asociados a este DNI.

👉 Escribí MENU para volver al inicio.
"""
    
    mensaje_estado = "🔍 *Estado de tus pedidos:*\n\n"
    for pedido in pedidos:
        mensaje_estado += f"""
📋 *Pedido {pedido['numero']}*
📦 Producto: {pedido['producto']}
📌 Estado: *{pedido['estado']}*
📅 Fecha: {pedido['fecha']}
---
"""
    
    sesiones[sender] = None
    return mensaje_estado

def iniciar_asesor(sender):
    logger.info(f"   📞 Iniciando flujo de asesor para {sender}")
    sesiones[sender] = "esperando_consulta_asesor"
    return """
📞 *Hablar con un asesor*

Decime tu consulta y un asesor te va a responder por este mismo chat.

👉 Escribí tu mensaje:
"""

def procesar_consulta_asesor(sender, mensaje):
    logger.info(f"   📞 Procesando consulta de asesor de {sender}")
    respuesta = asesores.procesar_consulta(sender, mensaje)
    
    if "✅ *Consulta enviada*" in respuesta:
        sesiones[sender] = None
        logger.info(f"   📞 Consulta exitosa. Estado limpiado.")
    else:
        logger.info(f"   📞 La consulta falló. Manteniendo estado 'esperando_consulta_asesor' para {sender}")
    
    return respuesta

# ============================================================
# INICIO DE LA APLICACIÓN
# ============================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info("🚀 Bot de gestión iniciado...")
    logger.info(f"📡 Escuchando en el puerto {port}")
    logger.info("✅ Logs detallados activados")
    app.run(host='0.0.0.0', port=port, debug=False)
