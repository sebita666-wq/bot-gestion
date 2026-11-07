# areas/gestion_ventas/presupuesto.py
# Motor de presupuestos: creación, lectura, actualización de estados, precios, cuotas y pendientes.

from utils import planillas
from utils import config
from areas.gestion_ventas import clientes
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Estados del presupuesto
ESTADOS = {
    "PENDIENTE": "Pendiente",
    "EN_REVISION": "En revisión por dueño",
    "ENVIADO": "Enviado al cliente",
    "MODIFICADO": "Modificado",
    "ACEPTADO": "Aceptado por cliente",
    "RECHAZADO": "Rechazado por cliente",
    "CONFIRMADO": "Confirmado - Pendiente producción"
}

def generar_numero_presupuesto():
    """Genera el próximo número de presupuesto correlativo (P-XXXX)"""
    try:
        datos = planillas.leer_datos(config.SPREADSHEETS["PEDIDOS"], 'A:A')
        if not datos or len(datos) < 2:
            logger.info("📝 Planilla vacía, primer presupuesto: P-0001")
            return "P-0001"
        
        ultimo_numero = "P-0000"
        for fila in datos[1:]:
            if len(fila) > 0 and fila[0].startswith("P-"):
                if fila[0] > ultimo_numero:
                    ultimo_numero = fila[0]
        
        num = int(ultimo_numero.split("-")[1]) + 1
        nuevo = f"P-{num:04d}"
        logger.info(f"✅ Nuevo número de presupuesto: {nuevo}")
        return nuevo
    except Exception as e:
        logger.error(f"❌ Error al generar número: {e}")
        return "P-0001"

def crear_presupuesto(sender, producto, personalizacion, dni=None, nombre=None, telefono=None):
    """Crea un nuevo presupuesto en la planilla PEDIDOS."""
    cliente = None
    if dni:
        cliente = clientes.buscar_por_dni(dni)
        if not cliente:
            if not nombre or not telefono:
                return {"error": "Faltan datos del cliente", "estado": False}
            if clientes.crear_cliente(dni, nombre, telefono):
                cliente = {"dni": dni, "nombre": nombre, "telefono": telefono}
            else:
                return {"error": "Error al crear cliente", "estado": False}
    else:
        return {"error": "Falta DNI", "estado": False}
    
    numero_presupuesto = generar_numero_presupuesto()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    nuevo_pedido = [[
        numero_presupuesto, fecha, cliente["dni"], cliente["nombre"], cliente["telefono"],
        producto, personalizacion, 
        "",  # Precio (H)
        ESTADOS["PENDIENTE"], # Estado (I)
        "",  # Forma de pago (J)
        "",  # Cuotas (K)
        "",  # Cuotas pagadas (L)
        ""   # Modificaciones solicitadas (M)
    ]]
    
    if planillas.escribir_datos(config.SPREADSHEETS["PEDIDOS"], 'A:M', nuevo_pedido):
        logger.info(f"✅ Presupuesto {numero_presupuesto} creado para {cliente['nombre']}")
        return {"estado": True, "numero": numero_presupuesto, "cliente": cliente}
    else:
        return {"error": "Error al guardar presupuesto", "estado": False}

def obtener_presupuesto(numero):
    """Obtiene los datos de un presupuesto por su número (P-XXXX)."""
    datos = planillas.leer_datos(config.SPREADSHEETS["PEDIDOS"], 'A:M')
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
                "cuotas_pagadas": fila[11] if len(fila) > 11 else "",
                "modificaciones": fila[12] if len(fila) > 12 else ""
            }
    return None

def actualizar_estado(numero, nuevo_estado):
    """Actualiza la columna I (Estado) de un presupuesto."""
    try:
        datos = planillas.leer_datos(config.SPREADSHEETS["PEDIDOS"], 'A:M')
        for i, fila in enumerate(datos):
            if len(fila) > 0 and fila[0].strip() == numero.strip():
                fila_excel = i + 1
                rango_celda = f'I{fila_excel}'
                return planillas.actualizar_celda(config.SPREADSHEETS["PEDIDOS"], rango_celda, nuevo_estado)
        return False
    except Exception as e:
        logger.error(f"❌ Error al actualizar estado: {e}")
        return False

def actualizar_precio(numero, nuevo_precio):
    """Actualiza la columna H (Precio)."""
    try:
        datos = planillas.leer_datos(config.SPREADSHEETS["PEDIDOS"], 'A:M')
        for i, fila in enumerate(datos):
            if len(fila) > 0 and fila[0].strip() == numero.strip():
                fila_excel = i + 1
                rango_celda = f'H{fila_excel}'
                return planillas.actualizar_celda(config.SPREADSHEETS["PEDIDOS"], rango_celda, nuevo_precio)
        return False
    except Exception as e:
        logger.error(f"❌ Error al actualizar precio: {e}")
        return False

def actualizar_forma_pago(numero, forma_pago):
    """Actualiza la columna J (Forma de pago)."""
    try:
        datos = planillas.leer_datos(config.SPREADSHEETS["PEDIDOS"], 'A:M')
        for i, fila in enumerate(datos):
            if len(fila) > 0 and fila[0].strip() == numero.strip():
                fila_excel = i + 1
                rango_celda = f'J{fila_excel}'
                return planillas.actualizar_celda(config.SPREADSHEETS["PEDIDOS"], rango_celda, forma_pago)
        return False
    except Exception as e:
        logger.error(f"❌ Error al actualizar forma de pago: {e}")
        return False

def actualizar_cuotas(numero, cantidad_cuotas):
    """Actualiza la columna K (Cuotas) de un presupuesto."""
    try:
        datos = planillas.leer_datos(config.SPREADSHEETS["PEDIDOS"], 'A:M')
        for i, fila in enumerate(datos):
            if len(fila) > 0 and fila[0].strip() == numero.strip():
                fila_excel = i + 1
                rango_celda = f'K{fila_excel}'
                return planillas.actualizar_celda(config.SPREADSHEETS["PEDIDOS"], rango_celda, cantidad_cuotas)
        return False
    except Exception as e:
        logger.error(f"❌ Error al actualizar cuotas: {e}")
        return False

def guardar_modificacion(numero, texto_modificacion):
    """Guarda el texto de modificación en la columna M."""
    try:
        datos = planillas.leer_datos(config.SPREADSHEETS["PEDIDOS"], 'A:M')
        for i, fila in enumerate(datos):
            if len(fila) > 0 and fila[0].strip() == numero.strip():
                fila_excel = i + 1
                rango_celda = f'M{fila_excel}'
                return planillas.actualizar_celda(config.SPREADSHEETS["PEDIDOS"], rango_celda, texto_modificacion)
        return False
    except Exception as e:
        logger.error(f"❌ Error al guardar modificación: {e}")
        return False

def obtener_presupuestos_por_dni(dni):
    """Para el flujo de Consultar Estado (Opción 2)."""
    datos = planillas.leer_datos(config.SPREADSHEETS["PEDIDOS"], 'A:M')
    if not datos or len(datos) < 2:
        return []
    
    resultados = []
    for fila in datos[1:]:
        if len(fila) > 2 and fila[2].strip() == str(dni).strip():
            resultados.append({
                "numero": fila[0] if len(fila) > 0 else "",
                "fecha": fila[1] if len(fila) > 1 else "",
                "producto": fila[5] if len(fila) > 5 else "",
                "estado": fila[8] if len(fila) > 8 else "",
                "precio": fila[7] if len(fila) > 7 else ""
            })
    return resultados

# ============================================================
# NUEVA FUNCIÓN: OBTENER PENDIENTES POR DNI (OPCIÓN 5)
# ============================================================
def obtener_presupuestos_pendientes(dni):
    """
    Busca presupuestos que estén pendientes (Enviados o Aceptados) para un DNI.
    """
    try:
        datos = planillas.leer_datos(config.SPREADSHEETS["PEDIDOS"], 'A:M')
        if not datos or len(datos) < 2:
            return []
        
        resultados = []
        dni_limpio = str(dni).strip()
        
        for fila in datos[1:]:
            # Comparamos el DNI (columna C, índice 2)
            if len(fila) > 2 and fila[2].strip() == dni_limpio:
                estado = fila[8] if len(fila) > 8 else ""
                if estado in ["Enviado al cliente", "Aceptado por cliente"]:
                    resultados.append({
                        "numero": fila[0],
                        "producto": fila[5],
                        "precio": fila[7],
                        "estado": estado
                    })
        return resultados
    except Exception as e:
        logger.error(f"❌ Error al buscar presupuestos pendientes: {e}")
        return []
