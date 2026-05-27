"""Decoradores semánticos para los componentes IA del proyecto.

Wrappers finos sobre `langfuse.decorators.observe`, la mejor práctica
oficial de Langfuse v2. `@observe` captura input/output/latency/errores
automáticamente, soporta async, hace auto-nesting via contextvars (una
función decorada que llame a otra decorada genera spans hijo
automáticamente) y es tolerante a fallos del cliente Langfuse por diseño.

Uso típico desde F3/F4 (los imports van a nivel módulo, no dentro de la
función decorada):

    from langfuse.decorators import langfuse_context

    @trace_classifier
    def classify(description: str) -> dict:
        result = complete(description, system="Eres clasificador...")
        # Auto-traza `generation` gracias a litellm.success_callback=["langfuse"]
        # configurado vía init_observability() en app.main.
        parsed = parse_classifier_output(result.content)
        langfuse_context.update_current_observation(
            metadata={"cita_normativa": parsed["cita"]}
        )
        return parsed

Las defensas que existían en una versión anterior del plan (D1: trace
failure no rompe app; D2: init failure no rompe import) son inherentes a
`@observe` y al lazy init del SDK v2: el decorador captura sus propias
excepciones internas y el cliente Langfuse se inicializa sólo al emitir
la primera traza, no al import.
"""

# TODO Langfuse v3: el namespace `langfuse.decorators` desaparece — los
# decoradores se importan directamente desde `langfuse`. Cuando se desbloquee
# el pin `langfuse==2.*` en `backend/pyproject.toml`, cambiar a:
#     from langfuse import observe
from langfuse.decorators import observe

trace_classifier = observe(name="classifier")
trace_collector = observe(name="collector")
trace_chat = observe(name="chat")

__all__ = ["trace_chat", "trace_classifier", "trace_collector"]
