# areas/gestion_ventas/clientes.py
# Funciones para manejar clientes (buscar, crear, actualizar) - BLINDADO

from utils import planillas
from utils import config
import logging

logger = logging.getLogger(__name__)

def buscar_por_dni(dni):
    """
    Busca un cliente por DNI/CUIT en la planilla CLIENTES.
    Devuelve el cliente como diccionario o None si no existe.
    """
    try:
        datos = planillas.leer_datos(config.SPREADSHEETS["CLIENTES"], 'A:G')
        if not datos or len(datos) < 2:
            return None
        
        for fila in datos[1:]:
            if len(fila) > 0 and fila[0].strip() == str(dni).strip():
                # BLINDAJE: Aseguramos que existan las columnas mínimas (A, B, C)
                nombre = fila[1].strip() if len(fila) > 1 else "Cliente sin nombre"
                telefono = fila[2].strip() if len(fila) > 2 else ""
                
                # Si el teléfono está vacío, lo marcamos como error para que el bot pida de nuevo
                if not telefono:
                    return None 
                    
                return {
                    "dni": fila[0],
                    "nombre": nombre,
                    "telefono": telefono,
                    "direccion": fila[3] if len(fila) > 3 else "",
                    "localidad": fila[4] if len(fila) > 4 else "",
                    "provincia": fila[5] if len(fila) > 5 else "",
                    "fecha_alta": fila[6] if len(fila) > 6 else ""
                }
        return None
    except Exception as e:
        logger.error(f"❌ Error al buscar cliente por DNI: {e}")
        return None

def crear_cliente(dni, nombre, telefono, direccion="", localidad="", provincia=""):
    """Crea un nuevo cliente en la planilla CLIENTES."""
    if buscar_por_dni(dni):
        logger.info(f"❌ El cliente con DNI {dni} ya existe.")
        return False
    
    from datetime import datetime
    fecha_alta = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nuevo_cliente = [[
        str(dni), nombre, telefono, direccion, localidad, provincia, fecha_alta
    ]]
    
    return planillas.escribir_datos(config.SPREADSHEETS["CLIENTES"], 'A:G', nuevo_cliente)
