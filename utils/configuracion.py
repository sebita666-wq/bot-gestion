# utils/configuracion.py
# Lee los datos de CONFIGURACIÓN con sistema de CACHÉ (memoria temporal)

from utils import planillas
from utils import config
import logging
import time

logger = logging.getLogger(__name__)

# Valores por defecto
CONFIG_DEFAULT = {
    "nombre_negocio": "Carpintería Radi",
    "telefono_duenio": config.NUMERO_DUENIO,
    "email_soporte": "ventas@carpinteriaradi.com",
    "direccion_local": "Av. San Martín 123, Paraná",
    "horario_atencion": "Lunes a viernes de 9 a 18hs",
    "descuento_efectivo": "10",
    "interes_cuota": "0",
    "timeout_asesor_minutos": "5",
    "banco_transferencia": "Banco Nación",
    "cbu_transferencia": "1234567890123456789012",
    "alias_transferencia": "CARPINTERIA.RADI",
    "titular_cuenta": "Diego Pérez",
    "web_negocio": "www.carpinteriaradi.com.ar",
    "cuotas_disponibles": "3,6,12",
    "mensaje_bienvenida": "¡Hola! Bienvenido a Carpintería Radi"
}

# Variables para el caché
_cache_datos = None
_cache_tiempo = 0
CACHE_DURACION = 300  # 5 minutos (en segundos)

def obtener_configuracion():
    """Lee la planilla CONFIGURACIÓN y devuelve un diccionario. Usa caché de 5 min."""
    global _cache_datos, _cache_tiempo
    
    # Si tenemos datos en caché y no pasaron 5 minutos, los devolvemos
    if _cache_datos and (time.time() - _cache_tiempo) < CACHE_DURACION:
        return _cache_datos.copy()
    
    # Si no hay caché, leemos la planilla
    datos = CONFIG_DEFAULT.copy()
    try:
        filas = planillas.leer_datos(config.SPREADSHEETS["CONFIGURACIÓN"], 'A:B')
        
        if filas and len(filas) > 1:
            for fila in filas[1:]:
                if len(fila) >= 2:
                    clave = fila[0].strip().lower()
                    valor = fila[1].strip()
                    if clave in datos:
                        datos[clave] = valor
                        
        # Guardamos en caché
        _cache_datos = datos
        _cache_tiempo = time.time()
        logger.info(f"✅ Configuración cargada desde Sheets y cacheada.")
        return datos
        
    except Exception as e:
        logger.error(f"❌ Error al leer CONFIGURACIÓN: {e}")
        return datos
