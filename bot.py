# bot.py
# Orquestador principal - 100% Genérico (Con validación de teléfono y memoria optimizada)

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
        gc.collect() # Libera memoria RAM en cada mensaje

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
    
    # 2. VERIFICAR ESTADO DE SESIÓN
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

    # 3. COMANDOS GLOBALES
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
    
    # 4. OPCIONES DEL MENÚ
    if mensaje_lower in ["1", "presupuesto"]: return iniciar_presupuesto(sender)
    if mensaje_lower in ["2", "estado"]: return iniciar_estado(sender)
    if mensaje_lower in ["3", "asesor"]:
        sesiones[sender] = "esperando_consulta_asesor"
        return f"📞 *Hablar con un asesor de {nombre}*\n\nDecime tu consulta y te responderemos por aquí.\n\n👉 Escribí tu mensaje:"
    if mensaje_lower in ["4", "reclamo"]:
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
    
    conf = obtener_configuracion()
    nombre = conf.get('nombre_negocio', 'Nuestro Negocio')
    notificaciones.enviar_whatsapp(cliente_telefono, f"📞 *Un asesor de {nombre} te responde:*\n{respuesta_texto}")
    
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
# FLUJO DE PRESUPUESTO
# ============================================================

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
    return "📋 *Presupuesto - Paso 3/3*\n\n🆔 Escribí tu DNI o CUIT (sin puntos ni guiones):"

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
    # --- CORRECCIÓN: Usamos el número real de WhatsApp (sender) ---
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
        import traceback
        traceback.print_exc()
        sesiones[sender] = None
        return f"❌ Error interno, enviame esto: {str(e)}"

# ============================================================
# ACCIONES DEL CLIENTE
# ============================================================

def p_accion(sender, mensaje):
    datos = datos_accion_presupuesto.get(sender, {})
    numero = datos.get("numero")
    pedido = presupuesto.obtener_presupuesto(numero)
    if not pedido: return "❌ Presupuesto no encontrado."

    if mensaje == "1":
        presupuesto.actualizar_estado(numero, presupuesto.ESTADOS["ACEPTADO"])
        notificaciones.notificar_aceptacion_cliente(numero, {"nombre": pedido["nombre"], "telefono": pedido["telefono"]}, pedido)
        sesiones[sender] = "esperando_forma_pago"
        return pagos.mostrar_opciones_pago()
    elif mensaje == "2":
        presupuesto.actualizar_estado(numero, presupuesto.ESTADOS["RECHAZADO"])
        notificaciones.notificar_rechazo_cliente(numero, {"nombre": pedido["nombre"], "telefono": pedido["telefono"]}, pedido)
        sesiones[sender] = None
        datos_accion_presupuesto.pop(sender, None)
        return "❌ *Rechazado*\n\n📌 1. Presupuesto nuevo | 2. Asesor | 3. Menú\n👉 Escribí el número:"
    elif mensaje == "3":
        sesiones[sender] = "esperando_modificacion"
        return "✏️ *Modificaciones*\n\n👉 Escribí los cambios que deseas:"
    elif mensaje == "4":
        sesiones[sender] = "esperando_consulta_asesor"
        datos_accion_presupuesto.pop(sender, None)
        return "📞 *Hablar con asesor*\n\n👉 Escribí tu consulta:"
    return "❌ Opción no válida."

def p_modificacion(sender, mensaje):
    datos = datos_accion_presupuesto.get(sender, {})
    numero = datos.get("numero")
    pedido = presupuesto.obtener_presupuesto(numero)
    presupuesto.guardar_modificacion(numero, mensaje)
    presupuesto.actualizar_estado(numero, presupuesto.ESTADOS["MODIFICADO"])
    notificaciones.notificar_modificacion_cliente(numero, {"nombre": pedido["nombre"], "telefono": pedido["telefono"]}, pedido, mensaje)
    sesiones[sender] = None
    datos_accion_presupuesto.pop(sender, None)
    return "✅ *Modificaciones enviadas*\n\n👉 Escribí MENU para volver."

def p_forma_pago(sender, mensaje):
    datos = datos_accion_presupuesto.get(sender, {})
    numero = datos.get("numero")
    pedido = presupuesto.obtener_presupuesto(numero)
    conf = obtener_configuracion()
    
    if mensaje == "1":
        forma = "Transferencia"
        msg = pagos.transferencia(pedido, conf)
    elif mensaje == "2":
        forma = "Efectivo"
        msg = pagos.efectivo(pedido, conf)
    elif mensaje == "3":
        forma = "Cuotas"
        sesiones[sender] = "esperando_cuotas"
        return pagos.cuotas(pedido, conf) 
    else:
        return "❌ Opción no válida. Elegí 1, 2 o 3."
    
    presupuesto.actualizar_forma_pago(numero, forma)
    notificaciones.notificar_forma_pago(numero, {"nombre": pedido["nombre"], "telefono": pedido["telefono"]}, pedido, forma)
    sesiones[sender] = None
    datos_accion_presupuesto.pop(sender, None)
    return msg

def p_cuotas(sender, mensaje):
    datos = datos_accion_presupuesto.get(sender, {})
    numero = datos.get("numero")
    pedido = presupuesto.obtener_presupuesto(numero)
    conf = obtener_configuracion()
    
    if mensaje not in ["3", "6", "12"]:
        return "❌ Opción no válida. Elegí 3, 6 o 12 cuotas:"
    
    presupuesto.actualizar_cuotas(numero, mensaje)
    presupuesto.actualizar_forma_pago(numero, f"Cuotas ({mensaje})")
    notificaciones.notificar_forma_pago(numero, {"nombre": pedido["nombre"], "telefono": pedido["telefono"]}, pedido, f"Cuotas ({mensaje})")
    
    msg = pagos.procesar_cuotas(mensaje, pedido, conf)
    sesiones[sender] = None
    datos_accion_presupuesto.pop(sender, None)
    return msg

# ============================================================
# CONSULTAR ESTADO
# ============================================================

def iniciar_estado(sender):
    sesiones[sender] = "esperando_dni_estado"
    return "🔍 *Consultar estado*\n\n👉 Escribí tu DNI o CUIT:"

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

# ============================================================
# UTILIDADES
# ============================================================

def mostrar_menu():
    conf = obtener_configuracion()
    nombre = conf.get('nombre_negocio', 'Nuestro Negocio')
    return f"""
👋 *Bienvenido a {nombre}*

1️⃣ Presupuesto
2️⃣ Consultar estado
3️⃣ Hablar con asesor
4️⃣ Reclamos
0️⃣ Repetir menú

💬 Escribí 'Ayuda' para más detalles.
"""

def no_entendido():
    return "🤔 *No entendí.*\n\n✅ Escribí 'Hola' o 'MENU' para ver las opciones."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
