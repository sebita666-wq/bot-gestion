def crear_consulta(sender, telefono_cliente, mensaje):
    """Crea una nueva consulta de cliente. Asigna un código C-XXXX y lo guarda en CONSULTAS."""
    print(f"   🔍 [crear_consulta] Iniciando para {telefono_cliente}")
    print(f"   🔍 [crear_consulta] Mensaje: {mensaje[:50]}...")
    
    # 1. Generar código
    codigo = generar_codigo_consulta()
    print(f"   ✅ [crear_consulta] Código generado: {codigo}")
    
    # 2. Preparar datos
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nueva_consulta = [[
        codigo,
        fecha,
        telefono_cliente,
        mensaje,
        "Pendiente",
        ""  # Respuesta del asesor
    ]]
    print(f"   📝 [crear_consulta] Datos a guardar: {nueva_consulta}")
    
    # 3. Intentar escribir en la planilla
    print(f"   📤 [crear_consulta] Escribiendo en CONSULTAS (ID: {config.SPREADSHEETS['CONSULTAS']})...")
    try:
        resultado = planillas.escribir_datos(config.SPREADSHEETS["CONSULTAS"], 'A:F', nueva_consulta)
        print(f"   📥 [crear_consulta] Resultado de escritura: {resultado}")
        if resultado:
            return {"codigo": codigo, "estado": "Pendiente"}
        else:
            print(f"   ❌ [crear_consulta] planillas.escribir_datos devolvió False")
            return None
    except Exception as e:
        print(f"   ❌ [crear_consulta] EXCEPCIÓN: {e}")
        import traceback
        traceback.print_exc()
        return None

def procesar_consulta(sender, mensaje):
    """Procesa la consulta de un cliente que está en el flujo de asesor."""
    print(f"   📞 [procesar_consulta] Iniciando para {sender}")
    print(f"   📞 [procesar_consulta] Mensaje: {mensaje[:50]}...")
    
    consulta = crear_consulta(sender, sender, mensaje)
    print(f"   📞 [procesar_consulta] consulta creada: {consulta}")
    
    if consulta:
        print(f"   📞 [procesar_consulta] Notificando al asesor...")
        notificar_asesor(consulta["codigo"], sender, mensaje)
        return f"""
✅ *Consulta enviada*

Tu consulta fue registrada con el código *{consulta['codigo']}*.

Un asesor te va a responder por este mismo chat en breve.

😊 Gracias por tu paciencia.
"""
    else:
        print(f"   ❌ [procesar_consulta] consulta es None, error al guardar")
        return """
❌ *Error al enviar tu consulta*

Hubo un problema al registrar tu consulta. Por favor, intentá de nuevo más tarde.

😊 Disculpá las molestias.
"""
