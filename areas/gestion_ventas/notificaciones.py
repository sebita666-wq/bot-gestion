# areas/gestion_ventas/notificaciones.py
# Sistema de notificaciones para el dueño y el cliente

from utils import config
from areas.gestion_ventas import presupuesto
from areas.gestion_ventas import clientes

# Simulación de envío de WhatsApp (en la práctica, usarías Twilio)
def enviar_whatsapp(destino, mensaje):
    """
    Envía un mensaje de WhatsApp.
    En producción, esto se reemplazaría con la API de Twilio.
    """
    print(f"📱 Enviando a {destino}:")
    print(mensaje)
    print("-" * 50)
    return True

def notificar_nuevo_presupuesto(numero_presupuesto, datos_cliente, producto, personalizacion):
    """
    Envía una notificación al dueño cuando se crea un nuevo presupuesto.
    """
    mensaje = f"""
🌞 Buenos días, Diego.

Tienes una *nueva solicitud de presupuesto*:

📋 *Presupuesto {numero_presupuesto}*
👤 Cliente: {datos_cliente['nombre']}
📞 Teléfono: {datos_cliente['telefono']}
📦 Producto: {producto}
🎨 Personalización: {personalizacion}

---
*¿Deseas modificar algo?*

Podés escribir en un solo mensaje:

🔹 *Con palabras:*  
`Precio 150000`, `Producto Silla de pino`, `Personalización 50 cm`, `Aclaración: texto`

🔹 *Con números:*  
`1 150000`, `2 Silla de pino`, `3 50 cm`, `4 texto`

✅ *Para terminar, escribí:* **LISTO**
"""
    return enviar_whatsapp(config.NUMERO_DUENIO, mensaje)

def procesar_respuesta_dueño(respuesta):
    """
    Procesa la respuesta del dueño al presupuesto.
    Extrae precio, producto modificado, personalización y aclaración.
    """
    # Dividir por líneas o por comas (si es un mensaje largo)
    lineas = respuesta.split('\n') if '\n' in respuesta else respuesta.split(',')
    
    resultado = {
        "precio": None,
        "producto_modificado": None,
        "personalizacion_modificada": None,
        "aclaracion": None,
        "enviar": False
    }
    
    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue
        
        # Detectar por palabras clave
        if linea.lower().startswith("precio") or linea.startswith("1"):
            partes = linea.split(maxsplit=1)
            if len(partes) > 1:
                resultado["precio"] = partes[1].strip()
        
        elif linea.lower().startswith("producto") or linea.startswith("2"):
            partes = linea.split(maxsplit=1)
            if len(partes) > 1:
                resultado["producto_modificado"] = partes[1].strip()
        
        elif linea.lower().startswith("personalizacion") or linea.startswith("3"):
            partes = linea.split(maxsplit=1)
            if len(partes) > 1:
                resultado["personalizacion_modificada"] = partes[1].strip()
        
        elif linea.lower().startswith("aclaracion") or linea.startswith("4"):
            partes = linea.split(maxsplit=1)
            if len(partes) > 1:
                resultado["aclaracion"] = partes[1].strip()
        
        elif linea.strip().upper() == "LISTO":
            resultado["enviar"] = True
    
    return resultado

def notificar_cliente(numero_presupuesto, datos_presupuesto):
    """
    Envía una notificación al cliente cuando el presupuesto está listo.
    """
    mensaje = f"""
🌞 Buenos días, {datos_presupuesto['nombre']}.

Tu presupuesto *{numero_presupuesto}* fue revisado por nuestro equipo.

📋 *Resumen del presupuesto:*

📦 Producto solicitado: {datos_presupuesto['producto_original']}  
👉 *Producto final: {datos_presupuesto['producto_final']}*

🎨 Personalización solicitada: {datos_presupuesto['personalizacion_original']}  
👉 *Personalización final: {datos_presupuesto['personalizacion_final']}*

💰 *Precio final: ${datos_presupuesto['precio']}*

📝 *Aclaración del equipo:*  
"{datos_presupuesto['aclaracion']}"

👉 ¿Aceptás este presupuesto?

1️⃣ Sí, lo acepto
2️⃣ No, lo rechazo
3️⃣ Necesito hablar con la empresa
"""
    return enviar_whatsapp(datos_presupuesto['telefono'], mensaje)

def notificar_pedido_confirmado(numero_presupuesto, datos_pedido):
    """
    Notifica al dueño que el cliente confirmó el pedido.
    """
    mensaje = f"""
✅ *Pedido confirmado*

Cliente: {datos_pedido['nombre']}
Pedido: {numero_presupuesto}
Producto: {datos_pedido['producto']}
Precio: ${datos_pedido['precio']}
Forma de pago: {datos_pedido['forma_pago']}

Estado: Confirmado - Pendiente producción
"""
    return enviar_whatsapp(config.NUMERO_DUENIO, mensaje)
