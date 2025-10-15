import React from 'react';
import { Image as ImageIcon, EyeOff, CheckCircle, Download, Loader2, X } from 'lucide-react';
import { useApp } from '../../contexts/AppContext';
import Button from '../Common/Button';

const ImageProcessingPanels = () => {
  const { state, actions } = useApp();

  const handleDownload = () => {
    if (!state.anonymizedImage) return;

    const link = document.createElement('a');
    link.href = state.anonymizedImage;
    link.download = `imagen-anonimizada-${Date.now()}.jpg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleClearImage = () => {
    actions.setInputImage(null);
    actions.setOriginalImagePreview(null);
    actions.setAnonymizedImage(null);
    actions.setImageDetectionInfo(null);
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      
      <div className="overflow-hidden bg-white border border-gray-200 rounded-xl shadow-brand">
        <div className="px-4 py-3 bg-gradient-to-r from-orange-500 to-orange-600">
          <h3 className="flex items-center space-x-2 text-sm font-semibold text-white">
            <ImageIcon className="w-4 h-4" />
            <span>Imagen Original</span>
          </h3>
          <p className="mt-1 text-xs text-orange-100">
            Imagen sin procesar
          </p>
        </div>
        
        <div className="p-4">
          {state.originalImagePreview ? (
            <div className="space-y-3">
              <div className="relative">
                <img 
                  src={state.originalImagePreview} 
                  alt="Original"
                  className="w-full border border-gray-200 rounded-lg"
                />
              </div>
              {state.inputImage && (
                <div className="flex items-center justify-between px-3 py-2 text-xs text-gray-600 rounded-lg bg-gray-50">
                  <span>{state.inputImage.name}</span>
                  <span>{(state.inputImage.size / 1024).toFixed(2)} KB</span>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-400">
              <div className="text-center">
                <ImageIcon className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Esperando imagen...</p>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="overflow-hidden bg-white border border-gray-200 rounded-xl shadow-brand">
        <div className="px-4 py-3 bg-gradient-to-r from-brand-primary to-brand-secondary">
          <h3 className="flex items-center space-x-2 text-sm font-semibold text-white">
            <EyeOff className="w-4 h-4" />
            <span>Imagen Anonimizada</span>
          </h3>
          <p className="mt-1 text-xs text-brand-light">
            Rostros y datos sensibles protegidos
          </p>
        </div>
        
        <div className="p-4">
          {state.isProcessingImage ? (
            <div className="flex items-center justify-center h-64 text-gray-400">
              <div className="text-center">
                <Loader2 className="w-8 h-8 mx-auto mb-2 animate-spin text-brand-primary" />
                <p className="text-sm text-brand-primary">Procesando imagen...</p>
              </div>
            </div>
          ) : state.anonymizedImage ? (
            <div className="space-y-3">
              <div className="relative">
                <img 
                  src={state.anonymizedImage} 
                  alt="Anonimizada"
                  className="w-full border border-gray-200 rounded-lg"
                />
              </div>
              
              {state.imageDetectionInfo && (
                <div className="p-3 text-xs rounded-lg bg-blue-50">
                  <div className="flex items-center mb-2 space-x-2 text-blue-800">
                    <CheckCircle className="w-4 h-4" />
                    <span className="font-medium">Detecciones realizadas:</span>
                  </div>
                  <div className="ml-6 space-y-1 text-blue-700">
                    <div>• Rostros: {state.imageDetectionInfo.faces || 0}</div>
                    <div>• Total: {state.imageDetectionInfo.total || 0}</div>
                  </div>
                </div>
              )}
              
              <div className="flex space-x-2">
                <Button
                  onClick={handleDownload}
                  size="sm"
                  className="flex-1"
                >
                  <Download className="w-3 h-3 mr-1" />
                  Descargar
                </Button>
                <Button
                  onClick={handleClearImage}
                  variant="outline"
                  size="sm"
                  className="flex-1"
                >
                  <X className="w-3 h-3 mr-1" />
                  Limpiar
                </Button>
              </div>
              
              <div className="flex items-center px-3 py-2 space-x-2 text-xs text-green-600 rounded-lg bg-green-50">
                <CheckCircle className="w-4 h-4" />
                <span>Imagen procesada correctamente</span>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-64 text-gray-400">
              <div className="text-center">
                <EyeOff className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Esperando resultado...</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ImageProcessingPanels;