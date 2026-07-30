# utils/planillas.py
# Funciones para leer y escribir en Google Sheets

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from . import config
import logging
import time

logger = logging.getLogger(__name__)

def obtener_conexion():
    """Devuelve el objeto de conexión a la API de Google Sheets usando CREDENTIALS globales."""
    if not config.CREDENTIALS:
        logger.error("❌ No hay credenciales disponibles")
        return None
    
    try:
        return build('sheets', 'v4', credentials=config.CREDENTIALS)
    except Exception as e:
        logger.error(f"❌ Error al crear conexión: {e}")
        return None

def leer_datos(spreadsheet_id, rango, max_retries=3):
    """
    Lee datos de una planilla con reintentos.
    """
    for intento in range(max_retries):
        try:
            service = obtener_conexion()
            if not service:
                raise Exception("No se pudo obtener conexión")
            
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=rango
            ).execute()
            
            valores = result.get('values', [])
            logger.info(f"✅ Lectura exitosa: {len(valores)} filas en {rango}")
            return valores
            
        except HttpError as e:
            logger.warning(f"⚠️ Intento {intento+1}/{max_retries} falló: {e}")
            if intento < max_retries - 1:
                time.sleep(2 ** intento)
            else:
                logger.error(f"❌ Error al leer después de {max_retries} intentos: {e}")
                return None
        except Exception as e:
            logger.error(f"❌ Error inesperado: {e}")
            return None

def escribir_datos(spreadsheet_id, rango, datos, max_retries=3):
    """
    Escribe datos en una planilla con reintentos.
    """
    for intento in range(max_retries):
        try:
            service = obtener_conexion()
            if not service:
                raise Exception("No se pudo obtener conexión")
            
            body = {'values': datos}
            result = service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=rango,
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            logger.info(f"✅ Escritura exitosa: {len(datos)} filas en {rango}")
            return True
            
        except HttpError as e:
            logger.warning(f"⚠️ Intento {intento+1}/{max_retries} falló: {e}")
            if intento < max_retries - 1:
                time.sleep(2 ** intento)
            else:
                logger.error(f"❌ Error al escribir después de {max_retries} intentos: {e}")
                return False
        except Exception as e:
            logger.error(f"❌ Error inesperado: {e}")
            return False

def actualizar_celda(spreadsheet_id, rango, valor, max_retries=3):
    """
    Actualiza una celda específica con reintentos.
    """
    for intento in range(max_retries):
        try:
            service = obtener_conexion()
            if not service:
                raise Exception("No se pudo obtener conexión")
            
            body = {'values': [[valor]]}
            result = service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=rango,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            logger.info(f"✅ Celda {rango} actualizada: {valor}")
            return True
            
        except HttpError as e:
            logger.warning(f"⚠️ Intento {intento+1}/{max_retries} falló: {e}")
            if intento < max_retries - 1:
                time.sleep(2 ** intento)
            else:
                logger.error(f"❌ Error al actualizar celda después de {max_retries} intentos: {e}")
                return False
        except Exception as e:
            logger.error(f"❌ Error inesperado: {e}")
            return False
