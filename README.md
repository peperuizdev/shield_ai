# Shield AI

Sistema Inteligente de Anonimización de Datos para modelos de IA Generativa.


## Desanonimizacion
Endpoints Principales

POST /setup-dummy-session/{session_id}: Crea datos dummy para pruebas
POST /deanonymize: Desanonimización síncorna completa
GET /deanonymize-stream/{session_id}: Streaming de desanonimización
GET /test-full-process/{session_id}: Prueba end-to-end

💡 Para Integración Real

Reemplaza dummy_llm_response_stream() con la llamada real al LLM
Ajusta los patrones de regex según tus tipos de PII específicos
Modifica el TTL de Redis según tus necesidades de seguridad
Implementa autenticación si es necesario

docker run -d -p 6379:6379 redis:alpine        