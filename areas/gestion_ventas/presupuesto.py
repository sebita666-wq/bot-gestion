# areas/gestion_ventas/presupuesto.py
# Flujo de presupuestos - VERSIÓN COMPLETA CON ACEPTACIÓN/RECHAZO/MODIFICACIONES

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
    "APROBADO": "Aprobado por dueño",
    "ENVIADO": "Enviado al cliente",
    "MODIFICADO": "Modificado",
    "ACEPTADO": "Aceptado por cliente",
    "RECHAZADO": "Rechazado por cliente",
    "PENDIENTE_AJUSTE": "Pendiente de ajuste",
    "CONFIRMADO": "Confirmado - Pendiente producción",
    "PAGADO": "Pagado",
    "ENTREGADO": "Entregado"
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
    """
    Crea un nuevo presupuesto.
    """
    # 1. Identificar o crear al cliente
    cliente = None
    if dni:
        cliente = clientes.buscar_por_dni(dni)
        if not cliente:
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
    else:
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
        "",  # Cuotas pagadas
        ""   # Modificaciones solicitadas
    ]]
    
    if planillas.escribir_datos(config.SPREADSHEETS["PEDIDOS"], 'A:M', nuevo_pedido):
        logger.info(f"✅ Presupuesto {numero_presupuesto} creado para {cliente['nombre']}")
        return {
            "estado": True,
            "numero": numero_presupuesto,
            "cliente": cliente
        }
    else:
        return {"error": "Error al guardar presupuesto", "estado": False}

def obtener_presupuesto(numero):
    """Obtiene los datos de un presupuesto por su número"""
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
    """
    Actualiza el estado de un presupuesto en la planilla.
    """
    try:
        datos = planillas.leer_datos(config.SPREADSHEETS["PEDIDOS"], 'A:M')
        if not datos or len(datos) < 2:
            logger.error(f"❌ No se encontraron datos para actualizar {numero}")
            return False
        
        fila_encontrada = None
        for i, fila in enumerate(datos):
            if len(fila) > 0 and fila[0].strip() == numero.strip():
                fila_encontrada = i
                break
        
        if fila_encontrada is None:
            logger.error(f"❌ Presupuesto {numero} no encontrado")
            return False
        
        fila_excel = fila_encontrada + 1
        rango_celda = f'I{fila_excel}'
        
        return planillas.actualizar_celda(
            config.SPREADSHEETS["PEDIDOS"],
            rango_celda,
            nuevo_estado
        )
        
    except Exception as e:
        logger.error(f"❌ Error al actualizar estado: {e}")
        return False

def actualizar_precio(numero, nuevo_precio):
    """
    Actualiza el precio de un presupuesto.
    """
    try:
        datos = planillas.leer_datos(config.SPREADSHEETS["PEDIDOS"], 'A:M')
        if not datos or len(datos) < 2:
            return False
        
        fila_encontrada = None
        for i, fila in enumerate(datos):
            if len(fila) > 0 and fila[0].strip() == numero.strip():
                fila_encontrada = i
                break
        
        if fila_encontrada is None:
            return False
        
        fila_excel = fila_encontrada + 1
        rango_celda = f'H{fila_excel}'
        
        return planillas.actualizar_celda(
            config.SPREADSHEETS["PEDIDOS"],
            rango_celda,
            nuevo_precio
        )
        
    except Exception as e:
        logger.error(f"❌ Error al actualizar precio: {e}")
        return False

def guardar_modificacion(numero, texto_modificacion):
    """
    Guarda el texto de modificación en el presupuesto.
    """
    try:
        datos = planillas.leer_datos(config.SPREADSHEETS["PEDIDOS"], 'A:M')
        if not datos or len(datos) < 2:
            return False
        
        fila_encontrada = None
        for i, fila in enumerate(datos):
            if len(fila) > 0 and fila[0].strip() == numero.strip():
                fila_encontrada = i
                break
        
        if fila_encontrada is None:
            return False
        
        fila_excel = fila_encontrada + 1
        rango_celda = f'M{fila_excel}'
        
        return planillas.actualizar_celda(
            config.SPREADSHEETS["PEDIDOS"],
            rango_celda,
            texto_modificacion
        )
        
    except Exception as e:
        logger.error(f"❌ Error al guardar modificación: {e}")
        return False

def actualizar_forma_pago(numero, forma_pago):
    """
    Actualiza la forma de pago de un presupuesto.
    """
    try:
        datos = planillas.leer_datos(config.SPREADSHEETS["PEDIDOS"], 'A:M')
        if not datos or len(datos) < 2:
            return False
        
        fila_encontrada = None
        for i, fila in enumerate(datos):
            if len(fila) > 0 and fila[0].strip() == numero.strip():
                fila_encontrada = i
                break
        
        if fila_encontrada is None:
            return False
        
        fila_excel = fila_encontrada + 1
        rango_celda = f'J{fila_excel}'
        
        return planillas.actualizar_celda(
            config.SPREADSHEETS["PEDIDOS"],
            rango_celda,
            forma_pago
        )
        
    except Exception as e:
        logger.error(f"❌ Error al actualizar forma de pago: {e}")
        return False

def obtener_presupuestos_por_dni(dni):
    """
    Obtiene todos los presupuestos de un cliente por DNI.
    """
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
