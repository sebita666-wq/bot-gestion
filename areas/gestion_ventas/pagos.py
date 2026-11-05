# areas/gestion_ventas/pagos.py
# Opciones de pago: transferencia, efectivo con descuento, cuotas

from utils import planillas
from utils import config
from areas.gestion_ventas import presupuesto
import logging

logger = logging.getLogger(__name__)

# Configuración de pagos (se puede leer desde CONFIGURACIÓN en el futuro)
DESCUENTO_EFECTIVO = 10  # 10% de descuento
INTERES_CUOTA = 0  # 0% de interés

def mostrar_opciones_pago():
    """Devuelve el mensaje con las opciones de pago."""
    return """
💰 *¿Cómo querés pagar?*

1️⃣ Transferencia bancaria
2️⃣ Pago en efectivo (10% de descuento)
3️⃣ Cuotas de la casa (sin interés)

👉 Escribí el número de la opción que desees.
"""

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

👉 Escribí MENU para volver al inicio.

¡Gracias por confiar en Carpintería Radi! 🪑
"""
    return mensaje

def efectivo(pedido):
    """Maneja pago en efectivo con descuento."""
    precio_original = int(pedido['precio']) if pedido['precio'] else 0
    descuento = int(precio_original * DESCUENTO_EFECTIVO / 100)
    precio_final = precio_original - descuento
    
    mensaje = f"""
💰 *Pago en efectivo*

Precio original: ${precio_original}  
🎉 *Descuento por pago en efectivo: {DESCUENTO_EFECTIVO}%*  
💰 *Total a pagar en efectivo: ${precio_final}*

Podés pasar por nuestro taller:  
📍 *Av. San Martín 123, Paraná*  
⏰ *Horario: lunes a viernes de 9 a 18 hs.*

👉 Escribí MENU para volver al inicio.

¡Gracias por confiar en Carpintería Radi! 🪑
"""
    return mensaje

def cuotas(pedido):
    """Maneja pago en cuotas de la casa."""
    precio = int(pedido['precio']) if pedido['precio'] else 0
    
    mensaje = f"""
💰 *Pago en cuotas de la casa*

Precio total: ${precio}

¿En cuántas cuotas querés pagar?  
3️⃣ *3 cuotas*  
6️⃣ *6 cuotas*  
12️⃣ *12 cuotas*

👉 Escribí el número de cuotas que deseas:
"""
    return mensaje

def procesar_cuotas(cantidad, pedido):
    """Calcula el valor de cada cuota y arma el plan de pagos."""
    precio = int(pedido['precio']) if pedido['precio'] else 0
    cantidad = int(cantidad)
    
    # Calcular valor de cuota con interés (0% por ahora)
    total_con_interes = precio * (1 + INTERES_CUOTA / 100)
    valor_cuota = total_con_interes / cantidad
    
    mensaje = f"""
💰 *Plan de pagos ({cantidad} cuotas sin interés)*

• *Valor de cada cuota:* ${int(valor_cuota)}  
• *Total final:* ${int(total_con_interes)}

👉 Escribí MENU para volver al inicio.

¡Gracias por confiar en Carpintería Radi! 🪑
"""
    return mensaje
