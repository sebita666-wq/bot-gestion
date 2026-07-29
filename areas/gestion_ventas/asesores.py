# areas/gestion_ventas/asesores.py
# Sistema de chat en vivo con asesores - CON LOGS Y FORMATO CORREGIDO

from utils import planillas
from utils import config
from datetime import datetime, timedelta
import logging

# Configurar logger para este módulo
logger = logging.getLogger(__name__)

TIMEOUT_MINUTOS = 5

# ============================================================
# 1. FUNCIONES DE ASESORES (desde Google Sheets)
# ============================================================

def cargar_asesores():
    """Carga la lista de asesores desde la planilla ASESORES."""
    logger.info("📋 [cargar_asesores] Leyendo ASESORES desde Google Sheets...")
    datos = planillas.leer_datos(config.SPREADSHEETS["ASESORES"], 'A:C')
    if not datos or len(datos) < 2:
        logger.warning("⚠️ [cargar_asesores] No hay datos, usando lista por defecto")
        return [{"orden": 1, "telefono": "5493434727811", "nombre": "Sebastian"}]
    
    asesores = []
    for fila in datos[1:]:
        if len(fila) >= 3 and fila[1].strip():
            asesores.append({
                "orden": int(fila[0]) if fila[0].isdigit() else 0,
                "telefono": fila[1].strip(),
                "nombre": fila[2].strip() if len(fila) > 2 else "Asesor"
            })
    asesores.sort(key=lambda x: x["orden"])
    logger.info(f"✅ [cargar_asesores] {len(asesores)} asesores cargados.")
    return asesores

def obtener_asesor_activo():
    asesores = cargar_asesores()
    return asesores[0] if asesores else None

# ============================================================
# 2. GENERACIÓN DE CÓDIGO DE CONSULTA
# ============================================================

def generar_codigo_consulta():
    """Genera el próximo código de consulta (C-XXXX)"""
    logger.info("🔢 [generar_codigo_consulta] Generando código...")
    try:
        datos = planillas.leer_datos(config.SPREADSHEETS["CONSULTAS"], 'A:A')
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
# 3. CREACIÓN DE CONSULTA (ESCRITURA EN SHEETS) - CORREGIDO
# ============================================================

def crear_consulta(sender, telefono_cliente, mensaje):
    """Crea una nueva consulta de cliente."""
    logger.info("🚨 [crear_consulta] ¡ESTA FUNCIÓN SE ESTÁ EJECUTANDO!")
    logger.info(f"   🔍 [crear_consulta] Iniciando para {telefono_cliente}")
    logger.info(f"   🔍 [crear_consulta] Mensaje: {mensaje[:50]}...")
    
    # 1. Generar código
    codigo = generar_codigo_consulta()
    logger.info(f"   ✅ [crear_consulta] Código generado: {codigo}")
    
    # 2. Preparar datos (en el mismo formato que el script de prueba)
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nueva_consulta = [
        [codigo, fecha, telefono_cliente, mensaje, "Pendiente", ""]
    ]
    logger.info(f"   📝 [crear_consulta] Datos a guardar: {nueva_consulta}")
    
    # 3. Intentar escribir en la planilla
    sheet_id = config.SPREADSHEETS["CONSULTAS"]
    logger.info(f"   📤 [crear_consulta] Escribiendo en CONSULTAS (ID: {sheet_id})...")
    
    try:
        resultado = planillas.escribir_datos(sheet_id, 'A:F', nueva_consulta)
        logger.info(f"   📥 [crear_consulta] Resultado de escritura: {resultado}")
        
        if resultado:
            logger.info("   ✅ [crear_consulta] Consulta guardada exitosamente")
            return {"codigo": codigo, "estado": "Pendiente"}
        else:
            logger.error("   ❌ [crear_consulta] planillas.escribir_datos devolvió False")
            return None
    except Exception as e:
        logger.error(f"   ❌ [crear_consulta] EXCEPCIÓN: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================================
# 4. NOTIFICACIÓN AL ASESOR
# ============================================================

def notificar_asesor(codigo, telefono_cliente, mensaje):
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
    return True

# ============================================================
# 5. PROCESADOR PRINCIPAL DE CONSULTA
# ============================================================

def procesar_consulta(sender, mensaje):
    """Procesa la consulta de un cliente que está en el flujo de asesor."""
    logger.info("🚨 [procesar_consulta] ¡ESTA FUNCIÓN SE ESTÁ EJECUTANDO!")
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

def verificar_timeout():
    """Verifica consultas sin respuesta."""
    datos = planillas.leer_datos(config.SPREADSHEETS["CONSULTAS"], 'A:F')
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
