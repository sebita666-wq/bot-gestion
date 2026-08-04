# areas/gestion_ventas/asesores.py
# SISTEMA DE CHAT EN VIVO CON ASESORES - COMPLETO CON TIMEOUTS

from utils import config
from datetime import datetime, timedelta
import logging
import os
from googleapiclient.discovery import build
from twilio.rest import Client

# Configurar logger
logger = logging.getLogger(__name__)

TIMEOUT_MINUTOS = 5

# Configuración de timeouts (en minutos)
TIMEOUT_RECORDATORIO = 3      # Recordatorio al asesor
TIMEOUT_REASIGNAR = 5          # Reasignar a otro asesor
TIMEOUT_FINAL = 8              # Mensaje final al cliente

# ============================================================
# 1. FUNCIONES DE ASESORES (desde Google Sheets)
# ============================================================

def cargar_asesores():
    """Carga la lista de asesores desde la planilla ASESORES."""
    logger.info("📋 [cargar_asesores] Leyendo ASESORES desde Google Sheets...")
    try:
        service = build('sheets', 'v4', credentials=config.CREDENTIALS)
        
        result = service.spreadsheets().values().get(
            spreadsheetId=config.SPREADSHEETS["ASESORES"],
            range='A:C'
        ).execute()
        datos = result.get('values', [])
        
        if not datos or len(datos) < 2:
            logger.warning("⚠️ [cargar_asesores] No hay datos, usando asesor por defecto")
            return [{"orden": 1, "telefono": "5493434727811", "nombre": "Sebastian"}]
        
        asesores = []
        for fila in datos[1:]:
            if len(fila) >= 2 and fila[1].strip():
                asesores.append({
                    "orden": int(fila[0]) if fila[0].isdigit() else 0,
                    "telefono": fila[1].strip(),
                    "nombre": fila[2].strip() if len(fila) > 2 else "Asesor"
                })
        asesores.sort(key=lambda x: x["orden"])
        logger.info(f"✅ [cargar_asesores] {len(asesores)} asesores cargados.")
        return asesores
    except Exception as e:
        logger.error(f"❌ [cargar_asesores] Error: {e}")
        return [{"orden": 1, "telefono": "5493434727811", "nombre": "Sebastian"}]

def obtener_asesor_activo():
    """Obtiene el primer asesor de la lista."""
    asesores = cargar_asesores()
    return asesores[0] if asesores else None

# ============================================================
# 2. GENERACIÓN DE CÓDIGO DE CONSULTA
# ============================================================

def generar_codigo_consulta():
    """Genera el próximo código de consulta (C-XXXX)"""
    logger.info("🔢 [generar_codigo_consulta] Generando código...")
    try:
        service = build('sheets', 'v4', credentials=config.CREDENTIALS)
        
        result = service.spreadsheets().values().get(
            spreadsheetId=config.SPREADSHEETS["CONSULTAS"],
            range='A:A'
        ).execute()
        datos = result.get('values', [])
        
        if not datos or len(datos) < 2:
            logger.info("📝 [generar_codigo_consulta] Planilla vacía, código inicial C-0001")
            return "C-0001"
        
        ultimo_codigo = "C-0000"
        for fila in datos[1:]:
            if len(fila) > 0 and fila[0].startswith("C-"):
                if fila[0] > ultimo_codigo:
                    ultimo_codigo = fila[0]
        
        num = int(ultimo_codigo.split("-")[1]) + 1
        nuevo_codigo = f"C-{num:04d}"
        logger.info(f"✅ [generar_codigo_consulta] Nuevo código: {nuevo_codigo}")
        return nuevo_codigo
    except Exception as e:
        logger.error(f"❌ [generar_codigo_consulta] Error: {e}")
        return "C-0001"

# ============================================================
# 3. CREACIÓN DE CONSULTA (API DIRECTA)
# ============================================================

def crear_consulta(sender, telefono_cliente, mensaje):
    """Crea una nueva consulta de cliente."""
    logger.info("🚨 [crear_consulta] Creando consulta...")
    
    codigo = generar_codigo_consulta()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nueva_consulta = [
        [codigo, fecha, telefono_cliente, mensaje, "Pendiente", ""]
    ]
    logger.info(f"   📝 [crear_consulta] Datos a guardar: {nueva_consulta}")
    
    sheet_id = config.SPREADSHEETS["CONSULTAS"]
    logger.info(f"   📤 [crear_consulta] Escribiendo en CONSULTAS (ID: {sheet_id})...")
    
    try:
        service = build('sheets', 'v4', credentials=config.CREDENTIALS)
        
        body = {'values': nueva_consulta}
        result = service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range='A:F',
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        logger.info(f"   📥 [crear_consulta] Resultado: {result}")
        logger.info("   ✅ [crear_consulta] Consulta guardada exitosamente")
        return {"codigo": codigo, "estado": "Pendiente"}
        
    except Exception as e:
        logger.error(f"   ❌ [crear_consulta] EXCEPCIÓN: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================================
# 4. NOTIFICACIÓN AL ASESOR (CON ENVÍO REAL POR TWILIO)
# ============================================================

def notificar_asesor(codigo, telefono_cliente, mensaje):
    """Notifica al asesor enviando un mensaje real por WhatsApp usando Twilio."""
    asesor = obtener_asesor_activo()
    if not asesor:
        logger.error("❌ No hay asesores disponibles.")
        return False
    
    telefono_asesor = asesor["telefono"]
    if not telefono_asesor.startswith("+"):
        telefono_asesor = "+" + telefono_asesor
    
    texto = f"""
📞 *Nueva consulta de cliente*

Código: {codigo}
Cliente: {telefono_cliente}
Consulta: "{mensaje}"

👉 Respondé copiando esta línea y agregando tu mensaje:
Respuesta {codigo}:
"""
    logger.info(f"📱 Enviando a {asesor['nombre']} ({telefono_asesor}):")
    logger.info(texto)
    
    try:
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        from_number = os.environ.get('TWILIO_WHATSAPP_NUMBER')
        
        if not account_sid or not auth_token or not from_number:
            logger.error("❌ Faltan variables de entorno de Twilio")
            return False
        
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            from_=f'whatsapp:{from_number}',
            body=texto,
            to=f'whatsapp:{telefono_asesor}'
        )
        logger.info(f"✅ Mensaje enviado a {telefono_asesor}. SID: {message.sid}")
        return True
    except Exception as e:
        logger.error(f"❌ Error al enviar mensaje: {e}")
        return False

# ============================================================
# 5. PROCESADOR PRINCIPAL DE CONSULTA
# ============================================================

def procesar_consulta(sender, mensaje):
    """Procesa la consulta de un cliente."""
    logger.info("🚨 [procesar_consulta] Procesando consulta...")
    logger.info(f"   📞 [procesar_consulta] Iniciando para {sender}")
    logger.info(f"   📞 [procesar_consulta] Mensaje: {mensaje[:50]}...")
    
    consulta = crear_consulta(sender, sender, mensaje)
    logger.info(f"   📞 [procesar_consulta] consulta creada: {consulta}")
    
    if consulta:
        notificar_asesor(consulta["codigo"], sender, mensaje)
        return f"""
✅ *Consulta enviada*

Tu consulta fue registrada con el código *{consulta['codigo']}*.

Un asesor te va a responder por este mismo chat en breve.

😊 Gracias por tu paciencia.
"""
    else:
        logger.error("   ❌ [procesar_consulta] consulta es None, error al guardar")
        return """
❌ *Error al enviar tu consulta*

Hubo un problema al registrar tu consulta. Por favor, intentá de nuevo más tarde.

😊 Disculpá las molestias.
"""

# ============================================================
# 6. PROCESAMIENTO DE RESPUESTA DEL ASESOR
# ============================================================

def procesar_respuesta_asesor(respuesta):
    """Procesa la respuesta del asesor."""
    lineas = respuesta.split('\n')
    for linea in lineas:
        if linea.strip().startswith("Respuesta C-"):
            partes = linea.split(":", 1)
            if len(partes) == 2:
                codigo = partes[0].strip().split(" ")[1]
                mensaje = partes[1].strip()
                return {"codigo": codigo, "respuesta": mensaje}
    return None

def actualizar_consulta(codigo, respuesta):
    """Actualiza una consulta con la respuesta del asesor."""
    logger.info(f"✅ Consulta {codigo} respondida: {respuesta}")
    return True

def obtener_telefono_cliente(codigo):
    """
    Obtiene el teléfono del cliente a partir del código de consulta.
    CORREGIDO: Elimina el prefijo 'whatsapp:' para evitar duplicación.
    """
    logger.info(f"🔍 [obtener_telefono_cliente] Buscando teléfono para código {codigo}...")
    try:
        service = build('sheets', 'v4', credentials=config.CREDENTIALS)
        
        result = service.spreadsheets().values().get(
            spreadsheetId=config.SPREADSHEETS["CONSULTAS"],
            range='A:C'
        ).execute()
        datos = result.get('values', [])
        
        if not datos or len(datos) < 2:
            logger.warning("⚠️ [obtener_telefono_cliente] No hay datos en CONSULTAS")
            return None
        
        for fila in datos[1:]:
            if len(fila) >= 3 and fila[0].strip() == codigo.strip():
                telefono = fila[2].strip()
                # CORREGIDO: Eliminar el prefijo "whatsapp:" si existe
                telefono = telefono.replace('whatsapp:', '')
                logger.info(f"✅ [obtener_telefono_cliente] Teléfono encontrado: {telefono}")
                return telefono
        
        logger.warning(f"⚠️ [obtener_telefono_cliente] No se encontró el código {codigo}")
        return None
    except Exception as e:
        logger.error(f"❌ [obtener_telefono_cliente] Error: {e}")
        return None

def verificar_timeout():
    """Verifica consultas sin respuesta."""
    try:
        service = build('sheets', 'v4', credentials=config.CREDENTIALS)
        
        result = service.spreadsheets().values().get(
            spreadsheetId=config.SPREADSHEETS["CONSULTAS"],
            range='A:F'
        ).execute()
        datos = result.get('values', [])
        
        if not datos or len(datos) < 2:
            return
        
        ahora = datetime.now()
        for fila in datos[1:]:
            if len(fila) >= 4 and fila[4] == "Pendiente":
                try:
                    fecha_consulta = datetime.strptime(fila[1], "%Y-%m-%d %H:%M:%S")
                    if (ahora - fecha_consulta) > timedelta(minutes=TIMEOUT_MINUTOS):
                        logger.info(f"⏰ Timeout: consulta {fila[0]} sin respuesta después de {TIMEOUT_MINUTOS} minutos.")
                except:
                    pass
    except Exception as e:
        logger.error(f"❌ [verificar_timeout] Error: {e}")

# ============================================================
# 7. NUEVAS FUNCIONES PARA TIMEOUTS AVANZADOS
# ============================================================

def enviar_whatsapp(destino, mensaje):
    """
    Envía un mensaje de WhatsApp REAL usando Twilio.
    """
    try:
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        from_number = os.environ.get('TWILIO_WHATSAPP_NUMBER')
        
        if not account_sid or not auth_token or not from_number:
            logger.error("❌ Faltan variables de entorno de Twilio")
            return False
        
        # Asegurar formato del número
        if not destino.startswith('+'):
            destino = '+' + destino
        if not destino.startswith('whatsapp:'):
            destino = f'whatsapp:{destino}'
        
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            from_=f'whatsapp:{from_number}',
            body=mensaje,
            to=destino
        )
        logger.info(f"✅ Mensaje enviado a {destino}. SID: {message.sid}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error al enviar mensaje: {e}")
        return False

def enviar_recordatorio_asesor(codigo, consulta, telefono_cliente, asesor):
    """
    Envía un recordatorio al asesor después de 3 minutos.
    """
    mensaje = f"""
⏰ *Recordatorio: Consulta pendiente*

Código: {codigo}
Cliente: {telefono_cliente}
Consulta: "{consulta}"
Tiempo transcurrido: {TIMEOUT_RECORDATORIO} minutos

👉 ¿Puedes atender esta consulta?
Responde con: Respuesta {codigo}: [tu mensaje]
"""
    logger.info(f"⏰ Enviando recordatorio al asesor {asesor['nombre']} para consulta {codigo}")
    return enviar_whatsapp(asesor["telefono"], mensaje)

def reasignar_asesor(codigo, consulta, telefono_cliente):
    """
    Reasigna una consulta al siguiente asesor disponible.
    """
    logger.info(f"🔄 [reasignar_asesor] Reasignando consulta {codigo}")
    
    asesores = cargar_asesores()
    if len(asesores) <= 1:
        logger.info(f"⚠️ Solo hay un asesor, no se puede reasignar")
        return None
    
    # Buscar el siguiente asesor (rotar)
    asesor_nuevo = asesores[1] if len(asesores) > 1 else asesores[0]
    
    # Actualizar el estado en CONSULTAS a "Reasignado"
    try:
        service = build('sheets', 'v4', credentials=config.CREDENTIALS)
        
        # Buscar la fila del código
        result = service.spreadsheets().values().get(
            spreadsheetId=config.SPREADSHEETS["CONSULTAS"],
            range='A:F'
        ).execute()
        datos = result.get('values', [])
        
        for i, fila in enumerate(datos):
            if len(fila) > 0 and fila[0] == codigo:
                # Actualizar estado a "Reasignado"
                fila_excel = i + 1
                rango_celda = f'E{fila_excel}'
                
                body = {'values': [["Reasignado"]]}
                service.spreadsheets().values().update(
                    spreadsheetId=config.SPREADSHEETS["CONSULTAS"],
                    range=rango_celda,
                    valueInputOption='USER_ENTERED',
                    body=body
                ).execute()
                
                logger.info(f"✅ Consulta {codigo} reasignada a {asesor_nuevo['nombre']}")
                
                # Notificar al nuevo asesor
                texto_notificacion = f"""
🔄 *Consulta reasignada*

Código: {codigo}
Cliente: {telefono_cliente}
Consulta: "{consulta}"

El asesor anterior no respondió en {TIMEOUT_REASIGNAR} minutos.
👉 Respondé con: Respuesta {codigo}: [tu mensaje]
"""
                enviar_whatsapp(asesor_nuevo["telefono"], texto_notificacion)
                
                return asesor_nuevo
                
    except Exception as e:
        logger.error(f"❌ Error al reasignar: {e}")
        return None

def responder_cliente_timeout(codigo, telefono_cliente):
    """
    Envía un mensaje al cliente cuando pasa el timeout de 5 minutos (sin reasignación).
    """
    mensaje = f"""
😔 Disculpa la demora, todos nuestros asesores se encuentran ocupados.

Tu consulta *{codigo}* aún no ha sido respondida pero está en nuestra lista de espera.

📌 ¿Preferís esperar o dejar un mensaje para que te contactemos por mail?
1️⃣ Esperar
2️⃣ Dejar mensaje (te respondemos por mail)
"""
    logger.info(f"⏰ Enviando mensaje de espera al cliente {telefono_cliente} para consulta {codigo}")
    return enviar_whatsapp(telefono_cliente, mensaje)

def responder_cliente_timeout_final(codigo, telefono_cliente):
    """
    Envía un mensaje final al cliente cuando pasa el timeout de 8 minutos.
    """
    mensaje = f"""
😔 Te pedimos disculpas por no poder atender tu consulta. Todos nuestros asesores se encuentran ocupados.

Tu consulta *{codigo}* no pudo ser atendida en este momento.

📌 Alternativas:
• Visita nuestra web: www.carpinteriaradi.com.ar
• Envíanos un mail a: carpinteriaradi@gmail.com
• Volvé a intentar más tarde

¡Gracias por contactarnos!
"""
    logger.info(f"⏰ Enviando mensaje final al cliente {telefono_cliente} para consulta {codigo}")
    return enviar_whatsapp(telefono_cliente, mensaje)

def verificar_timeout_avanzado():
    """
    Verifica consultas sin respuesta y toma acción según el tiempo:
    - A los 3 min: Envía recordatorio al asesor
    - A los 5 min: Reasigna a otro asesor (si existe) o avisa al cliente
    - A los 8 min: Mensaje final al cliente
    """
    logger.info("⏰ [verificar_timeout_avanzado] Verificando consultas pendientes...")
    
    try:
        service = build('sheets', 'v4', credentials=config.CREDENTIALS)
        
        result = service.spreadsheets().values().get(
            spreadsheetId=config.SPREADSHEETS["CONSULTAS"],
            range='A:F'
        ).execute()
        datos = result.get('values', [])
        
        if not datos or len(datos) < 2:
            logger.info("⏰ No hay consultas pendientes")
            return
        
        ahora = datetime.now()
        asesores = cargar_asesores()
        asesor_actual = asesores[0] if asesores else None
        
        for fila in datos[1:]:
            # Verificar que tenga al menos 5 columnas y esté Pendiente
            if len(fila) >= 5 and fila[4] == "Pendiente":
                try:
                    # Parsear fecha
                    fecha_consulta = datetime.strptime(fila[1], "%Y-%m-%d %H:%M:%S")
                    tiempo_transcurrido = (ahora - fecha_consulta).total_seconds() / 60  # en minutos
                    
                    codigo = fila[0]
                    telefono_cliente = fila[2] if len(fila) > 2 else ""
                    consulta = fila[3] if len(fila) > 3 else ""
                    
                    # --- 3 minutos: Recordatorio al asesor ---
                    if tiempo_transcurrido >= TIMEOUT_RECORDATORIO and tiempo_transcurrido < TIMEOUT_REASIGNAR:
                        logger.info(f"⏰ [3 min] Recordatorio para consulta {codigo} ({tiempo_transcurrido:.1f} min)")
                        if asesor_actual:
                            enviar_recordatorio_asesor(codigo, consulta, telefono_cliente, asesor_actual)
                    
                    # --- 5 minutos: Reasignar o avisar al cliente ---
                    elif tiempo_transcurrido >= TIMEOUT_REASIGNAR and tiempo_transcurrido < TIMEOUT_FINAL:
                        logger.info(f"⏰ [5 min] Procesando consulta {codigo} ({tiempo_transcurrido:.1f} min)")
                        
                        if len(asesores) > 1:
                            # Reasignar a otro asesor
                            reasignar_asesor(codigo, consulta, telefono_cliente)
                        else:
                            # Solo hay un asesor, avisar al cliente
                            responder_cliente_timeout(codigo, telefono_cliente)
                    
                    # --- 8 minutos: Mensaje final al cliente ---
                    elif tiempo_transcurrido >= TIMEOUT_FINAL:
                        logger.info(f"⏰ [8 min] Timeout final para consulta {codigo} ({tiempo_transcurrido:.1f} min)")
                        
                        # Actualizar estado a "Abandonada"
                        fila_excel = datos.index(fila) + 1
                        rango_celda = f'E{fila_excel}'
                        body = {'values': [["Abandonada"]]}
                        service.spreadsheets().values().update(
                            spreadsheetId=config.SPREADSHEETS["CONSULTAS"],
                            range=rango_celda,
                            valueInputOption='USER_ENTERED',
                            body=body
                        ).execute()
                        
                        # Enviar mensaje final al cliente
                        responder_cliente_timeout_final(codigo, telefono_cliente)
                        
                except Exception as e:
                    logger.error(f"❌ Error procesando fila {fila}: {e}")
                    continue
                    
    except Exception as e:
        logger.error(f"❌ [verificar_timeout_avanzado] Error general: {e}")
        import traceback
        traceback.print_exc()
