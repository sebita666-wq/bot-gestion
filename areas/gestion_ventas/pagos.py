# areas/gestion_ventas/pagos.py
# Opciones de pago: transferencia, efectivo, cuotas

from utils import planillas
from utils import config
from areas.gestion_ventas import presupuesto

# Configuración de pagos (se puede leer desde CONFIGURACIÓN en el futuro)
DESCUENTO_EFECTIVO = 10  # 10% de descuento
INTERES_CUOTA = 0  # 0% de interés

def mostrar_opciones_pago():
    """Devuelve el mensaje con las opciones de pago."""
    return """
💰 ¿Cómo querés pagar?

1️⃣ Transferencia bancaria
2️⃣ Pago en efectivo (con descuento)
3️⃣ Cuotas de la casa (sin interés)

➡️ Elegí una opción para continuar.
"""

def procesar_opcion_pago(opcion, numero_presupuesto):
    """
    Procesa la opción de pago elegida por el cliente.
    opcion: "1", "2" o "3"
    """
    pedido = presupuesto.obtener_presupuesto(numero_presupuesto)
    if not pedido:
        return {"error": "Presupuesto no encontrado"}
    
    if opcion == "1":
        return transferencia(pedido)
    elif opcion == "2":
        return efectivo(pedido)
    elif opcion == "3":
        return cuotas(pedido)
    else:
        return {"error": "Opción no válida"}

def transferencia(pedido):
    """Maneja pago por transferencia bancaria."""
    mensaje = f"""
💰 *Transferencia bancaria*

Datos para transferir:  
🏦 *Banco Nación*  
📌 *CBU:* 1234567890123456789012  
📌 *Alias:* CARPINTERIA.RADI  
📌 *Monto:* ${pedido['precio']}  

Una vez que hagas la transferencia, enviá el comprobante por este chat.

➡️ Podés escribir *"Listo"* o adjuntar la foto del comprobante.
"""
    return {
        "tipo": "transferencia",
        "mensaje": mensaje,
        "estado": "Pendiente comprobante"
    }

def efectivo(pedido):
    """Maneja pago en efectivo con descuento."""
    precio_original = int(pedido['precio']) if pedido['precio'] else 0
    descuento = int(precio_original * DESCUENTO_EFECTIVO / 100)
    precio_final = precio_original - descuento
    
    mensaje = f"""
💰 *Pago en efectivo*

Precio original: *${precio_original}*  
🎉 *Descuento por pago en efectivo: {DESCUENTO_EFECTIVO}%*  
💰 *Total a pagar en efectivo: ${precio_final}*

Podés pasar por nuestro taller:  
📍 *Av. San Martín 123, Paraná*  
⏰ *Horario: lunes a viernes de 9 a 18 hs.*

¿Confirmás el pago en efectivo? (sí / no)
"""
    return {
        "tipo": "efectivo",
        "mensaje": mensaje,
        "precio_final": precio_final,
        "estado": "Pendiente confirmación"
    }

def cuotas(pedido):
    """Maneja pago en cuotas de la casa."""
    precio = int(pedido['precio']) if pedido['precio'] else 0
    
    mensaje = f"""
💰 *Pago en cuotas de la casa*

¿En cuántas cuotas querés pagar?  
3️⃣ *3 cuotas*  
6️⃣ *6 cuotas*  
12️⃣ *12 cuotas*
"""
    return {
        "tipo": "cuotas",
        "mensaje": mensaje,
        "precio": precio,
        "estado": "Pendiente cuotas"
    }

def procesar_cuotas(cantidad, pedido):
    """
    Procesa la cantidad de cuotas elegida por el cliente.
    Calcula el valor de cada cuota y el plan de pagos.
    """
    precio = int(pedido['precio']) if pedido['precio'] else 0
    interes = INTERES_CUOTA
    cantidad = int(cantidad)
    
    # Calcular valor de cuota con interés
    total_con_interes = precio * (1 + interes / 100)
    valor_cuota = total_con_interes / cantidad
    
    # Si es 0% de interés, se muestra sin interés
    if interes == 0:
        total_con_interes = precio
        valor_cuota = precio / cantidad
    
    entrega_inicial = valor_cuota
    
    mensaje = f"""
💰 *Plan de pagos ({cantidad} cuotas {'' if interes == 0 else f'con {interes}% de interés'} )*

• *Entrega inicial:* ${int(entrega_inicial)}  
• *{cantidad} cuotas de:* ${int(valor_cuota)}  
• *Total final:* ${int(total_con_interes)}

📅 *Primera cuota vence:* 30/06/2026  
📅 *Segunda cuota vence:* 30/07/2026  
📅 *Tercera cuota vence:* 30/08/2026

¿Confirmás este plan de pagos? (sí / no)
"""
    return {
        "tipo": "cuotas",
        "mensaje": mensaje,
        "cantidad": cantidad,
        "valor_cuota": int(valor_cuota),
        "total": int(total_con_interes),
        "estado": "Pendiente confirmación"
    }
