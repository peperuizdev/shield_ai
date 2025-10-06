import React, { useState } from 'react';
import { Send, Upload, Image as ImageIcon, FileText, AlertCircle } from 'lucide-react';
import { useApp } from '../../contexts/AppContext';
import { anonymizationService } from '../../services/anonymizationService';
import Button from '../Common/Button';
import TextArea from '../Common/TextArea';
import FileUpload from '../Common/FileUpload';

const InputPanel = () => {
  const { state, actions } = useApp();
  const [activeTab, setActiveTab] = useState('text');

  const handleTextChange = (value) => {
    actions.setInputText(value);
  };

  const handleFileUpload = (file) => {
    actions.setInputFile(file);
  };

  const handleImageUpload = (image) => {
    actions.setInputImage(image);
  };

  const handleSubmit = async () => {
    if (!state.inputText.trim() && !state.inputFile && !state.inputImage) {
      actions.setError('Por favor, ingresa texto, selecciona un archivo o sube una imagen.');
      return;
    }

    try {
      actions.setLoading(true);
      actions.clearError();
      actions.resetProcess();
      
      const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      actions.setSessionId(sessionId);

      const requestData = {
        sessionId,
        text: state.inputText,
        file: state.inputFile,
        image: state.inputImage
      };

      console.log('🚀 Iniciando flujo completo: Streaming dual + Panel 1 al detectar metadata');

      await anonymizationService.processCompleteFlow(requestData, {
  
        onStreamStart: () => {
          actions.startStreaming();
          console.log('🚀 Streaming iniciado - Paneles 2 y 3');
        },

        onAnonymousChunk: (anonymousText) => {
          actions.setModelResponse(anonymousText);  // ← Panel 2
          console.log('🤖 Panel 2 actualizado (streaming)');
        },

        onDeanonymizedChunk: (deanonymizedText) => {
          actions.updateStreamingText(deanonymizedText);  // ← Panel 3
          console.log('✨ Panel 3 actualizado (streaming)');
        },

        onAnonymized: (anonymizedData) => {
          actions.setAnonymizedText(anonymizedData.text);
          console.log('✅ Panel 1 actualizado - Texto anonimizado cargado');
        },

        onStreamEnd: (result) => {
          actions.stopStreaming();
          
          if (result.anonymousResponse) {
            actions.setModelResponse(result.anonymousResponse);
          }
          if (result.finalResponse) {
            actions.setFinalResponse(result.finalResponse);
          }

          console.log('🎉 Flujo completo terminado');
        },

        onError: (error) => {
          console.error('❌ Error en flujo completo:', error);
          actions.setError(error.message);
          actions.stopStreaming();
        }
      });

    } catch (error) {
      console.error('❌ Error general en flujo:', error);
      actions.setError(`Error en el proceso: ${error.message}`);
      actions.stopStreaming();
    } finally {
      actions.setLoading(false);
    }
  };

  const isDisabled = state.isLoading || state.isStreaming;
  const hasContent = state.inputText.trim() || state.inputFile || state.inputImage;

  const handleTestEndpoints = async () => {
    try {
      const results = await anonymizationService.testEndpoints();
      console.log('🧪 Test de endpoints:', results);
      
      if (results.streaming?.status === 'success' && results.anonymizedRequest?.status === 'success') {
        actions.clearError();
        alert(`✅ Ambos endpoints funcionando
        
/chat/streaming: ✅ Status: ${results.streaming.statusCode}
/anonymized-request: ✅ Texto obtenido: ${results.anonymizedRequest.hasText ? 'Sí' : 'No'} (${results.anonymizedRequest.textLength} caracteres)

El flujo funciona correctamente!`);
      } else {
        actions.setError(`❌ Error en endpoints: ${results.error || 'Algún endpoint falló'}`);
      }
    } catch (error) {
      actions.setError(`❌ Error probando endpoints: ${error.message}`);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-brand border border-gray-200 overflow-hidden">
      <div className="bg-gradient-to-r from-brand-primary to-brand-secondary px-6 py-4">
        <div className="flex justify-between items-start">
          <div>
            <h2 className="text-lg font-semibold text-white flex items-center space-x-2">
              <FileText className="w-5 h-5" />
              <span>Entrada de Datos</span>
            </h2>
            <p className="text-brand-light text-sm mt-1">
              Panel 1 se carga al inicio, Paneles 2 y 3 en streaming simultáneo
            </p>
          </div>
          
          {process.env.NODE_ENV === 'development' && (
            <Button
              onClick={handleTestEndpoints}
              variant="outline"
              size="sm"
              className="bg-white bg-opacity-20 border-white border-opacity-30 text-white hover:bg-opacity-30"
            >
              🧪 Test
            </Button>
          )}
        </div>
      </div>

      <div className="border-b border-gray-200">
        <nav className="flex space-x-0">
          <button
            onClick={() => setActiveTab('text')}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'text'
                ? 'border-brand-primary text-brand-primary bg-brand-light bg-opacity-50'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Texto
          </button>
          <button
            onClick={() => setActiveTab('file')}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'file'
                ? 'border-brand-primary text-brand-primary bg-brand-light bg-opacity-50'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Archivo
          </button>
          <button
            onClick={() => setActiveTab('image')}
            className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'image'
                ? 'border-brand-primary text-brand-primary bg-brand-light bg-opacity-50'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Imagen
          </button>
        </nav>
      </div>

      <div className="p-6">
        {activeTab === 'text' && (
          <div className="space-y-4">
            <TextArea
              placeholder="Escribe tu consulta aquí. Por ejemplo: 'Mi nombre es Juan Pérez, vivo en Madrid y mi email es juan.perez@email.com. ¿Puedes ayudarme con información sobre préstamos hipotecarios?'"
              value={state.inputText}
              onChange={handleTextChange}
              disabled={isDisabled}
              rows={6}
              className="w-full"
            />
            <div className="flex items-center text-xs text-gray-500">
              <AlertCircle className="w-4 h-4 mr-2" />
              Orden: Panel 1 (datos anonimizados) → Panel 2 y 3 (streaming simultáneo)
            </div>
            
            {state.isLoading && !state.isStreaming && (
              <div className="flex items-center space-x-2 text-xs text-brand-primary bg-brand-light bg-opacity-20 px-3 py-2 rounded-lg">
                <div className="animate-pulse w-2 h-2 bg-brand-primary rounded-full"></div>
                <span>Iniciando proceso...</span>
              </div>
            )}
            
            {state.isStreaming && (
              <div className="flex items-center space-x-2 text-xs text-blue-600 bg-blue-50 px-3 py-2 rounded-lg">
                <div className="animate-pulse w-2 h-2 bg-blue-600 rounded-full"></div>
                <span>Streaming en tiempo real en Paneles 2 y 3...</span>
              </div>
            )}
          </div>
        )}

        {activeTab === 'file' && (
          <div className="space-y-4">
            <FileUpload
              accept=".pdf,.docx,.xlsx,.txt"
              onFileSelect={handleFileUpload}
              disabled={isDisabled}
              selectedFile={state.inputFile}
            />
            <div className="text-sm text-gray-600">
              <AlertCircle className="w-4 h-4 inline mr-1 text-yellow-500" />
              <strong>Nota:</strong> Los archivos aún no están soportados. Usa texto por ahora.
            </div>
          </div>
        )}

        {activeTab === 'image' && (
          <div className="space-y-4">
            <FileUpload
              accept="image/*"
              onFileSelect={handleImageUpload}
              disabled={isDisabled}
              selectedFile={state.inputImage}
              icon={ImageIcon}
              text="Seleccionar imagen o arrastrar aquí"
            />
            <div className="text-sm text-gray-600">
              <AlertCircle className="w-4 h-4 inline mr-1 text-yellow-500" />
              <strong>Nota:</strong> Las imágenes aún no están soportadas. Usa texto por ahora.
            </div>
          </div>
        )}

        <div className="mt-6 flex justify-end">
          <Button
            onClick={handleSubmit}
            disabled={isDisabled || !hasContent}
            loading={state.isLoading}
            className="px-8 py-3"
          >
            <Send className="w-4 h-4 mr-2" />
            {state.isLoading && !state.isStreaming
              ? 'Iniciando...'
              : state.isStreaming 
                ? 'Streaming en curso...' 
                : 'Iniciar Proceso Completo'}
          </Button>
        </div>

        {state.error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
            <span className="text-red-700 text-sm">{state.error}</span>
          </div>
        )}

        {process.env.NODE_ENV === 'development' && state.sessionId && (
          <div className="mt-4 p-3 bg-gray-50 border border-gray-200 rounded-lg">
            <p className="text-xs text-gray-600">
              <strong>Dev Info:</strong> Session ID: {state.sessionId}
            </p>
            <p className="text-xs text-gray-600">
              Loading: {state.isLoading ? '🟢 Activo' : '🔴 Inactivo'} | 
              Streaming: {state.isStreaming ? '🟢 Activo' : '🔴 Inactivo'}
            </p>
            <p className="text-xs text-gray-600">
              Flujo: metadata → /anonymized-request (P1), chunks → P2+P3
            </p>
            <p className="text-xs text-gray-600">
              Paneles: 
              {state.anonymizedText ? ' ✅P1' : ' ⏳P1'} |
              {state.modelResponse ? ' ✅P2' : ' ❌P2'} |
              {state.finalResponse || state.streamingText ? ' ✅P3' : ' ❌P3'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default InputPanel;