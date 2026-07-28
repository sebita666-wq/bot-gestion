# areas/gestion_ventas/presupuesto.py
# Flujo de presupuestos: cliente nuevo, existente, modificación, etc.

from utils import planillas
from utils import config
from areas.gestion_ventas import clientes
from datetime import datetime

# Estados del presupuesto
ESTADOS = {
    "PENDIENTE": "Pendiente",
    "EN_REVISION": "En revisión por dueño",
    "APROBADO": "Aprobado por dueño",
    "ENVIADO": "Enviado al cliente",
    "ACEPTADO": "Aceptado por cliente",
    "RECHAZADO": "Rechazado por cliente",
    "PENDIENTE_AJUSTE": "Pendiente de ajuste",
    "CONFIRMADO": "Confirmado - Pendiente producción"
}

def generar_numero_presupuesto():
    """Genera el próximo número de presupuesto correlativo (P-XXXX)"""
    datos = planillas.leer_datos(config.SPREADSHEETS["PEDIDOS"], 'A:A')
    if not datos or len(datos) < 2:
        return "P-0001"
    
    # Buscar el último número (columna A)
    ultimo_numero = "P-0000"
    for fila in datos[1:]:
        if len(fila) > 0 and fila[0].startswith("P-"):
            if fila[0] > ultimo_numero:
                ultimo_numero = fila[0]
    
    # Extraer el número y sumar 1
    try:
        num = int(ultimo_numero.split("-")[1]) + 1
        return f"P-{num:04d}"
    except:
        return "P-0001"

def crear_presupuesto(sender, producto, personalizacion, dni=None, nombre=None, telefono=None):
    """
    Crea un nuevo presupuesto.
    Si se pasa DNI, busca al cliente existente.
    Si no, crea un cliente nuevo (requiere nombre y teléfono).
    """
    # 1. Identificar o crear al cliente
    cliente = None
    if dni:
        cliente = clientes.buscar_por_dni(dni)
        if not cliente:
            return {"error": "Cliente no encontrado", "estado": False}
    else:
        # Crear cliente nuevo
        if not nombre or not telefono:
            return {"error": "Faltan datos del cliente", "estado": False}
        if clientes.crear_cliente(dni, nombre, telefono):
            cliente = {
                "dni": dni,
                "nombre": nombre,
                "telefono": telefono
            }
        else:
            return {"error": "Error al crear cliente", "estado": False}
    
    # 2. Generar número de presupuesto
    numero_presupuesto = generar_numero_presupuesto()
    
    # 3. Guardar en PEDIDOS
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nuevo_pedido = [[
        numero_presupuesto,
        fecha,
        cliente["dni"],
        cliente["nombre"],
        cliente["telefono"],
        producto,
        personalizacion,
        "",  # Precio (lo pone el dueño después)
        ESTADOS["PENDIENTE"],
        "",  # Forma de pago
        "",  # Cuotas
        ""   # Cuotas pagadas
    ]]
    
    if planillas.escribir_datos(config.SPREADSHEETS["PEDIDOS"], 'A:L', nuevo_pedido):
        return {
            "estado": True,
            "numero": numero_presupuesto,
            "cliente": cliente
        }
    else:
        return {"error": "Error al guardar presupuesto", "estado": False}

def obtener_presupuesto(numero):
    """Obtiene los datos de un presupuesto por su número"""
    datos = planillas.leer_datos(config.SPREADSHEETS["PEDIDOS"], 'A:L')
    if not datos or len(datos) < 2:
        return None
    
    for fila in datos[1:]:
        if len(fila) > 0 and fila[0].strip() == numero.strip():
            return {
                "numero": fila[0],
                "fecha": fila[1] if len(fila) > 1 else "",
                "dni": fila[2] if len(fila) > 2 else "",
                "nombre": fila[3] if len(fila) > 3 else "",
                "telefono": fila[4] if len(fila) > 4 else "",
                "producto": fila[5] if len(fila) > 5 else "",
                "personalizacion": fila[6] if len(fila) > 6 else "",
                "precio": fila[7] if len(fila) > 7 else "",
                "estado": fila[8] if len(fila) > 8 else "",
                "forma_pago": fila[9] if len(fila) > 9 else "",
                "cuotas": fila[10] if len(fila) > 10 else "",
                "cuotas_pagadas": fila[11] if len(fila) > 11 else ""
            }
    return None

def actualizar_estado(numero, nuevo_estado):
    """Actualiza el estado de un presupuesto"""
    # Esta es una versión simplificada
    # En la práctica, necesitarías actualizar la fila específica
    print(f"✅ Actualizando presupuesto {numero} a estado: {nuevo_estado}")
    # TODO: Implementar actualización directa en Sheets
    return True
