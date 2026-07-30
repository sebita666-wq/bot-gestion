# utils/config.py
# Configuración global del sistema

import os
import json
from google.oauth2 import service_account

# IDs de las planillas de Google Sheets
SPREADSHEETS = {
    "CLIENTES": "1brdihjFnZAvNPgeoG834eDbeD5nn8sp3uEDEpTdcty0",
    "PEDIDOS": "1_FcX0Qo8c2TzoSSMvmSUotOwwXaiQ-aWTA1zgn6BG1Y",
    "ASESORES": "1wD5__81o_yiWnKVDqwiIocgadP_yftptXwBOF4JGIac",
    "CONSULTAS": "1i-GwLHSz0XWUmdAtCALR3dkCYgZk150kJ4ktXdlBW8k",
    "CONFIGURACIÓN": "162T2djwXdJ_vogyPAmZ3RkBPHDpC-G5iIOD4NtpyxsE"
}

# === CREDENCIALES DE GOOGLE (desde variable de entorno) ===
def get_google_credentials():
    """
    Obtiene las credenciales de Google desde la variable de entorno GOOGLE_CREDENTIALS.
    Si no existe, intenta cargar desde el archivo JSON local (para desarrollo).
    """
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if creds_json:
        try:
            # Convertir el string JSON a un diccionario
            creds_info = json.loads(creds_json)
            # Crear credenciales desde el diccionario
            return service_account.Credentials.from_service_account_info(
                creds_info, scopes=SCOPES
            )
        except Exception as e:
            print(f"❌ Error al cargar credenciales desde variable de entorno: {e}")
    
    # Fallback para desarrollo local (si la variable no está definida)
    try:
        return service_account.Credentials.from_service_account_file(
            'bot-gestion-499113-32c7b57fd893.json', scopes=SCOPES
        )
    except Exception as e:
        print(f"❌ Error al cargar credenciales desde archivo: {e}")
        return None

# Credenciales globales (se cargan al iniciar)
CREDENTIALS = get_google_credentials()

# Alcances (scopes) necesarios para Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Número del dueño (para notificaciones)
NUMERO_DUENIO = "whatsapp:+5493434727811"
