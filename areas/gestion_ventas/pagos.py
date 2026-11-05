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
    precio = int(pedido['precio']) if pedido['precio'] else 0
    interes = int(conf.get('interes_cuota', 0))
    texto_interes = f"con {interes}% de interés" if interes > 0 else "sin interés"
    nombre = conf.get('nombre_negocio', 'Nuestro Negocio')
    
    return f"""
💳 *Cuotas de la casa*

Precio total: ${precio}
({texto_interes})

¿En cuántas cuotas querés pagar?  
3️⃣ *3 cuotas*  
6️⃣ *6 cuotas*  
12️⃣ *12 cuotas*

👉 Escribí el número de cuotas que deseas:
"""
