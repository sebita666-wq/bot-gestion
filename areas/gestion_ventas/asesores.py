# areas/gestion_ventas/asesores.py
# Sistema de chat en vivo con asesores

from utils import planillas
from utils import config
from datetime import datetime, timedelta

# Lista de asesores (orden de prioridad)
ASESORES = [
    {"nombre": "Diego", "telefono": "+5493435123123"},  # Reemplazar con número real
    {"nombre": "Carlos", "telefono": "+5493435987654"},
    {"nombre": "Laura", "telefono": "+5493435112233"}
]

# Tiempo de espera en minutos antes de considerar que el asesor no responde
TIMEOUT_MINUTOS = 5

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
    """
    Crea una nueva consulta de cliente.
    Asigna un código C-XXXX y lo guarda en CONSULTAS.
    """
    codigo = generar_codigo_consulta()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    nueva_consulta = [[
        codigo,
        fecha,
        telefono_cliente,
        mensaje,
        "Pendiente",  # Estado inicial
        ""  # Respuesta del asesor
    ]]
    
    if planillas.escribir_datos(config.SPREADSHEETS["CONSULTAS"], 'A:F', nueva_consulta):
        return {
            "codigo": codigo,
            "estado": "Pendiente"
        }
    return None

def notificar_asesor(codigo, telefono_cliente, mensaje):
    """
    Notifica al asesor (el primero de la lista) sobre una nueva consulta.
    En producción, esto enviaría un mensaje de WhatsApp al asesor.
    """
    # Buscar el primer asesor disponible (simplificado)
    asesor = ASESORES[0]
    texto = f"""
📞 *Nueva consulta de cliente*

Código: {codigo}
Cliente: {telefono_cliente}
Consulta: "{mensaje}"

👉 Respondé copiando esta línea y agregando tu mensaje:
Respuesta {codigo}:
"""
    print(f"📱 Enviando a {asesor['telefono']}:")
    print(texto)
    print("-" * 50)
    return True

def procesar_respuesta_asesor(respuesta):
    """
    Procesa la respuesta del asesor.
    Busca el código C-XXXX y extrae la respuesta.
    """
    lineas = respuesta.split('\n')
    for linea in lineas:
        if linea.strip().startswith("Respuesta C-"):
            partes = linea.split(":", 1)
            if len(partes) == 2:
                codigo = partes[0].strip().split(" ")[1]  # "Respuesta C-0001" → "C-0001"
                mensaje = partes[1].strip()
                return {
                    "codigo": codigo,
                    "respuesta": mensaje
                }
    return None

def actualizar_consulta(codigo, respuesta):
    """
    Actualiza una consulta con la respuesta del asesor.
    """
    # Esta función es simplificada; en la práctica, actualizarías la fila en Sheets
    print(f"✅ Consulta {codigo} respondida: {respuesta}")
    return True

def verificar_timeout():
    """
    Verifica consultas que llevan más de TIMEOUT_MINUTOS sin respuesta.
    En producción, se ejecutaría como un proceso en segundo plano.
    """
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
                    # Aquí se podría derivar al siguiente asesor o notificar al admin
            except:
                pass
