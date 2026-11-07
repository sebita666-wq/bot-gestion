# areas/gestion_ventas/presupuesto.py
# Motor de presupuestos: búsqueda flexible de DNI/CUIT.

from utils import planillas
from utils import config
from areas.gestion_ventas import clientes
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)

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
    try:
        datos = planillas.leer_datos(config.SPREADSHEETS["PEDIDOS"], 'A:A')
        if not datos or len(datos) < 2:
            return "P-0001"
        ultimo_numero = "P-0000"
        for fila in datos[1:]:
            if len(fila) > 0 and fila[0].startswith("P-"):
                if fila[0] > ultimo_numero:
                    ultimo_numero = fila[0]
        num = int(ultimo_numero.split("-")[1]) + 1
        return f"P-{num:04d}"
    except Exception as e:
        logger.error(f"❌ Error al generar número: {e}")
        return "P-0001"

def crear_presupuesto(sender, producto, personalizacion, dni=None, nombre=None, telefono=None):
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
        producto, personalizacion, "", ESTADOS["PENDIENTE"], "", "", "", ""
    ]]
    
    if planillas.escribir_datos(config.SPREADSHEETS["PEDIDOS"], 'A:M', nuevo_pedido):
        return {"estado": True, "numero": numero_presupuesto, "cliente": cliente}
    else:
        return {"error": "Error al guardar presupuesto", "estado": False}

def obtener_presupuesto(numero):
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

# ... (Acá van las funciones actualizar_estado, actualizar_precio, etc. que no cambian).

def obtener_presupuestos_por_dni(dni):
    datos = planillas.leer_datos(config.SPREADSHEETS["PEDIDOS"], 'A:M')
    if not datos or len(datos) < 2:
        return []
    
    resultados = []
    busqueda = str(dni).strip()
    if len(busqueda) == 11:
        busqueda_dni = busqueda[2:10]
    else:
        busqueda_dni = busqueda

    for fila in datos[1:]:
        if len(fila) > 2:
            dni_guardado = fila[2].strip()
            if busqueda in dni_guardado or (len(busqueda_dni) == 8 and busqueda_dni in dni_guardado):
                resultados.append({
                    "numero": fila[0] if len(fila) > 0 else "",
                    "fecha": fila[1] if len(fila) > 1 else "",
                    "producto": fila[5] if len(fila) > 5 else "",
                    "estado": fila[8] if len(fila) > 8 else "",
                    "precio": fila[7] if len(fila) > 7 else ""
                })
    return resultados

def obtener_presupuestos_pendientes(dni):
    try:
        datos = planillas.leer_datos(config.SPREADSHEETS["PEDIDOS"], 'A:M')
        if not datos or len(datos) < 2:
            return []
        
        resultados = []
        busqueda = str(dni).strip()
        if len(busqueda) == 11:
            busqueda_dni = busqueda[2:10]
        else:
            busqueda_dni = busqueda

        for fila in datos[1:]:
            if len(fila) > 2:
                dni_guardado = fila[2].strip()
                if busqueda in dni_guardado or (len(busqueda_dni) == 8 and busqueda_dni in dni_guardado):
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
