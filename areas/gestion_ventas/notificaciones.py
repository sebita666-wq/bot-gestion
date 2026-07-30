# areas/gestion_ventas/notificaciones.py
# Sistema de notificaciones REAL con Twilio

from utils import config
import os
import logging
from twilio.rest import Client

logger = logging.getLogger(__name__)

def enviar_whatsapp(destino, mensaje):
    """
    Envía un mensaje de WhatsApp REAL usando Twilio.
    """
    try:
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        from_number = os.environ.get('TWILIO_WHATSAPP_NUMBER')
        
        if not account_sid or not auth_token or not from_number:
            logger.error("❌ Faltan variables de entorno de Twilio")
            return False
        
        # Asegurar formato del número
        if not destino.startswith('+'):
            destino = '+' + destino
        if not destino.startswith('whatsapp:'):
            destino = f'whatsapp:{destino}'
        
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            from_=f'whatsapp:{from_number}',
            body=mensaje,
            to=destino
        )
        logger.info(f"✅ Mensaje enviado a {destino}. SID: {message.sid}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error al enviar mensaje: {e}")
        return False

def notificar_nuevo_presupuesto(numero_presupuesto, datos_cliente, producto, personalizacion, es_modificacion=False):
    """
    Envía una notificación al dueño cuando se crea un nuevo presupuesto o modificación.
    """
    tipo = "MODIFICACIÓN" if es_modificacion else "NUEVO PRESUPUESTO"
    emoji = "✏️" if es_modificacion else "📋"
    
    mensaje = f"""
{emoji} *{tipo}*

Código: {numero_presupuesto}
Cliente: {datos_cliente['nombre']} ({datos_cliente['telefono']}) - 👤 Cliente {'recurrente' if datos_cliente.get('recurrente') else 'nuevo'}
Producto: {producto}
Personalización: {personalizacion}
Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}

👉 Para responder, escribí:
{numero_presupuesto.replace('-', '')} (tu mensaje o presupuesto)

Ejemplo: {numero_presupuesto.replace('-', '')} El presupuesto es de $150.000
"""
    from datetime import datetime
    return enviar_whatsapp(config.NUMERO_DUENIO, mensaje)

def notificar_respuesta_dueño(numero_presupuesto, mensaje_respuesta):
    """
    Confirma al dueño que su respuesta fue enviada al cliente.
    """
    mensaje = f"""
✅ *Respuesta enviada*

Tu respuesta para el presupuesto {numero_presupuesto} fue enviada exitosamente al cliente.

📩 El cliente recibirá tu mensaje en su chat de WhatsApp.
"""
    return enviar_whatsapp(config.NUMERO_DUENIO, mensaje)

def notificar_error_respuesta(numero):
    """
    Notifica al dueño que no encontró el presupuesto.
    """
    mensaje = f"""
❌ *Error al enviar*

No se encontró el presupuesto con el código que ingresaste.

Verificá que el código sea correcto y volvé a intentar.

Ejemplo correcto: {numero.replace('-', '')} (tu mensaje)
"""
    return enviar_whatsapp(config.NUMERO_DUENIO, mensaje)

def notificar_presupuesto_cliente(numero_presupuesto, datos_presupuesto, mensaje_dueño, es_modificacion=False):
    """
    Envía el presupuesto al cliente con las opciones de acción.
    """
    modificacion_texto = " (Modificado)" if es_modificacion else ""
    
    mensaje = f"""
📞 *El asesor te responde:*
{mensaje_dueño}

📋 *Presupuesto {numero_presupuesto}{modificacion_texto}*

Producto: {datos_presupuesto['producto']}
Personalización: {datos_presupuesto['personalizacion']}
💰 Precio: {datos_presupuesto['precio']}

📌 ¿Qué querés hacer?

1️⃣ Aceptar el presupuesto
2️⃣ Rechazar el presupuesto
3️⃣ Solicitar modificaciones
4️⃣ Hablar con un asesor

👉 Escribí el número de la opción que desees.
"""
    return enviar_whatsapp(datos_presupuesto['telefono'], mensaje)

def notificar_aceptacion_cliente(numero_presupuesto, datos_cliente, datos_presupuesto):
    """
    Notifica al dueño que el cliente aceptó el presupuesto.
    """
    mensaje = f"""
✅ *Presupuesto aceptado*

Cliente: {datos_cliente['nombre']} ({datos_cliente['telefono']})
Presupuesto: {numero_presupuesto}
Producto: {datos_presupuesto['producto']}
Precio: ${datos_presupuesto['precio']}

👉 El cliente aceptó el presupuesto. Esperá que elija la forma de pago.
"""
    return enviar_whatsapp(config.NUMERO_DUENIO, mensaje)

def notificar_rechazo_cliente(numero_presupuesto, datos_cliente, datos_presupuesto):
    """
    Notifica al dueño que el cliente rechazó el presupuesto.
    """
    mensaje = f"""
❌ *Presupuesto rechazado*

Cliente: {datos_cliente['nombre']} ({datos_cliente['telefono']})
Presupuesto: {numero_presupuesto}
Precio ofrecido: ${datos_presupuesto['precio']}

👉 El cliente rechazó el presupuesto. Esperá su decisión o contactalo para negociar.
"""
    return enviar_whatsapp(config.NUMERO_DUENIO, mensaje)

def notificar_modificacion_cliente(numero_presupuesto, datos_cliente, datos_presupuesto, texto_modificacion):
    """
    Notifica al dueño que el cliente solicitó modificaciones.
    """
    mensaje = f"""
✏️ *Solicitud de modificaciones*

Cliente: {datos_cliente['nombre']} ({datos_cliente['telefono']})
Presupuesto: {numero_presupuesto}
Producto: {datos_presupuesto['producto']}
Precio original: ${datos_presupuesto['precio']}

Cambios solicitados:
"{texto_modificacion}"

👉 Para responder, escribí:
{numero_presupuesto.replace('-', '')} (tu respuesta)

Ejemplo: {numero_presupuesto.replace('-', '')} Podemos hacerlo por $130.000
"""
    return enviar_whatsapp(config.NUMERO_DUENIO, mensaje)

def notificar_forma_pago(numero_presupuesto, datos_cliente, datos_presupuesto, forma_pago):
    """
    Notifica al dueño la forma de pago elegida por el cliente.
    """
    mensaje = f"""
💰 *Forma de pago seleccionada*

Cliente: {datos_cliente['nombre']} ({datos_cliente['telefono']})
Presupuesto: {numero_presupuesto}
Producto: {datos_presupuesto['producto']}
Precio: ${datos_presupuesto['precio']}
Forma de pago: {forma_pago}

👉 El cliente ya eligió cómo pagar. Coordiná la producción y pago.
"""
    return enviar_whatsapp(config.NUMERO_DUENIO, mensaje)
