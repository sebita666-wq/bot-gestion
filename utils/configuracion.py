# utils/configuracion.py
# Lee los datos de la planilla CONFIGURACIÓN para que el bot sea genérico.

from utils import planillas
from utils import config
import logging

logger = logging.getLogger(__name__)

# Valores por defecto (por si la planilla falla o está vacía)
CONFIG_DEFAULT = {
    "nombre_negocio": "Carpintería Radi",
    "telefono_duenio": config.NUMERO_DUENIO,
    "email_soporte": "ventas@carpinteriaradi.com",
    "direccion_local": "Av. San Martín 123, Paraná",
    "horario_atencion": "Lunes a viernes de 9 a 18hs",
    "descuento_efectivo": "10",
    "interes_cuota": "0",
    "timeout_asesor": "5",
    "banco_transferencia": "Banco Nación",
    "cbu_transferencia": "1234567890123456789012",
    "alias_transferencia": "CARPINTERIA.RADI",
    "titular_cuenta": "Diego Pérez",
    "web_negocio": "www.carpinteriaradi.com.ar"
}

def obtener_configuracion():
    """
    Lee la planilla CONFIGURACIÓN y devuelve un diccionario con los datos.
    Si una clave no existe, usa el valor por defecto.
    """
    datos = CONFIG_DEFAULT.copy()
    
    try:
        # Leemos las columnas A (Clave) y B (Valor)
        filas = planillas.leer_datos(config.SPREADSHEETS["CONFIGURACIÓN"], 'A:B')
        
        if filas and len(filas) > 1:
            for fila in filas[1:]: # Salteamos el encabezado
                if len(fila) >= 2:
                    clave = fila[0].strip().lower()
                    valor = fila[1].strip()
                    
                    # Si la clave existe en nuestro diccionario, la actualizamos
                    if clave in datos:
                        datos[clave] = valor
                        
        logger.info(f"✅ Configuración cargada: {datos.get('nombre_negocio')}")
        return datos
        
    except Exception as e:
        logger.error(f"❌ Error al leer CONFIGURACIÓN: {e}")
        return datos # Devolvemos los valores por defecto si falla
