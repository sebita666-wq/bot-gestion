from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Definir los IDs de las planillas
SPREADSHEETS = {
    "CLIENTES": "1brdihjFnZAvNPgeoG834eDbeD5nn8sp3uEDEpTdcty0",
    "PEDIDOS": "1_FcX0Qo8c2TzoSSMvmSUotOwwXaiQ-aWTA1zgn6BG1Y",
    "ASESORES": "1wD5__81o_yiWnKVDqwiIocgadP_yftptXwBOF4JGIac",
    "CONSULTAS": "1i-GwLHSz0XWUmdAtCALR3dkCYgZk150kJ4ktXdlBW8k",
    "CONFIGURACIÓN": "162T2djwXdJ_vogyPAmZ3RkBPHDpC-G5iIOD4NtpyxsE"
}

KEY_FILE = 'bot-gestion-499113-32c7b57fd893.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def probar_planilla(nombre, spreadsheet_id):
    print(f"\n🔍 Probando planilla: {nombre}")
    print(f"   ID: {spreadsheet_id}")

    try:
        creds = service_account.Credentials.from_service_account_file(KEY_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)

        # Leer datos (columna A, primeras 5 filas)
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='A:A'
        ).execute()
        values = result.get('values', [])

        print(f"   ✅ Lectura exitosa. {len(values)} filas encontradas.")

        # Probar escritura: agregar una fila de prueba
        test_row = [
            ['TEST', 'Escritura OK', 'Prueba', 'Sistema', 'Funciona']
        ]
        body = {'values': test_row}
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range='A:A',
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()

        print("   ✅ Escritura exitosa. Se agregó una fila de prueba.")

    except HttpError as err:
        print(f"   ❌ Error: {err}")
        if err.resp.status == 403:
            print("   ⚠️ La Service Account no tiene permisos de escritura en esta planilla.")
        elif err.resp.status == 404:
            print("   ⚠️ El ID de la planilla es incorrecto o no existe.")
    except Exception as e:
        print(f"   ❌ Error inesperado: {e}")

if __name__ == '__main__':
    print("🚀 Iniciando pruebas de conexión con Google Sheets...")
    print(f"📁 Archivo de clave: {KEY_FILE}\n")

    for nombre, sid in SPREADSHEETS.items():
        probar_planilla(nombre, sid)

    print("\n✅ Pruebas completadas.")
    print("👉 Revisá las planillas en Google Drive para confirmar que aparezca la fila de prueba.")
