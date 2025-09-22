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
 
  async processAnonymization(requestData, callbacks = {}) {
    const { sessionId, text, file, image } = requestData;
    const {
      onAnonymized,
      onStreamStart,
      onStreamData,
      onStreamEnd,
      onDeanonymized,
      onError
    } = callbacks;

    try {
      // Anonimizar datos
      const anonymizedData = await this.anonymizeData({ text, file, image, sessionId });
      if (onAnonymized) onAnonymized(anonymizedData);

      // Enviar a modelo con streaming
      const modelResponse = await this.sendToModel(anonymizedData, {
        onStreamStart,
        onStreamData,
        onStreamEnd,
        sessionId
      });

      // Desanonimizar respuesta
      const finalResponse = await this.deanonymizeResponse({
        response: modelResponse,
        sessionId
      });
      
      if (onDeanonymized) onDeanonymized(finalResponse);

      return finalResponse;

    } catch (error) {
      if (onError) onError(error);
      throw error;
    }
  }

  async anonymizeData(data) {
    const formData = new FormData();
    
    if (data.text) {
      formData.append('text', data.text);
    }
    
    if (data.file) {
      formData.append('file', data.file);
    }
    
    if (data.image) {
      formData.append('image', data.image);
    }
    
    formData.append('session_id', data.sessionId);

    const response = await apiClient.post('/anonymize', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  }

  async sendToModel(anonymizedData, callbacks = {}) {
    const { onStreamStart, onStreamData, onStreamEnd, sessionId } = callbacks;
    
    if (onStreamStart) onStreamStart();

    try {
      const response = await fetch(`${API_BASE_URL}/process-llm`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          anonymized_text: anonymizedData.text || anonymizedData.content,
          session_id: sessionId,
          stream: true
        }),
      });

      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.type === 'chunk') {
                fullResponse += data.content;
                if (onStreamData) onStreamData(fullResponse);
              } else if (data.type === 'end') {
                if (onStreamEnd) onStreamEnd(fullResponse);
                return fullResponse;
              } else if (data.type === 'error') {
                throw new Error(data.message);
              }
            } catch (parseError) {
              console.warn('Error parsing SSE data:', parseError);
            }
          }
        }
      }

      if (onStreamEnd) onStreamEnd(fullResponse);
      return fullResponse;

    } catch (error) {
      throw new Error(`Error en streaming: ${error.message}`);
    }
  }

  async deanonymizeResponse(data) {
    const response = await apiClient.post('/deanonymize', {
      response: data.response,
      session_id: data.sessionId
    });

    return response.data.deanonymized_response;
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
      const response = await apiClient.get(`/session/${sessionId}/stats`);
      return response.data;
    } catch (error) {
      console.warn('No se pudieron obtener las estadísticas de sesión:', error);
      return null;
    }
  }


  async clearSession(sessionId) {
    try {
      await apiClient.delete(`/session/${sessionId}`);
    } catch (error) {
      console.warn('Error al limpiar la sesión:', error);
    }
  }
}

// Instancia singleton del servicio
export const anonymizationService = new AnonymizationService();

// Exportar también la clase para testing
export default AnonymizationService;