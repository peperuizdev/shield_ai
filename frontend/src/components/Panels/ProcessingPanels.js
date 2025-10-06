import React from 'react';
import { EyeOff, Bot, CheckCircle, Copy, Download, Zap } from 'lucide-react';
import { useApp } from '../../contexts/AppContext';
import Button from '../Common/Button';

const ProcessingPanels = () => {
  const { state } = useApp();

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const downloadText = (text, filename) => {
    const element = document.createElement('a');
    const file = new Blob([text], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = filename;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      {/* Panel 1: Datos Anonimizados */}
      <div className="bg-white rounded-xl shadow-brand border border-gray-200 overflow-hidden">
        <div className="bg-gradient-to-r from-orange-500 to-orange-600 px-4 py-3">
          <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
            <EyeOff className="w-4 h-4" />
            <span>Datos Anonimizados</span>
          </h3>
          <p className="text-orange-100 text-xs mt-1">
            Versión enviada a la IA
          </p>
        </div>
        
        <div className="p-4">
          {state.anonymizedText ? (
            <div className="space-y-3">
              <div className="bg-orange-50 rounded-lg p-3 text-sm font-mono text-gray-700 min-h-32 max-h-48 overflow-y-auto border-l-4 border-orange-400 whitespace-pre-wrap">
                {state.anonymizedText}
              </div>
              <div className="flex space-x-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => copyToClipboard(state.anonymizedText)}
                >
                  <Copy className="w-3 h-3 mr-1" />
                  Copiar
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => downloadText(state.anonymizedText, 'datos-anonimizados.txt')}
                >
                  <Download className="w-3 h-3 mr-1" />
                  Descargar
                </Button>
              </div>
              <div className="flex items-center space-x-2 text-xs text-orange-600 bg-orange-50 px-3 py-2 rounded-lg">
                <CheckCircle className="w-4 h-4" />
                <span>Datos personales protegidos</span>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-32 text-gray-400">
              <div className="text-center">
                <EyeOff className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Esperando datos para anonimizar...</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Panel 2: Respuesta Anónima */}
      <div className="bg-white rounded-xl shadow-brand border border-gray-200 overflow-hidden">
        <div className="bg-gradient-to-r from-brand-primary to-brand-secondary px-4 py-3">
          <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
            <Bot className="w-4 h-4" />
            <span>Respuesta del Modelo IA</span>
            {state.isStreaming && state.modelResponse && (
              <Zap className="w-3 h-3 animate-pulse text-yellow-300" />
            )}
          </h3>
          <p className="text-brand-light text-xs mt-1">
            Respuesta con datos anonimizados
          </p>
        </div>
        
        <div className="p-4">
          {state.isStreaming && !state.modelResponse ? (
            <div className="space-y-3">
              <div className="bg-gray-50 rounded-lg p-3 min-h-32 max-h-48 overflow-y-auto">
                <div className="flex items-center space-x-2 text-gray-500">
                  <Bot className="w-4 h-4 animate-pulse" />
                  <span className="text-sm">La IA está pensando...</span>
                </div>
              </div>
              <div className="flex items-center space-x-2 text-xs text-gray-500">
                <div className="animate-pulse w-2 h-2 bg-brand-primary rounded-full"></div>
                <span>Recibiendo respuesta...</span>
              </div>
            </div>
          ) : state.modelResponse ? (
            <div className="space-y-3">
              <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-700 min-h-32 max-h-48 overflow-y-auto whitespace-pre-wrap">
                {state.modelResponse}
              </div>
              <div className="flex space-x-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => copyToClipboard(state.modelResponse)}
                >
                  <Copy className="w-3 h-3 mr-1" />
                  Copiar
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => downloadText(state.modelResponse, 'respuesta-modelo.txt')}
                >
                  <Download className="w-3 h-3 mr-1" />
                  Descargar
                </Button>
              </div>
              {state.isStreaming ? (
                <div className="flex items-center space-x-2 text-xs text-blue-600 bg-blue-50 px-3 py-2 rounded-lg">
                  <div className="animate-pulse w-2 h-2 bg-blue-600 rounded-full"></div>
                  <span>Streaming en curso...</span>
                </div>
              ) : (
                <div className="flex items-center space-x-2 text-xs text-blue-600 bg-blue-50 px-3 py-2 rounded-lg">
                  <CheckCircle className="w-4 h-4" />
                  <span>Respuesta completada</span>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-32 text-gray-400">
              <div className="text-center">
                <Bot className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Esperando respuesta del modelo...</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Panel 3: Respuesta Desanonimizada*/}
      <div className="bg-white rounded-xl shadow-brand border border-gray-200 overflow-hidden">
        <div className="bg-gradient-to-r from-green-500 to-green-600 px-4 py-3">
          <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
            <CheckCircle className="w-4 h-4" />
            <span>Respuesta Final</span>
            {state.isStreaming && state.streamingText && (
              <Zap className="w-3 h-3 animate-pulse text-yellow-300" />
            )}
          </h3>
          <p className="text-green-100 text-xs mt-1">
            Datos restaurados para el usuario
          </p>
        </div>
        
        <div className="p-4">
          {state.isStreaming ? (
            <div className="space-y-3">
              <div className="bg-green-50 rounded-lg p-3 min-h-32 max-h-48 overflow-y-auto border-l-4 border-green-400">
                {state.streamingText ? (
                  <div className="text-sm text-gray-700 whitespace-pre-wrap">
                    {state.streamingText}
                  </div>
                ) : (
                  <div className="flex items-center space-x-2 text-green-600">
                    <CheckCircle className="w-4 h-4 animate-pulse" />
                    <span className="text-sm">Restaurando datos originales...</span>
                  </div>
                )}
              </div>
              <div className="flex items-center space-x-2 text-xs text-green-600 bg-green-50 px-3 py-2 rounded-lg">
                <div className="animate-pulse w-2 h-2 bg-green-600 rounded-full"></div>
                <span>Desanonimizando en tiempo real...</span>
              </div>
            </div>
          ) : state.finalResponse ? (
            <div className="space-y-3">
              <div className="bg-green-50 rounded-lg p-3 text-sm text-gray-700 min-h-32 max-h-48 overflow-y-auto whitespace-pre-wrap border-l-4 border-green-400">
                {state.finalResponse}
              </div>
              <div className="flex space-x-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => copyToClipboard(state.finalResponse)}
                >
                  <Copy className="w-3 h-3 mr-1" />
                  Copiar
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => downloadText(state.finalResponse, 'respuesta-final.txt')}
                >
                  <Download className="w-3 h-3 mr-1" />
                  Descargar
                </Button>
              </div>
              <div className="flex items-center space-x-2 text-xs text-green-600 bg-green-50 px-3 py-2 rounded-lg">
                <CheckCircle className="w-4 h-4" />
                <span>Proceso completado exitosamente</span>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-32 text-gray-400">
              <div className="text-center">
                <CheckCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Esperando respuesta final...</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProcessingPanels;