import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_ENDPOINT || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'multipart/form-data',
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

class ImageAnonymizationService {
  async anonymizeImage(imageFile, sessionId, options = {}) {
    try {
      const formData = new FormData();
      formData.append('file', imageFile);
      formData.append('session_id', sessionId);
      formData.append('detect_faces', options.detect_faces !== false ? 'true' : 'false');
      formData.append('face_method', options.face_method || 'blur');
      formData.append('store_originals', options.store_originals !== false ? 'true' : 'false');
      formData.append('return_format', 'base64');

      const response = await apiClient.post('/anonymize/image', formData);

      return {
        anonymized_image: response.data.anonymized_image,
        session_id: response.data.session_id,
        pii_detected: response.data.pii_detected,
        detections: response.data.detections,
        image_info: response.data.image_info,
        methods: response.data.methods
      };
    } catch (error) {
      throw error;
    }
  }

  async getAnonymizationMap(sessionId) {
    try {
      const response = await apiClient.get(`/anonymize/session/${sessionId}/image-map`);
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  async deanonymizeImage(imageFile, sessionId) {
    try {
      const formData = new FormData();
      formData.append('file', imageFile);
      formData.append('session_id', sessionId);
      formData.append('return_format', 'base64');

      const response = await apiClient.post('/anonymize/image/deanonymize', formData);

      return {
        restored_image: response.data.restored_image,
        session_id: response.data.session_id,
        regions_restored: response.data.regions_restored
      };
    } catch (error) {
      throw error;
    }
  }
}

export const imageAnonymizationService = new ImageAnonymizationService();

export default ImageAnonymizationService;