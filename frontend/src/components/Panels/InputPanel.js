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
      
      // Generar ID de sesión único
      const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      actions.setSessionId(sessionId);

      // Preparar datos para enviar
      const requestData = {
        sessionId,
        text: state.inputText,
        file: state.inputFile,
        image: state.inputImage
      };

      // Iniciar proceso de anonimización
      await anonymizationService.processAnonymization(requestData, {
        onAnonymized: (anonymizedData) => {
          actions.setAnonymizedText(anonymizedData.text || anonymizedData.content);
        },
        onStreamStart: () => {
          actions.startStreaming();
        },
        onStreamData: (chunk) => {
          actions.updateStreamingText(chunk);
        },
        onStreamEnd: (finalResponse) => {
          actions.stopStreaming();
          actions.setModelResponse(finalResponse);
        },
        onDeanonymized: (deanonymizedResponse) => {
          actions.setFinalResponse(deanonymizedResponse);
        },
        onError: (error) => {
          actions.setError(error.message);
        }
      });

    } catch (error) {
      actions.setError(`Error en el proceso: ${error.message}`);
    } finally {
      actions.setLoading(false);
    }
  };

  const isDisabled = state.isLoading || state.isStreaming;
  const hasContent = state.inputText.trim() || state.inputFile || state.inputImage;

  return (
    <div className="bg-white rounded-xl shadow-brand border border-gray-200 overflow-hidden">
      {/* Header del panel */}
      <div className="bg-gradient-to-r from-brand-primary to-brand-secondary px-6 py-4">
        <h2 className="text-lg font-semibold text-white flex items-center space-x-2">
          <FileText className="w-5 h-5" />
          <span>Entrada de Datos</span>
        </h2>
        <p className="text-brand-light text-sm mt-1">
          Introduce tu consulta, sube un archivo o una imagen para comenzar
        </p>
      </div>

      {/* Tabs */}
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

      {/* Contenido del panel */}
      <div className="p-6">
        {/* Tab de Texto */}
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
              El sistema detectará automáticamente nombres, emails, teléfonos y otros datos personales
            </div>
          </div>
        )}

        {/* Tab de Archivo */}
        {activeTab === 'file' && (
          <div className="space-y-4">
            <FileUpload
              accept=".pdf,.docx,.xlsx,.txt"
              onFileSelect={handleFileUpload}
              disabled={isDisabled}
              selectedFile={state.inputFile}
            />
            <div className="text-sm text-gray-600">
              Formatos soportados: PDF, Word (.docx), Excel (.xlsx), Texto (.txt)
            </div>
          </div>
        )}

        {/* Tab de Imagen */}
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
              El sistema detectará y anonimizará caras y matrículas en la imagen
            </div>
          </div>
        )}

        {/* Botón de envío */}
        <div className="mt-6 flex justify-end">
          <Button
            onClick={handleSubmit}
            disabled={isDisabled || !hasContent}
            loading={state.isLoading}
            className="px-8 py-3"
          >
            <Send className="w-4 h-4 mr-2" />
            {state.isLoading ? 'Procesando...' : 'Iniciar Anonimización'}
          </Button>
        </div>

        {/* Mostrar error si existe */}
        {state.error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
            <span className="text-red-700 text-sm">{state.error}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default InputPanel;