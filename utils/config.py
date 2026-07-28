# utils/config.py
# Configuración global del sistema

# IDs de las planillas de Google Sheets
SPREADSHEETS = {
    "CLIENTES": "1brdihjFnZAvNPgeoG834eDbeD5nn8sp3uEDEpTdcty0",
    "PEDIDOS": "1_FcX0Qo8c2TzoSSMvmSUotOwwXaiQ-aWTA1zgn6BG1Y",
    "ASESORES": "1wD5__81o_yiWnKVDqwiIocgadP_yftptXwBOF4JGIac",
    "CONSULTAS": "1i-GwLHSz0XWUmdAtCALR3dkCYgZk150kJ4ktXdlBW8k",
    "CONFIGURACIÓN": "162T2djwXdJ_vogyPAmZ3RkBPHDpC-G5iIOD4NtpyxsE"
}

# Archivo de autenticación de Google (Service Account)
KEY_FILE = 'bot-gestion-499113-32c7b57fd893.json'

# Alcances (scopes) necesarios para Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Número del dueño (para notificaciones) - CAMBIAR POR EL REAL
NUMERO_DUENIO = "whatsapp:+5493434727811"
