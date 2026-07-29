# areas/gestion_ventas/asesores.py
# Sistema de chat en vivo con asesores (LEE DESDE GOOGLE SHEETS)

from utils import planillas
from utils import config
from datetime import datetime, timedelta

# Tiempo de espera en minutos antes de considerar que el asesor no responde
TIMEOUT_MINUTOS = 5

def cargar_asesores():
    """
    Carga la lista de asesores desde la planilla ASESORES en Google Sheets.
    La planilla debe tener las columnas: Orden, Telefono, Nombre.
    """
    datos = planillas.leer_datos(config.SPREADSHEETS["ASESORES"], 'A:C')
    if not datos or len(datos) < 2:
        # Si no hay datos, usar una lista por defecto
        return [
            {"orden": 1, "telefono": "5493434727811", "nombre": "Sebastian"}
        ]
    
    asesores = []
    for fila in datos[1:]:  # Saltar la fila de encabezados
        if len(fila) >= 3 and fila[1].strip():  # Si tiene teléfono
            asesores.append({
                "orden": int(fila[0]) if fila[0].isdigit() else 0,
                "telefono": fila[1].strip(),
                "nombre": fila[2].strip() if len(fila) > 2 else "Asesor"
            })
    
    # Ordenar por la columna "Orden"
    asesores.sort(key=lambda x: x["orden"])
    return asesores

def obtener_asesor_activo():
    """Obtiene el primer asesor de la lista (orden 1)."""
    asesores = cargar_asesores()
    if asesores:
        return asesores[0]  # El de orden 1
    return None

def generar_codigo_consulta():
    """Genera el próximo código de consulta (C-XXXX)"""
    datos = planillas.leer_datos(config.SPREADSHEETS["CONSULTAS"], 'A:A')
    if not datos or len(datos) < 2:
        return "C-0001"
    
    ultimo_codigo = "C-0000"
    for fila in datos[1:]:
        if len(fila) > 0 and fila[0].startswith("C-"):
            if fila[0] > ultimo_codigo:
                ultimo_codigo = fila[0]
    
    try:
        num = int(ultimo_codigo.split("-")[1]) + 1
        return f"C-{num:04d}"
    except:
        return "C-0001"

def crear_consulta(sender, telefono_cliente, mensaje):
    """Crea una nueva consulta de cliente. Asigna un código C-XXXX y lo guarda en CONSULTAS."""
    codigo = generar_codigo_consulta()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    nueva_consulta = [[
        codigo,
        fecha,
        telefono_cliente,
        mensaje,
        "Pendiente",
        ""  # Respuesta del asesor
    ]]
    
    if planillas.escribir_datos(config.SPREADSHEETS["CONSULTAS"], 'A:F', nueva_consulta):
        return {"codigo": codigo, "estado": "Pendiente"}
    return None

def notificar_asesor(codigo, telefono_cliente, mensaje):
    """Notifica al primer asesor (orden 1) sobre una nueva consulta."""
    asesor = obtener_asesor_activo()
    if not asesor:
        print("❌ No hay asesores disponibles.")
        return False
    
    # Asegurar que el número tenga el formato correcto para WhatsApp
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
    print(f"📱 Enviando a {asesor['nombre']} ({telefono_asesor}):")
    print(texto)
    print("-" * 50)
    return True

def procesar_consulta(sender, mensaje):
    """Procesa la consulta de un cliente que está en el flujo de asesor."""
    print(f"   📞 Procesando consulta de asesor para {sender}")
    
    consulta = crear_consulta(sender, sender, mensaje)
    if consulta:
        notificar_asesor(consulta["codigo"], sender, mensaje)
        return f"""
✅ *Consulta enviada*

Tu consulta fue registrada con el código *{consulta['codigo']}*.

Un asesor te va a responder por este mismo chat en breve.

😊 Gracias por tu paciencia.
"""
    else:
        return """
❌ *Error al enviar tu consulta*

Hubo un problema al registrar tu consulta. Por favor, intentá de nuevo más tarde.

😊 Disculpá las molestias.
"""

def procesar_respuesta_asesor(respuesta):
    """Procesa la respuesta del asesor. Busca el código C-XXXX y extrae la respuesta."""
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
    print(f"✅ Consulta {codigo} respondida: {respuesta}")
    return True

def verificar_timeout():
    """Verifica consultas que llevan más de TIMEOUT_MINUTOS sin respuesta."""
    datos = planillas.leer_datos(config.SPREADSHEETS["CONSULTAS"], 'A:F')
    if not datos or len(datos) < 2:
        return
    
    ahora = datetime.now()
    for fila in datos[1:]:
        if len(fila) >= 4 and fila[4] == "Pendiente":
            try:
                fecha_consulta = datetime.strptime(fila[1], "%Y-%m-%d %H:%M:%S")
                if (ahora - fecha_consulta) > timedelta(minutes=TIMEOUT_MINUTOS):
                    print(f"⏰ Timeout: consulta {fila[0]} sin respuesta después de {TIMEOUT_MINUTOS} minutos.")
            except:
                pass
