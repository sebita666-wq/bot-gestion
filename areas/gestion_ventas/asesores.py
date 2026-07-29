# areas/gestion_ventas/asesores.py
# Sistema de chat en vivo con asesores

from utils import planillas
from utils import config
from datetime import datetime, timedelta

TIMEOUT_MINUTOS = 5

def cargar_asesores():
    """Carga la lista de asesores desde la planilla ASESORES en Google Sheets."""
    datos = planillas.leer_datos(config.SPREADSHEETS["ASESORES"], 'A:C')
    if not datos or len(datos) < 2:
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
    return asesores

def obtener_asesor_activo():
    asesores = cargar_asesores()
    return asesores[0] if asesores else None

# ========== FUNCIÓN QUE FALTABA ==========
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
    print(f"   🔍 [crear_consulta] Iniciando para {telefono_cliente}")
    codigo = generar_codigo_consulta()
    print(f"   ✅ [crear_consulta] Código generado: {codigo}")
    
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nueva_consulta = [[codigo, fecha, telefono_cliente, mensaje, "Pendiente", ""]]
    
    print(f"   📤 [crear_consulta] Escribiendo en CONSULTAS...")
    try:
        resultado = planillas.escribir_datos(config.SPREADSHEETS["CONSULTAS"], 'A:F', nueva_consulta)
        if resultado:
            return {"codigo": codigo, "estado": "Pendiente"}
        else:
            print(f"   ❌ [crear_consulta] planillas.escribir_datos devolvió False")
            return None
    except Exception as e:
        print(f"   ❌ [crear_consulta] EXCEPCIÓN: {e}")
        import traceback
        traceback.print_exc()
        return None

def notificar_asesor(codigo, telefono_cliente, mensaje):
    asesor = obtener_asesor_activo()
    if not asesor:
        print("❌ No hay asesores disponibles.")
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
    print(f"📱 Enviando a {asesor['nombre']} ({telefono_asesor}):")
    print(texto)
    return True

def procesar_consulta(sender, mensaje):
    print(f"   📞 [procesar_consulta] Iniciando para {sender}")
    
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
