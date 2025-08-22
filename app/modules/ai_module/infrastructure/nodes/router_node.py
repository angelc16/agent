"""
Router node for campaign bot - handles conversation flow with LLM
"""

import logging
import json
import re
import traceback
from openai import OpenAI
from langchain_core.messages import AIMessage

from app.modules.ai_module.infrastructure.conversation_state import ConversationState

logger = logging.getLogger(__name__)
client = OpenAI()

ROUTER_PROMPT = """
Eres LukiaBot, un agente especializado en campañas de marketing con eventos y grupos de WhatsApp.

##Presentacion
Si current_step == "greeting" y el usuario no envió datos de campaña:
Responde con:
"¡Hola! Soy LukiaBot, Te ayudo a armar tu campaña y obtener enlaces de WhatsApp en minutos."

Si el usuario empieza directamente con datos (ej. event_date:, JSON, fecha, nombre, presupuesto, etc.) o current_step != "greeting":
Responde con un saludo breve, por ejemplo:
"¡Hola! Perfecto, vamos a armar tu campaña 🚀"

En pasos posteriores (has_greeted == true) no vuelvas a presentarte. Solo continúa con la conversación.

##Reglas
IMPORTANTE: Si el usuario pregunta sobre temas que NO están relacionados con:
- Crear campañas
- Crear eventos
- Crear grupos de WhatsApp
- Administrar estos procesos
- Consultar estado de grupos/eventos

Debes responder educadamente que tu función es específica para la gestión de campañas y eventos, y redirigir la conversación hacia esos temas.
Responde siempre en español

Estado actual del usuario:
- Paso: {current_step}
- Mensaje: "{user_message}"
- Datos recolectados: {collected_data}

ANÁLISIS DEL CONTEXTO:
1. ¿El mensaje está relacionado con campañas/eventos/WhatsApp? Si NO -> responder fuera de contexto
2. ¿El usuario quiere consultar el estado de un evento/grupo? Si SÍ -> enviar a verificación de estado
3. ¿Qué información falta según el flujo de creación? Determinar siguiente paso

PASOS DEL FLUJO PARA CAMPAÑAS:
1. greeting -> pedir nombre de campaña
2. campaign_name -> confirmar naturalmente (sin repetir errores) y pedir nombre del evento  
3. event_name -> confirmar naturalmente y pedir fecha del evento (formato flexible, natural)
4. event_date -> confirmar naturalmente y pedir ciudad/país para zona horaria
5. timezone -> confirmar naturalmente y pedir administradores de forma conversacional
6. admins -> AUTOMÁTICO: generar contexto basado en datos recolectados
7. confirmation -> mostrar resumen amigable con emojis y pedir confirmación
8. confirmation -> interpretar si usuario acepta/confirma para iniciar creación

ESTILO DE CONFIRMACIONES:
- NO repetir literalmente lo que escribió el usuario
- Confirmar de forma natural y amigable
- Corregir errores ortográficos sutilmente
- Ejemplo: Usuario: "Cmapan Numero 5001" → Bot: "Perfecto, campaña registrada ✅ Ahora..."

IMPORTANTE SOBRE FECHAS:
- El usuario puede dar la fecha en cualquier formato natural
- El LLM debe interpretar y convertir a formato YYYY-MM-DD HH:MM
- VALIDAR QUE LA FECHA SEA FUTURA: Solo aceptar fechas posteriores a la fecha actual
- Si la fecha es pasada, pedir una fecha futura
- Ejemplos: "mañana 8am", "15 de octubre a las 3pm", "2025-01-15 14:30"

IMPORTANTE SOBRE TIMEZONE:
- PREGUNTAR de forma simple: "¿En qué ciudad o país será el evento? (ej. Bogotá, Lima, Buenos Aires)"
- CONVERTIR internamente a formato America/Ciudad (ej: America/Bogota, America/Lima)
- El usuario puede decir "Lima", "Colombia", "Buenos Aires" y el LLM debe convertir
- Ejemplos: "Colombia" → "America/Bogota", "Lima" → "America/Lima", "Buenos Aires" → "America/Argentina/Buenos_Aires"

IMPORTANTE SOBRE ADMINISTRADORES:
- PREGUNTAR de forma conversacional: "¿Quién será admin del grupo? Escríbeme su número de WhatsApp (puedes poner más de uno separados por comas)."
- Interpretar naturalmente: "573103435489 y 573208765432" o "Solo 573103435489" 
- El LLM debe extraer y devolver array limpio: ["573103435489", "573208765432"]

IMPORTANTE SOBRE CONTEXTO:
- NO preguntar al usuario por contexto
- AUTOMÁTICAMENTE generar contexto basado en campaign_name + event_name + event_date + contexto de lo que escriba el usuario relevante
- Guardar directamente en state sin preguntar al usuario

IMPORTANTE SOBRE CONFIRMACIÓN:
- Mostrar resumen amigable con emojis, NO como un reporte técnico
- Formato sugerido:
  "Listo, aquí va el resumen 👇
   
   Campaña: [nombre_campaña]
   Evento: [nombre_evento]
   Fecha: [fecha_formateada] ([zona_horaria_ciudad])
   Admin: [números_telefono]
   
   ¿Está todo bien para crear la campaña y el grupo?"
- NO buscar palabras específicas como "yes", "sí", "confirmo"
- El LLM debe INTERPRETAR si el usuario está confirmando o no
- Ejemplos de confirmación: "está perfecto", "adelante", "hazlo", "correcto", "listo"
- Ejemplos de no confirmación: "no", "espera", "cambia", "falta algo"

IMPORTANTE SOBRE CREACIÓN:
- Solo cambiar processing_status a "creating_campaign" cuando TODOS los datos estén completos Y el usuario confirme
- Datos requeridos: campaign_name, event_name, event_date, timezone, admins, context
- Confirmación interpretada por LLM (no palabras específicas)

CONSULTA DE ESTADO:
- Si el usuario pregunta por el estado, estado del grupo, consultar evento, etc.
- Extraer event_id del mensaje si lo proporciona
- Dirigir a verificación de estado

Responde SOLO con JSON. Pide al LLM que sea flexible y extraiga los datos en lenguaje natural, devolviendo además
una clave `parsed` con valores lo más simples y normalizados posible. No codifiques reglas estrictas en Python;
deja que el LLM intente resolver entradas variadas (frases completas, abreviaturas, errores tipográficos).

##Ejemplos
Ejemplo de salida esperada con estilo conversacional:
{{
    "next_step": "paso_siguiente|completed|check_status|out_of_context",
    "bot_response": "Perfecto, campaña registrada ✅ Ahora dime, ¿cómo se llama tu evento?",
    "processing_status": "idle|creating_campaign|checking_status|out_of_context",
    "is_campaign_related": true/false,
    "parsed": {{
        "campaign_name": "campaña número 1",
        "event_name": "evento de navidad",
        "event_date": "2025-08-22T05:40:37.371Z",
        "timezone": "America/Argentina/Buenos_Aires",
        "admins": ["573165780882"],
        "context": "Campaña navideña con evento especial para diciembre",
        "event_id": "evento123",
        "user_confirms": true/false
    }}
}}
##Notas
NOTA: Si no hay datos nuevos que extraer, devuelve `parsed` con valores nulos o vacíos.
Si el usuario consulta el link de WhatsApp o message group o enlace, extrae el event_id si lo proporciona y devuelve next_step="check_status"
Si el usuario ya tiene el event_id y campaign_id no vacíos y quiere info de su campaña o evento -> next_step="completed".  
El código solo aplicará limpiezas ligeras por seguridad (p. ej. extraer dígitos de un elemento de `admins` si el LLM retorna "Solo para el numero 573...") — por lo demás, confía en el LLM.
"""


def router_node(state: ConversationState) -> dict:
    """Routes conversation using LLM intelligence"""
    current_step = state.get("current_step", "greeting")
    user_message = state.get("user_message", "")

    logger.info(f"🔄 Router: {current_step} - '{user_message[:50]}'")

    # Prepare collected data for LLM
    collected_data = {
        "campaign_id": state.get("campaign_id"),
        "event_id": state.get("event_id"),
        "campaign_name": state.get("campaign_name"),
        "event_name": state.get("event_name"),
        "event_date": state.get("event_date"),
        "timezone": state.get("timezone"),
        "admins": state.get("admins"),
        "context": state.get("context"),
    }

    try:
        response = client.responses.create(
            model="gpt-5-mini",
            input=[
                {
                    "role": "system",
                    "content": ROUTER_PROMPT.format(
                        current_step=current_step,
                        user_message=user_message,
                        collected_data=json.dumps(collected_data, ensure_ascii=False),
                    ),
                },
                {"role": "user", "content": user_message},
            ],
            #temperature=0.1,
        )

        content = response.output_text
        state["messages"] = AIMessage(content, additional_kwargs={"llm": "router"})
        # logger.info(f"Router LLM raw response: {content}")
        try:
            llm_res = json.loads(content)
        except Exception:
            llm_res = {
                "next_step": "out_of_context",
                "bot_response": (
                    "Disculpa, no entendí completamente tu mensaje. "
                    "Soy un asistente para crear campañas y eventos; si quieres, podemos empezar una campaña."
                ),
                "processing_status": "out_of_context",
                "is_campaign_related": False,
            }

        # Check if message is campaign-related
        is_campaign_related = llm_res.get("is_campaign_related", True)

        if not is_campaign_related:
            # Handle out-of-context messages
            state["current_step"] = "out_of_context"
            state["bot_response"] = llm_res.get(
                "bot_response",
                "Disculpa, soy un asistente especializado en la creación de campañas con eventos y grupos de WhatsApp. "
                "¿Te gustaría crear una campaña? Puedo ayudarte con eso.",
            )
            state["processing_status"] = "out_of_context"
            logger.info("❌ Message out of context - redirecting to campaign topics")
        else:
            # Update state based on LLM decision for campaign-related messages
            state["current_step"] = llm_res.get("next_step", current_step)
            state["bot_response"] = llm_res.get("bot_response", "¿Cómo puedo ayudarte?")

            llm_processing_status = llm_res.get("processing_status", "idle")
            if llm_processing_status in ["checking_status", "out_of_context"]:
                state["processing_status"] = llm_processing_status

            # Use parsed data from LLM when available (preferred)
            parsed = llm_res.get("parsed", {}) or {}

            # Campaign name & event name & date: trust LLM parsed values first; minimal fallback to raw message
            if parsed.get("campaign_name"):
                state["campaign_name"] = str(parsed.get("campaign_name")).strip()
            elif current_step == "campaign_name" and user_message.strip():
                state["campaign_name"] = user_message.strip()

            if parsed.get("event_name"):
                state["event_name"] = str(parsed.get("event_name")).strip()
            elif current_step == "event_name" and user_message.strip():
                state["event_name"] = user_message.strip()

            if parsed.get("event_date"):
                state["event_date"] = str(parsed.get("event_date")).strip()
            elif current_step == "event_date" and user_message.strip():
                state["event_date"] = user_message.strip()

            # Timezone
            if parsed.get("timezone"):
                state["timezone"] = str(parsed.get("timezone")).strip()
            elif current_step == "timezone" and user_message.strip():
                state["timezone"] = user_message.strip()

            # Admins: trust LLM to extract and clean phone numbers
            if parsed.get("admins"):
                admins_parsed = parsed.get("admins")
                if isinstance(admins_parsed, list):
                    state["admins"] = [str(a).strip() for a in admins_parsed]
                else:
                    state["admins"] = [str(admins_parsed).strip()]
            elif current_step == "admins" and user_message.strip():
                # Fallback: extract phone numbers if LLM didn't parse
                nums = re.findall(r"\+?\d{7,15}", user_message)
                if nums:
                    state["admins"] = nums
                else:
                    state["admins"] = [user_message.strip()]

            # Context
            if parsed.get("context"):
                state["context"] = str(parsed.get("context")).strip()
            elif current_step == "context" and user_message.strip():
                state["context"] = user_message.strip()

            # Confirmation - let LLM interpret if user is confirming
            if parsed.get("user_confirms") is not None:
                user_confirms = parsed.get("user_confirms")
                if user_confirms:
                    # Check if all required data is present
                    required_data = [
                        state.get("campaign_name"),
                        state.get("event_name"),
                        state.get("event_date"),
                        state.get("timezone"),
                        state.get("admins"),
                        state.get("context")
                    ]
                    if all(required_data):
                        state["processing_status"] = "creating_campaign"
                        logger.info("🚀 All data complete - starting campaign creation")
                    else:
                        state["bot_response"] = "Faltan algunos datos. Te ayudo a completarlos."
                        state["processing_status"] = "idle"
                else:
                    # User did not confirm - stay in current step or go back
                    state["processing_status"] = "idle"

            # Event ID for status checking
            if parsed.get("event_id"):
                state["event_id"] = str(parsed.get("event_id")).strip()

            logger.info(f"✅ Router -> {state['current_step']}: {state['bot_response'][:50]}...")

    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(f"❌ Router LLM error: {e}")
        state["bot_response"] = "Ocurrió un error. ¿Puedes repetir tu mensaje?"

    return state
