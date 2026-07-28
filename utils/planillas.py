# utils/planillas.py
# Funciones para leer y escribir en Google Sheets

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from . import config

def obtener_conexion():
    """Devuelve el objeto de conexión a la API de Google Sheets"""
    try:
        creds = service_account.Credentials.from_service_account_file(
            config.KEY_FILE, scopes=config.SCOPES
        )
        return build('sheets', 'v4', credentials=creds)
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return None

def leer_datos(spreadsheet_id, rango):
    """Lee datos de una planilla"""
    service = obtener_conexion()
    if not service:
        return None
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=rango
        ).execute()
        return result.get('values', [])
    except HttpError as e:
        print(f"❌ Error al leer: {e}")
        return None

def escribir_datos(spreadsheet_id, rango, datos):
    """Escribe datos en una planilla"""
    service = obtener_conexion()
    if not service:
        return False
    try:
        body = {'values': datos}
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=rango,
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        return True
    except HttpError as e:
        print(f"❌ Error al escribir: {e}")
        return False
