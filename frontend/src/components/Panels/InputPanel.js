import React, { useRef, useState, useEffect } from 'react';
import { Send, Paperclip, Image as ImageIcon, FileText, AlertCircle, X, File } from 'lucide-react';
import { useApp } from '../../contexts/AppContext';
import { anonymizationService } from '../../services/anonymizationService';
import { imageAnonymizationService } from '../../services/imageAnonymizationService';
import Button from '../Common/Button';

const InputPanel = () => {
  const { state, actions } = useApp();
  const fileInputRef = useRef(null);
  const imageInputRef = useRef(null);
  const [imagePreview, setImagePreview] = useState(null);

  const handleTextChange = (e) => {
    actions.setInputText(e.target.value);
  };

  useEffect(() => {
    if (state.inputImage) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result);
        actions.setOriginalImagePreview(reader.result);
      };
      reader.readAsDataURL(state.inputImage);
    } else {
      setImagePreview(null);
      actions.setOriginalImagePreview(null);
    }
  }, [state.inputImage]);

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      actions.setInputFile(file);
    }
    event.target.value = '';
  };

  const handleImageSelect = (event) => {
    const image = event.target.files[0];
    if (image) {
      actions.setInputImage(image);
    }
    event.target.value = '';
  };

  const handleRemoveFile = () => {
    actions.setInputFile(null);
  };

  const handleRemoveImage = () => {
    actions.setInputImage(null);
    setImagePreview(null);
  };

  const handleSubmit = async () => {
    const hasTextOrDocument = state.inputText.trim() || state.inputFile;
    const hasImage = state.inputImage;

    if (!hasTextOrDocument && !hasImage) {
      actions.setError('Por favor, ingresa texto, selecciona un archivo o sube una imagen.');
      return;
    }

    try {
      actions.setLoading(true);
      actions.clearError();
      actions.resetProcess();
      
      const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      actions.setSessionId(sessionId);

      if (hasTextOrDocument) {
        const hasDocument = state.inputFile;
        
        if (hasDocument) {
          actions.setProcessingDocument(true);
        }

        const requestData = {
          sessionId,
          text: state.inputText,
          file: state.inputFile,
          image: null
        };

        console.log('🚀 Iniciando flujo completo: Anonimización + Dual Streaming');

        await anonymizationService.processCompleteFlow(requestData, {
          onAnonymized: (anonymizedData) => {
            console.log('✅ Panel 1 - onAnonymized ejecutado:', anonymizedData);
            actions.setAnonymizedText(anonymizedData.text);
            console.log('✅ Panel 1 actualizado - Datos anonimizados');
          },

          onStreamStart: () => {
            actions.startStreaming();
            console.log('🚀 Iniciando streaming para paneles 2 y 3');
          },

          onAnonymousChunk: (anonymousText) => {
            actions.setModelResponse(anonymousText);
          },

          onDeanonymizedChunk: (deanonymizedText) => {
            actions.updateStreamingText(deanonymizedText);
          },

          onStreamEnd: async (result) => {
            actions.stopStreaming();
            if (result.anonymousResponse) {
              actions.setModelResponse(result.anonymousResponse);
            }
            if (result.finalResponse) {
              actions.setFinalResponse(result.finalResponse);
            }
            
            try {
              console.log('🔄 Cargando Panel 1 después del streaming...');
              const anonymizedResult = await anonymizationService.getAnonymizedRequest(sessionId);
              if (anonymizedResult && anonymizedResult.anonymized) {
                actions.setAnonymizedText(anonymizedResult.anonymized);
                console.log('✅ Panel 1 cargado después del streaming');
              }
            } catch (error) {
              console.warn('⚠️ No se pudo cargar Panel 1:', error);
            }
            
            if (hasDocument) {
              actions.setProcessingDocument(false);
            }
          },

          onError: (error) => {
            console.error('❌ Error en flujo completo:', error);
            actions.setError(error.message);
            actions.stopStreaming();
            actions.setProcessingDocument(false);
          }
        });
      }

      if (hasImage) {
        actions.setProcessingImage(true);

        try {
          const imageResult = await imageAnonymizationService.anonymizeImage(
            state.inputImage,
            sessionId
          );

          actions.setAnonymizedImage(imageResult.anonymized_image);
          actions.setImageDetectionInfo(imageResult.detections);
          actions.setProcessingImage(false);
        } catch (error) {
          actions.setError(`Error procesando imagen: ${error.message}`);
          actions.setProcessingImage(false);
        }
      }

    } catch (error) {
      console.error('❌ Error general en flujo:', error);
      actions.setError(`Error en el proceso: ${error.message}`);
      actions.stopStreaming();
      actions.setProcessingDocument(false);
      actions.setProcessingImage(false);
    } finally {
      actions.setLoading(false);
    }
  };

  const handleTestEndpoints = async () => {
    try {
      const results = await anonymizationService.testEndpoints();
      console.log('🧪 Test de endpoints:', results);
      
      if (results.streaming?.status === 'success') {
        actions.clearError();
        alert(`✅ Endpoint funcionando\n\n/chat/streaming: ✅ Status: ${results.streaming.statusCode}`);
      } else {
        actions.setError(`❌ Error en endpoints: ${results.error || 'Algún endpoint falló'}`);
      }
    } catch (error) {
      actions.setError(`❌ Error probando endpoints: ${error.message}`);
    }
  };

  const isDisabled = state.isLoading || state.isStreaming || state.isProcessingImage;
  const hasContent = state.inputText.trim() || state.inputFile || state.inputImage;

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = (file) => {
    if (!file) return null;
    
    const fileName = file.name.toLowerCase();
    
    if (fileName.endsWith('.pdf')) {
      return <File className="w-5 h-5 text-red-500" />;
    } else if (fileName.endsWith('.doc') || fileName.endsWith('.docx')) {
      return <FileText className="w-5 h-5 text-blue-500" />;
    } else if (fileName.endsWith('.xls') || fileName.endsWith('.xlsx')) {
      return <FileText className="w-5 h-5 text-green-500" />;
    } else {
      return <Paperclip className="w-5 h-5 text-gray-500" />;
    }
  };

  return (
    <div className="overflow-hidden bg-white border border-gray-200 rounded-xl shadow-brand">
      <div className="px-6 py-4 bg-gradient-to-r from-brand-primary to-brand-secondary">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="flex items-center space-x-2 text-lg font-semibold text-white">
              <FileText className="w-5 h-5" />
              <span>Entrada de Datos</span>
            </h2>
            <p className="mt-1 text-sm text-brand-light">
              Introduce texto, sube documentos o imágenes para procesar
            </p>
          </div>
          
          {process.env.NODE_ENV === 'development' && (
            <Button
              onClick={handleTestEndpoints}
              variant="outline"
              size="sm"
              className="text-white bg-white border-white bg-opacity-20 border-opacity-30 hover:bg-opacity-30"
            >
              🧪 Test
            </Button>
          )}
        </div>
      </div>

      <div className="p-6">
        <div className="space-y-4">
          <div className="relative">
            {(state.inputFile || state.inputImage) && (
              <div className="mb-3 space-y-2">
                {state.inputFile && (
                  <div className="bg-white border border-gray-200 rounded-lg p-2.5 shadow-sm">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2.5 min-w-0 flex-1">
                        <div className="bg-gray-50 rounded p-1.5">
                          {getFileIcon(state.inputFile)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-gray-900 truncate">
                            {state.inputFile.name}
                          </p>
                          <p className="text-[10px] text-gray-500 mt-0.5">
                            {formatFileSize(state.inputFile.size)}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={handleRemoveFile}
                        disabled={isDisabled}
                        className="flex-shrink-0 p-1 text-gray-400 transition-colors rounded hover:bg-gray-100 hover:text-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )}

                {state.inputImage && (
                  <div className="bg-white border border-gray-200 rounded-lg p-2.5 shadow-sm">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2.5 min-w-0 flex-1">
                        <img 
                          src={imagePreview} 
                          alt="Preview" 
                          className="object-cover border border-gray-200 rounded w-14 h-14"
                        />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-gray-900 truncate">
                            {state.inputImage.name}
                          </p>
                          <p className="text-[10px] text-gray-500 mt-0.5">
                            {formatFileSize(state.inputImage.size)}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={handleRemoveImage}
                        disabled={isDisabled}
                        className="flex-shrink-0 p-1 text-gray-400 transition-colors rounded hover:bg-gray-100 hover:text-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            <textarea
              placeholder="Escribe tu consulta aquí. Por ejemplo: 'Mi nombre es Juan Pérez, vivo en Madrid y mi email es juan.perez@email.com. ¿Puedes ayudarme con información sobre préstamos hipotecarios?'"
              value={state.inputText}
              onChange={handleTextChange}
              disabled={isDisabled}
              rows={6}
              className="w-full px-4 py-3 text-sm placeholder-gray-500 transition-all duration-200 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-brand-primary focus:border-brand-primary disabled:bg-gray-50 disabled:cursor-not-allowed"
            />
          </div>

          <div className="flex items-center text-xs text-gray-500">
            <AlertCircle className="w-4 h-4 mr-2" />
            Puedes combinar texto, documentos e imágenes en un solo proceso
          </div>
          
          {state.isProcessingDocument && (
            <div className="flex items-center px-3 py-2 space-x-2 text-xs text-purple-600 rounded-lg bg-purple-50">
              <div className="w-2 h-2 bg-purple-600 rounded-full animate-pulse"></div>
              <span>📄 Leyendo y procesando documento...</span>
            </div>
          )}

          {state.isProcessingImage && (
            <div className="flex items-center px-3 py-2 space-x-2 text-xs text-orange-600 rounded-lg bg-orange-50">
              <div className="w-2 h-2 bg-orange-600 rounded-full animate-pulse"></div>
              <span>🖼️ Procesando imagen...</span>
            </div>
          )}
          
          {state.isLoading && !state.isProcessingDocument && !state.isStreaming && !state.isProcessingImage && (
            <div className="flex items-center px-3 py-2 space-x-2 text-xs rounded-lg text-brand-primary bg-brand-light bg-opacity-20">
              <div className="w-2 h-2 rounded-full animate-pulse bg-brand-primary"></div>
              <span>🔒 Anonimizando datos personales...</span>
            </div>
          )}
          
          {state.isStreaming && (
            <div className="flex items-center px-3 py-2 space-x-2 text-xs text-blue-600 rounded-lg bg-blue-50">
              <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></div>
              <span>⚡ Generando respuestas en tiempo real...</span>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between mt-6">
          <div className="flex items-center space-x-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.xlsx,.txt"
              onChange={handleFileSelect}
              disabled={isDisabled}
              className="hidden"
            />
            <input
              ref={imageInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageSelect}
              disabled={isDisabled}
              className="hidden"
            />
            
            <Button
              onClick={() => fileInputRef.current?.click()}
              disabled={isDisabled}
              variant="outline"
              size="sm"
              className="flex items-center space-x-2"
            >
              <Paperclip className="w-4 h-4" />
              <span className="hidden sm:inline">Archivo</span>
            </Button>
            
            <Button
              onClick={() => imageInputRef.current?.click()}
              disabled={isDisabled}
              variant="outline"
              size="sm"
              className="flex items-center space-x-2"
            >
              <ImageIcon className="w-4 h-4" />
              <span className="hidden sm:inline">Imagen</span>
            </Button>

            {(state.inputFile || state.inputImage) && (
              <div className="hidden md:flex items-center text-xs text-gray-600 bg-gray-50 px-3 py-1.5 rounded-lg">
                {state.inputFile && '📎 1 archivo'}
                {state.inputFile && state.inputImage && ' + '}
                {state.inputImage && '🖼️ 1 imagen'}
              </div>
            )}
          </div>

          <Button
            onClick={handleSubmit}
            disabled={isDisabled || !hasContent}
            loading={state.isLoading}
            className="px-8 py-3"
          >
            <Send className="w-4 h-4 mr-2" />
            {state.isProcessingDocument
              ? 'Procesando documento...'
              : state.isProcessingImage
                ? 'Procesando imagen...'
                : state.isLoading && !state.isStreaming
                  ? 'Anonimizando...'
                  : state.isStreaming 
                    ? 'Generando respuestas...' 
                    : 'Iniciar Proceso'}
          </Button>
        </div>

        {state.error && (
          <div className="flex items-center p-4 mt-4 space-x-2 border border-red-200 rounded-lg bg-red-50">
            <AlertCircle className="flex-shrink-0 w-5 h-5 text-red-500" />
            <span className="text-sm text-red-700">{state.error}</span>
          </div>
        )}

        {process.env.NODE_ENV === 'development' && state.sessionId && (
          <div className="p-3 mt-4 border border-gray-200 rounded-lg bg-gray-50">
            <p className="text-xs text-gray-600">
              <strong>Dev Info:</strong> Session ID: {state.sessionId}
            </p>
            <p className="text-xs text-gray-600">
              Loading: {state.isLoading ? '🟢' : '🔴'} | 
              Processing Doc: {state.isProcessingDocument ? '🟢' : '🔴'} |
              Streaming: {state.isStreaming ? '🟢' : '🔴'}
            </p>
            <p className="text-xs text-gray-600">
              Paneles: 
              {state.anonymizedText ? ' ✅P1' : ' ❌P1'} |
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