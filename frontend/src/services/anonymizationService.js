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
 
  async getAnonymizedRequest(sessionId) {
    console.log('📤 Llamando a /anonymize/session/{session_id}/anonymized-request...');
    
    const response = await apiClient.get(`/anonymize/session/${sessionId}/anonymized-request`);

    console.log('📥 Respuesta de /anonymized-request:', response.data);
    
    return {
      anonymized: response.data.anonymized_request,
      mapping: {},
      session_id: response.data.session_id
    };
  }

  async getAnonymizedRequestWithRetry(sessionId, maxRetries = 10, delayMs = 300) {
    for (let i = 0; i < maxRetries; i++) {
      try {
        const result = await this.getAnonymizedRequest(sessionId);
        console.log(`✅ Texto anonimizado obtenido en intento ${i + 1}`);
        return result;
      } catch (error) {
        if (i === maxRetries - 1) {
          console.error('❌ No se pudo obtener texto anonimizado después de todos los intentos');
          throw error;
        }
        
        console.log(`⏳ Intento ${i + 1}/${maxRetries} - Esperando texto anonimizado...`);
        await new Promise(resolve => setTimeout(resolve, delayMs));
      }
    }
  }

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
      console.log('🚀 Iniciando flujo completo: Dual Streaming con Panel 1 al detectar metadata');
      
      const streamingResult = await this.processDualStreamingChat(
        {
          sessionId,
          text, 
          file,
          image
        },
        {
          onStreamStart,
          onAnonymousChunk,
          onDeanonymizedChunk,
          
          onMetadata: async (metadata) => {
            console.log('📊 Metadata recibido, cargando Panel 1 inmediatamente...');
            
            try {
              const result = await this.getAnonymizedRequestWithRetry(sessionId);
              
              if (onAnonymized) {
                onAnonymized({
                  text: result.anonymized,
                  mapping: {},
                  pii_detected: metadata.pii_detected || true
                });
              }
              
              console.log('✅ Panel 1 cargado exitosamente');
            } catch (error) {
              console.warn('⚠️ Error cargando Panel 1:', error);
            }
          },
          
          onStreamEnd,
          onError
        }
      );

      return streamingResult;

    } catch (error) {
      if (onError) onError(error);
      throw error;
    }
  }

  async processDualStreamingChat(requestData, callbacks = {}) {
    const { sessionId, text, file, image } = requestData;
    const {
      onStreamStart,
      onMetadata,
      onAnonymousChunk,
      onDeanonymizedChunk,
      onStreamEnd,
      onError
    } = callbacks;

    try {
      const formData = new FormData();
      
      if (text) {
        formData.append('message', text);
      }
      
      formData.append('session_id', sessionId);
      formData.append('model', 'es');
      formData.append('use_regex', 'true');
      formData.append('pseudonymize', 'true');
      formData.append('save_mapping', 'true');
      formData.append('use_realistic_fake', 'true');
      
      if (file) {
        formData.append('file', file);
      }
      
      if (image) {
        formData.append('file', image);
      }

      console.log('📤 Llamando a /chat/streaming con session_id:', sessionId);

      if (onStreamStart) onStreamStart();

      const response = await fetch(`${API_BASE_URL}/chat/streaming`, {
        method: 'POST',
        body: formData,
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
                case 'metadata':
                  console.log('📊 Metadata detectado:', eventData);
                  if (onMetadata) {
                    onMetadata(eventData);
                  }
                  break;
                
                case 'llm_chunk_anonymous':
                case 'anonymous_chunk':
                case 'chunk_anonymous':
                case 'anonymous': 
                  currentAnonymousResponse += eventData.chunk || eventData.content || eventData.data || '';
                  if (onAnonymousChunk) {
                    onAnonymousChunk(currentAnonymousResponse);
                  }
                  break;
                
                case 'llm_chunk_deanonymized':
                case 'deanonymized_chunk':
                case 'chunk_deanonymized':
                case 'deanonymized': 
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

  async anonymizeText(data) {
    console.warn('⚠️ anonymizeText() está deprecated. Usa getAnonymizedRequest()');
    return this.getAnonymizedRequest(data.session_id);
  }

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

  async testEndpoints() {
    try {
      const sessionId = `test_${Date.now()}`;
      const testText = "Hola, soy Juan Pérez de Madrid";

      console.log('🧪 Testing /chat/streaming...');
      
      const formData = new FormData();
      formData.append('message', testText);
      formData.append('session_id', sessionId);
      formData.append('model', 'es');
      formData.append('save_mapping', 'true');
      
      const streamingResponse = await fetch(`${API_BASE_URL}/chat/streaming`, {
        method: 'POST',
        body: formData,
      });

      await new Promise(resolve => setTimeout(resolve, 2000));

      console.log('🧪 Testing /anonymized-request...');
      const anonymizedResult = await this.getAnonymizedRequest(sessionId);

      return {
        streaming: {
          status: streamingResponse.ok ? 'success' : 'error',
          statusCode: streamingResponse.status,
          contentType: streamingResponse.headers.get('content-type')
        },
        anonymizedRequest: {
          status: 'success',
          hasText: !!anonymizedResult.anonymized,
          textLength: anonymizedResult.anonymized?.length || 0
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

export const anonymizationService = new AnonymizationService();

export default AnonymizationService;