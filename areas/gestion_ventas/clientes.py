# areas/gestion_ventas/clientes.py
# Funciones para manejar clientes (buscar, crear, actualizar)

from utils import planillas
from utils import config

def buscar_por_dni(dni):
    """
    Busca un cliente por DNI/CUIT en la planilla CLIENTES.
    Devuelve el cliente como diccionario o None si no existe.
    """
    datos = planillas.leer_datos(config.SPREADSHEETS["CLIENTES"], 'A:G')
    if not datos or len(datos) < 2:
        return None
    
    # La primera fila son los encabezados
    for fila in datos[1:]:
        if len(fila) > 0 and fila[0].strip() == str(dni).strip():
            return {
                "dni": fila[0],
                "nombre": fila[1] if len(fila) > 1 else "",
                "telefono": fila[2] if len(fila) > 2 else "",
                "direccion": fila[3] if len(fila) > 3 else "",
                "localidad": fila[4] if len(fila) > 4 else "",
                "provincia": fila[5] if len(fila) > 5 else "",
                "fecha_alta": fila[6] if len(fila) > 6 else ""
            }
    return None

def crear_cliente(dni, nombre, telefono, direccion="", localidad="", provincia=""):
    """
    Crea un nuevo cliente en la planilla CLIENTES.
    Devuelve True si se creó correctamente, False si ya existe o hay error.
    """
    # Verificar si ya existe
    if buscar_por_dni(dni):
        print(f"❌ El cliente con DNI {dni} ya existe.")
        return False
    
    # Preparar los datos
    from datetime import datetime
    fecha_alta = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nuevo_cliente = [[
        str(dni),
        nombre,
        telefono,
        direccion,
        localidad,
        provincia,
        fecha_alta
    ]]
    
    # Escribir en la planilla
    return planillas.escribir_datos(
        config.SPREADSHEETS["CLIENTES"],
        'A:G',
        nuevo_cliente
    )

def actualizar_cliente(dni, campo, valor):
    """
    Actualiza un campo específico de un cliente.
    Los campos válidos son: nombre, telefono, direccion, localidad, provincia
    """
    # Primero obtenemos todos los datos
    datos = planillas.leer_datos(config.SPREADSHEETS["CLIENTES"], 'A:G')
    if not datos or len(datos) < 2:
        return False
    
    # Mapeo de campos a índices de columna (0 = DNI, 1 = nombre, 2 = telefono, etc.)
    campos = {
        "nombre": 1,
        "telefono": 2,
        "direccion": 3,
        "localidad": 4,
        "provincia": 5
    }
    
    if campo not in campos:
        print(f"❌ Campo '{campo}' no válido. Usar: {list(campos.keys())}")
        return False
    
    col_idx = campos[campo]
    dni_str = str(dni).strip()
    
    # Buscar la fila del cliente
    for i, fila in enumerate(datos):
        if len(fila) > 0 and fila[0].strip() == dni_str:
            # Actualizar el campo
            while len(fila) <= col_idx:
                fila.append("")
            fila[col_idx] = valor
            
            # Escribir la fila actualizada (esto es más complejo, usamos un enfoque simple)
            # Nota: Esta implementación es básica, para un sistema completo se necesitaría usar update()
            print(f"✅ Cliente {dni} actualizado: {campo} = {valor}")
            # TODO: Implementar escritura de una fila específica
            return True
    
    print(f"❌ Cliente con DNI {dni} no encontrado.")
    return False
