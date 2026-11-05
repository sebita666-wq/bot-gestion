# areas/gestion_ventas/pagos.py

def mostrar_opciones_pago():
    return """
💰 *¿Cómo querés pagar?*

1️⃣ Transferencia bancaria
2️⃣ Pago en efectivo (10% de descuento)
3️⃣ Cuotas de la casa (sin interés)

👉 Escribí el número de la opción que desees.
"""

def transferencia(pedido, conf):
    banco = conf.get('banco_transferencia', 'Banco Nación')
    cbu = conf.get('cbu_transferencia', '1234567890123456789012')
    alias = conf.get('alias_transferencia', 'CARPINTERIA.RADI')
    nombre = conf.get('nombre_negocio', 'Nuestro Negocio')
    
    return f"""
💰 *Transferencia bancaria*

🏦 *{banco}*  
📌 *CBU:* {cbu}  
📌 *Alias:* {alias}  
📌 *Monto:* ${pedido['precio']}  

Una vez que hagas la transferencia, enviá el comprobante por este chat.

👉 Escribí MENU para volver al inicio.

¡Gracias por confiar en {nombre}! ✨
"""

def efectivo(pedido, conf):
    descuento_porc = int(conf.get('descuento_efectivo', 10))
    precio_original = int(pedido['precio']) if pedido['precio'] else 0
    descuento = int(precio_original * descuento_porc / 100)
    precio_final = precio_original - descuento
    
    direccion = conf.get('direccion_local', 'Nuestro taller')
    horario = conf.get('horario_atencion', 'Horario de atención')
    nombre = conf.get('nombre_negocio', 'Nuestro Negocio')
    
    return f"""
💰 *Pago en efectivo*

Precio original: ${precio_original}  
🎉 *Descuento: {descuento_porc}%*  
💰 *Total: ${precio_final}*

📍 *{direccion}*  
⏰ *{horario}*

👉 Escribí MENU para volver al inicio.

¡Gracias por confiar en {nombre}! ✨
"""

def cuotas(pedido, conf):
    """Muestra el menú inicial para elegir cuotas."""
    precio = int(pedido['precio']) if pedido['precio'] else 0
    cuotas_disp = conf.get('cuotas_disponibles', '3,6,12')
    
    return f"""
💳 *Cuotas de la casa*

Precio total: ${precio}

¿En cuántas cuotas querés pagar?  
👉 Opciones disponibles: *{cuotas_disp}*

Escribí el número de cuotas que deseas:
"""

def procesar_cuotas(cantidad, pedido, conf):
    """Calcula el valor de la cuota y arma el mensaje final."""
    precio = int(pedido['precio']) if pedido['precio'] else 0
    interes = int(conf.get('interes_cuota', 0))
    cantidad = int(cantidad)
    
    total_con_interes = precio * (1 + interes / 100)
    valor_cuota = total_con_interes / cantidad
    texto_interes = f"con {interes}% de interés" if interes > 0 else "sin interés"
    nombre = conf.get('nombre_negocio', 'Nuestro Negocio')
    
    return f"""
✅ *Plan de pagos confirmado*

💳 *{cantidad} cuotas {texto_interes}*

• *Valor de cada cuota:* ${int(valor_cuota)}  
• *Total final:* ${int(total_con_interes)}

📌 Un asesor de {nombre} se contactará para coordinar el pago.

👉 Escribí MENU para volver al inicio.

¡Gracias por confiar en {nombre}! ✨
"""
