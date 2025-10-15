import React from 'react';
import InputPanel from '../Panels/InputPanel';
import ProcessingPanels from '../Panels/ProcessingPanels';
import ImageProcessingPanels from '../Panels/ImageProcessingPanels';
import { useApp } from '../../contexts/AppContext';

const MainContainer = () => {
  const { state } = useApp();
  
  return (
    <main className="px-4 py-8 mx-auto max-w-7xl sm:px-6 lg:px-8">
      <div className="space-y-8">
        
        <section className="animate-fade-in">
          <InputPanel />
        </section>

        {(state.anonymizedText || state.modelResponse || state.finalResponse || state.isStreaming) && (
          <section className="animate-slide-in">
            <ProcessingPanels />
          </section>
        )}

        {(state.anonymizedImage || state.isProcessingImage || state.originalImagePreview) && (
          <section className="animate-slide-in">
            <ImageProcessingPanels />
          </section>
        )}

        <section className="py-8 text-center">
          <div className="p-6 bg-white border border-gray-200 shadow-sm rounded-xl">
            <h3 className="mb-2 text-lg font-semibold text-scalian-dark">
              ¿Cómo funciona Shield AI?
            </h3>
            <div className="grid grid-cols-1 gap-6 mt-6 md:grid-cols-3">
              <div className="text-center">
                <div className="flex items-center justify-center w-12 h-12 mx-auto mb-3 rounded-full bg-brand-primary bg-opacity-10">
                  <span className="font-bold text-brand-primary">1</span>
                </div>
                <h4 className="mb-2 font-medium text-brand-dark">Detección</h4>
                <p className="text-sm text-gray-600">
                  Identifica automáticamente datos personales (PII) en tu texto o imagen
                </p>
              </div>
              <div className="text-center">
                <div className="flex items-center justify-center w-12 h-12 mx-auto mb-3 rounded-full bg-brand-primary bg-opacity-10">
                  <span className="font-bold text-brand-primary">2</span>
                </div>
                <h4 className="mb-2 font-medium text-brand-dark">Anonimización</h4>
                <p className="text-sm text-gray-600">
                  Reemplaza los datos sensibles con información sintética realista
                </p>
              </div>
              <div className="text-center">
                <div className="flex items-center justify-center w-12 h-12 mx-auto mb-3 rounded-full bg-brand-primary bg-opacity-10">
                  <span className="font-bold text-brand-primary">3</span>
                </div>
                <h4 className="mb-2 font-medium text-brand-dark">Restauración</h4>
                <p className="text-sm text-gray-600">
                  Devuelve los datos originales en la respuesta del modelo
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
};

export default MainContainer;