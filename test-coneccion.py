from google.oauth2 import service_account
from googleapiclient.discovery import build

# ID de tu planilla CLIENTES (reemplazá con el tuyo)
SPREADSHEET_ID = '1brdihjFnZAvNPgeoG834eDbeD5nn8sp3uEDEpTdcty0'

# Ruta al archivo JSON (debe estar en la misma carpeta)
KEY_FILE = 'bot-gestion-499113-32c7b57fd893.json'

def test_sheets():
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        creds = service_account.Credentials.from_service_account_file(KEY_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)

        # Leer datos de la columna A
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='A:A'
        ).execute()

        values = result.get('values', [])
        print(f"✅ Conexión exitosa. Se encontraron {len(values)} filas con datos.")
        print("📋 Datos (primeras 10 filas):", values[:10])

    except Exception as e:
        print(f"❌ Error: {e}")
        print("⚠️ Verificá que:")
        print("   - El archivo JSON existe en la misma carpeta.")
        print("   - El SPREADSHEET_ID es correcto.")
        print("   - La Service Account tiene permisos de editor en la planilla.")

if __name__ == '__main__':
    test_sheets()
