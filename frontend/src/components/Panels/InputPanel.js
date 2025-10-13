import React, { useRef, useState, useEffect } from 'react';
import { Send, Paperclip, Image as ImageIcon, FileText, AlertCircle, X, File } from 'lucide-react';
import { useApp } from '../../contexts/AppContext';
import { anonymizationService } from '../../services/anonymizationService';
import Button from '../Common/Button';

const InputPanel = () => {
  const { state, actions } = useApp();
  const fileInputRef = useRef(null);
  const imageInputRef = useRef(null);
  const [imagePreview, setImagePreview] = useState(null);

  const handleTextChange = (e) => {
    actions.setInputText(e.target.value);
  };

  // Generar preview cuando se sube una imagen
  useEffect(() => {
    if (state.inputImage) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(state.inputImage);
    } else {
      setImagePreview(null);
    }
  }, [state.inputImage]);

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      if (state.inputImage) {
        actions.setInputImage(null);
      }
      actions.setInputFile(file);
    }
    // Reset input para permitir seleccionar el mismo archivo
    event.target.value = '';
  };

  const handleImageSelect = (event) => {
    const image = event.target.files[0];
    if (image) {
      if (state.inputFile) {
        actions.setInputFile(null);
      }
      actions.setInputImage(image);
    }
    // Reset input para permitir seleccionar la misma imagen
    event.target.value = '';
  };

  const handleRemoveAttachment = () => {
    actions.setInputFile(null);
    actions.setInputImage(null);
    setImagePreview(null);
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

      console.log('🚀 Iniciando flujo completo: Anonimización + Dual Streaming');

      // ⚠️ CALLBACKS SIN MODIFICAR - Como en tu código original
      await anonymizationService.processCompleteFlow(requestData, {
        onAnonymized: (anonymizedData) => {
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

        onStreamEnd: (result) => {
          actions.stopStreaming();
          if (result.anonymousResponse) {
            actions.setModelResponse(result.anonymousResponse);
          }
          if (result.finalResponse) {
            actions.setFinalResponse(result.finalResponse);
          }
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

  const handleTestEndpoints = async () => {
    try {
      const results = await anonymizationService.testEndpoints();
      console.log('🧪 Test de endpoints:', results);
      
      if (results.anonymize?.status === 'success' && results.streaming?.status === 'success') {
        actions.clearError();
        alert(`✅ Ambos endpoints funcionando\n\n/anonymize: ✅ PII detectado: ${results.anonymize.pii_detected}\n/chat/streaming: ✅ Status: ${results.streaming.statusCode}\n\nTexto anonimizado: ${results.anonymize.anonymized}`);
      } else {
        actions.setError(`❌ Error en endpoints: ${results.error || 'Algún endpoint falló'}`);
      }
    } catch (error) {
      actions.setError(`❌ Error probando endpoints: ${error.message}`);
    }
  };

  const isDisabled = state.isLoading || state.isStreaming;
  const hasContent = state.inputText.trim() || state.inputFile || state.inputImage;
  const currentAttachment = state.inputFile || state.inputImage;

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = () => {
    if (!currentAttachment) return null;
    
    const fileName = currentAttachment.name.toLowerCase();
    
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

  // ✨ SOLO CAMBIO ESTÉTICO: Padding dinámico más compacto
  const textareaPaddingTop = currentAttachment ? (state.inputImage ? '90px' : '70px') : '12px';

  return (
    <div className="bg-white rounded-xl shadow-brand border border-gray-200 overflow-hidden">
      {/* Header - Sin cambios */}
      <div className="bg-gradient-to-r from-brand-primary to-brand-secondary px-6 py-4">
        <div className="flex justify-between items-start">
          <div>
            <h2 className="text-lg font-semibold text-white flex items-center space-x-2">
              <FileText className="w-5 h-5" />
              <span>Entrada de Datos</span>
            </h2>
            <p className="text-brand-light text-sm mt-1">
              Introduce tu consulta para ver el proceso completo: anonimización + comparación de respuestas IA
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

      {/* Main Content */}
      <div className="p-6">
        <div className="space-y-4">
          {/* ✨ CAMBIO ESTÉTICO: Contenedor relativo para overlay integrado */}
          <div className="relative">
            {/* ✨ NUEVO: Overlay minimalista DENTRO del textarea */}
            {currentAttachment && (
              <div className="absolute top-3 left-3 right-3 z-10 animate-fade-in pointer-events-none">
                <div className="bg-white border border-gray-200 rounded-lg p-2.5 shadow-sm pointer-events-auto hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5 min-w-0 flex-1">
                      {/* Preview de Imagen o Icono */}
                      <div className="flex-shrink-0">
                        {state.inputImage && imagePreview ? (
                          <img 
                            src={imagePreview} 
                            alt="Preview" 
                            className="w-14 h-14 object-cover rounded border border-gray-200"
                          />
                        ) : (
                          <div className="bg-gray-50 rounded p-1.5">
                            {getFileIcon()}
                          </div>
                        )}
                      </div>
                      
                      {/* Info del Archivo */}
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-medium text-gray-900 truncate">
                          {currentAttachment.name}
                        </p>
                        <p className="text-[10px] text-gray-500 mt-0.5">
                          {formatFileSize(currentAttachment.size)}
                        </p>
                      </div>
                    </div>
                    
                    {/* Botón Eliminar */}
                    <button
                      onClick={handleRemoveAttachment}
                      disabled={isDisabled}
                      className="flex-shrink-0 p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-red-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Quitar adjunto"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* ✨ CAMBIO: Textarea con padding dinámico mejorado */}
            <textarea
              placeholder="Escribe tu consulta aquí. Por ejemplo: 'Mi nombre es Juan Pérez, vivo en Madrid y mi email es juan.perez@email.com. ¿Puedes ayudarme con información sobre préstamos hipotecarios?'"
              value={state.inputText}
              onChange={handleTextChange}
              disabled={isDisabled}
              rows={6}
              style={{ paddingTop: textareaPaddingTop }}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-brand-primary focus:border-brand-primary disabled:bg-gray-50 disabled:cursor-not-allowed placeholder-gray-500 resize-none transition-all duration-200"
            />
          </div>

          {/* Info Text - Sin cambios */}
          <div className="flex items-center text-xs text-gray-500">
            <AlertCircle className="w-4 h-4 mr-2" />
            Verás 3 pasos: datos anonimizados → respuesta con datos falsos → respuesta con datos reales
          </div>
          
          {/* Loading States - Sin cambios */}
          {state.isLoading && !state.isStreaming && (
            <div className="flex items-center space-x-2 text-xs text-brand-primary bg-brand-light bg-opacity-20 px-3 py-2 rounded-lg">
              <div className="animate-pulse w-2 h-2 bg-brand-primary rounded-full"></div>
              <span>Anonimizando datos personales...</span>
            </div>
          )}
          
          {state.isStreaming && (
            <div className="flex items-center space-x-2 text-xs text-blue-600 bg-blue-50 px-3 py-2 rounded-lg">
              <div className="animate-pulse w-2 h-2 bg-blue-600 rounded-full"></div>
              <span>Comparando respuestas en tiempo real...</span>
            </div>
          )}
        </div>

        {/* Barra de Herramientas - Sin cambios */}
        <div className="mt-6 flex items-center justify-between">
          {/* Botones de Adjuntar */}
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

            {/* ✨ CAMBIO: Indicador mejorado */}
            {currentAttachment && (
              <div className="hidden md:flex items-center text-xs text-gray-600 bg-gray-50 px-3 py-1.5 rounded-lg">
                {state.inputFile ? '📎 1 archivo' : '🖼️ 1 imagen'}
              </div>
            )}
          </div>

          {/* Botón de Enviar - Sin cambios */}
          <Button
            onClick={handleSubmit}
            disabled={isDisabled || !hasContent}
            loading={state.isLoading}
            className="px-8 py-3"
          >
            <Send className="w-4 h-4 mr-2" />
            {state.isLoading && !state.isStreaming
              ? 'Anonimizando...'
              : state.isStreaming 
                ? 'Comparando respuestas...' 
                : 'Iniciar Proceso Completo'}
          </Button>
        </div>

        {/* Error Display - Sin cambios */}
        {state.error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
            <span className="text-red-700 text-sm">{state.error}</span>
          </div>
        )}

        {/* Dev Info - Sin cambios */}
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
              Paneles: 
              {state.anonymizedText ? ' ✅P1' : ' ❌P1'} |
              {state.modelResponse ? ' ✅P2' : ' ❌P2'} |
              {state.finalResponse || state.streamingText ? ' ✅P3' : ' ❌P3'}
            </p>
            <p className="text-xs text-gray-600">
              Adjunto: {currentAttachment ? `✅ ${currentAttachment.name}` : '❌ Ninguno'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default InputPanel;