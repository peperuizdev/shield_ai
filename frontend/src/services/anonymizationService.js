import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_ENDPOINT || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, 
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const message = error.response.data?.message || error.response.data?.detail || 'Error del servidor';
      throw new Error(`Error ${error.response.status}: ${message}`);
    } else if (error.request) {
      throw new Error('No se pudo conectar con el servidor. Verifica tu conexión.');
    } else {
      throw new Error('Error en la configuración de la petición');
    }
  }
);

class AnonymizationService {
 
  /**
   * FLUJO COMPLETO: Anonimización + Dual Streaming Chat
   * 1. Llama a /anonymize → Panel 1
   * 2. Llama a /chat/streaming → Panel 2 + 3
   */
  async processCompleteFlow(requestData, callbacks = {}) {
    const { sessionId, text, file, image } = requestData;
    const {
      onAnonymized,
      onStreamStart,
      onAnonymousChunk,
      onDeanonymizedChunk,
      onStreamEnd,
      onError
    } = callbacks;

    try {
      // ===== PASO 1: ANONIMIZACIÓN → PANEL 1 =====
      console.log('🔐 Step 1: Anonimizando texto...');
      
      const anonymizationResult = await this.anonymizeText({
        text,
        session_id: sessionId,
        model: 'es',
        use_regex: true,
        pseudonymize: true
      });

      // Mostrar resultado en Panel 1
      if (onAnonymized) {
        onAnonymized({
          text: anonymizationResult.anonymized,
          mapping: anonymizationResult.mapping,
          pii_detected: Object.keys(anonymizationResult.mapping || {}).length > 0
        });
      }

      console.log('✅ Anonimización completada, PII detectado:', Object.keys(anonymizationResult.mapping || {}).length > 0);

      // ===== PASO 2: DUAL STREAMING CHAT → PANEL 2 + 3 =====
      console.log('🚀 Step 2: Iniciando dual streaming...');
      
      const streamingResult = await this.processDualStreamingChat(
        {
          sessionId,
          text, // Texto original, el backend usará el mapa guardado en Redis
          file,
          image
        },
        {
          onStreamStart,
          onAnonymousChunk,
          onDeanonymizedChunk,
          onStreamEnd,
          onError
        }
      );

      return {
        anonymized: anonymizationResult.anonymized,
        mapping: anonymizationResult.mapping,
        ...streamingResult
      };

    } catch (error) {
      if (onError) onError(error);
      throw error;
    }
  }

  /**
   * PASO 1: Anonimización usando endpoint /anonymize
   */
  async anonymizeText(data) {
    console.log('📤 Llamando a /anonymize...');
    
    const response = await apiClient.post('/anonymize', {
      text: data.text,
      model: data.model || 'es',
      use_regex: data.use_regex !== false,
      pseudonymize: data.pseudonymize !== false,
      session_id: data.session_id
    });

    console.log('📥 Respuesta de /anonymize:', response.data);
    return response.data;
  }

  /**
   * PASO 2: Dual streaming usando endpoint /chat/streaming  
   */
  async processDualStreamingChat(requestData, callbacks = {}) {
    const { sessionId, text, file, image } = requestData;
    const {
      onStreamStart,
      onAnonymousChunk,
      onDeanonymizedChunk,
      onStreamEnd,
      onError
    } = callbacks;

    try {
      // Preparar datos para el endpoint de chat streaming
      const chatRequest = {
        message: text || '',
        session_id: sessionId,
        model: 'es',
        use_regex: true,
        pseudonymize: true,
        save_mapping: true, // Usar mapa existente de la sesión
        use_realistic_fake: true
      };

      console.log('📤 Llamando a /chat/streaming con session_id:', sessionId);

      if (onStreamStart) onStreamStart();

      const response = await fetch(`${API_BASE_URL}/chat/streaming`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(chatRequest),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(`Error ${response.status}: ${errorData.detail || response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let currentAnonymousResponse = '';
      let currentDeanonymizedResponse = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const eventData = JSON.parse(line.slice(6));
              
              console.log('📥 Evento SSE recibido:', eventData.type);
              
              switch (eventData.type) {
                case 'llm_chunk_anonymous':
                case 'anonymous_chunk':
                case 'chunk_anonymous':
                case 'anonymous': // ← AÑADIR ESTA LÍNEA
                  currentAnonymousResponse += eventData.chunk || eventData.content || eventData.data || '';
                  if (onAnonymousChunk) {
                    onAnonymousChunk(currentAnonymousResponse);
                  }
                  break;
                
                case 'llm_chunk_deanonymized':
                case 'deanonymized_chunk':
                case 'chunk_deanonymized':
                case 'deanonymized': // ← AÑADIR ESTA LÍNEA
                  currentDeanonymizedResponse += eventData.chunk || eventData.content || eventData.data || '';
                  if (onDeanonymizedChunk) {
                    onDeanonymizedChunk(currentDeanonymizedResponse);
                  }
                  break;
                
                case 'complete':
                case 'end':
                case 'done':
                  if (onStreamEnd) {
                    onStreamEnd({
                      anonymousResponse: currentAnonymousResponse,
                      finalResponse: currentDeanonymizedResponse,
                      sessionId: eventData.session_id || sessionId
                    });
                  }
                  return {
                    anonymousResponse: currentAnonymousResponse,
                    finalResponse: currentDeanonymizedResponse
                  };
                
                case 'error':
                  throw new Error(eventData.message || eventData.error || 'Error en el streaming');
                
                default:
                  console.log('🔄 Evento SSE desconocido:', eventData.type, eventData);
                  // Intentar procesar como chunk genérico
                  if (eventData.content || eventData.data) {
                    currentDeanonymizedResponse += eventData.content || eventData.data;
                    if (onDeanonymizedChunk) {
                      onDeanonymizedChunk(currentDeanonymizedResponse);
                    }
                  }
              }
            } catch (parseError) {
              console.warn('⚠️ Error parsing SSE data:', parseError, line);
            }
          }
        }
      }

      // Si llegamos aquí sin evento 'complete', devolver lo que tenemos
      if (onStreamEnd) {
        onStreamEnd({
          anonymousResponse: currentAnonymousResponse,
          finalResponse: currentDeanonymizedResponse,
          sessionId
        });
      }

      return {
        anonymousResponse: currentAnonymousResponse,
        finalResponse: currentDeanonymizedResponse
      };

    } catch (error) {
      if (onError) onError(error);
      throw error;
    }
  }

  // Métodos individuales para casos específicos
  async anonymizeData(data) {
    return this.anonymizeText(data);
  }

  async deanonymizeResponse(data) {
    const response = await apiClient.post('/deanonymize', {
      text: data.response,
      session_id: data.sessionId
    });

    return response.data.success ? response.data.deanonymized_text : data.response;
  }

  // Método legacy para compatibilidad total
  async processAnonymization(requestData, callbacks = {}) {
    console.warn('processAnonymization redirigido a processCompleteFlow');
    return this.processCompleteFlow(requestData, callbacks);
  }

  async checkHealth() {
    try {
      const response = await apiClient.get('/health');
      return response.data;
    } catch (error) {
      throw new Error('El backend no está disponible');
    }
  }

  async getSessionStats(sessionId) {
    try {
      const response = await apiClient.get(`/sessions/${sessionId}/stats`);
      return response.data;
    } catch (error) {
      console.warn('No se pudieron obtener las estadísticas de sesión:', error);
      return null;
    }
  }

  async clearSession(sessionId) {
    try {
      await apiClient.delete(`/sessions/${sessionId}`);
    } catch (error) {
      console.warn('Error al limpiar la sesión:', error);
    }
  }

  // Método para probar ambos endpoints
  async testEndpoints() {
    try {
      const sessionId = `test_${Date.now()}`;
      const testText = "Hola, soy Juan Pérez de Madrid";

      // Test 1: /anonymize
      console.log('🧪 Testing /anonymize...');
      const anonymizeResult = await this.anonymizeText({
        text: testText,
        session_id: sessionId,
        model: 'es'
      });

      // Test 2: /chat/streaming  
      console.log('🧪 Testing /chat/streaming...');
      const streamingResponse = await fetch(`${API_BASE_URL}/chat/streaming`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: testText,
          session_id: sessionId,
          model: 'es'
        }),
      });

      return {
        anonymize: {
          status: 'success',
          pii_detected: Object.keys(anonymizeResult.mapping || {}).length > 0,
          anonymized: anonymizeResult.anonymized
        },
        streaming: {
          status: streamingResponse.ok ? 'success' : 'error',
          statusCode: streamingResponse.status,
          contentType: streamingResponse.headers.get('content-type')
        }
      };

    } catch (error) {
      return {
        status: 'error',
        error: error.message
      };
    }
  }
}

// Instancia singleton del servicio
export const anonymizationService = new AnonymizationService();

// Exportar también la clase para testing
export default AnonymizationService;