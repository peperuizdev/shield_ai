import React from 'react';
import InputPanel from '../Panels/InputPanel';
import ProcessingPanels from '../Panels/ProcessingPanels';
import { useApp } from '../../contexts/AppContext';

const MainContainer = () => {
  const { state } = useApp();
  
  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="space-y-8">
        
        <section className="animate-fade-in">
          <InputPanel />
        </section>

        {(state.anonymizedText || state.modelResponse || state.finalResponse || state.isStreaming) && (
          <section className="animate-slide-in">
            <ProcessingPanels />
          </section>
        )}

        <section className="text-center py-8">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-scalian-dark mb-2">
              ¿Cómo funciona Shield AI?
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
              <div className="text-center">
                <div className="w-12 h-12 bg-brand-primary bg-opacity-10 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-brand-primary font-bold">1</span>
                </div>
                <h4 className="font-medium text-brand-dark mb-2">Detección</h4>
                <p className="text-sm text-gray-600">
                  Identifica automáticamente datos personales (PII) en tu texto o imagen
                </p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 bg-brand-primary bg-opacity-10 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-brand-primary font-bold">2</span>
                </div>
                <h4 className="font-medium text-brand-dark mb-2">Anonimización</h4>
                <p className="text-sm text-gray-600">
                  Reemplaza los datos sensibles con información sintética realista
                </p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 bg-brand-primary bg-opacity-10 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-brand-primary font-bold">3</span>
                </div>
                <h4 className="font-medium text-brand-dark mb-2">Restauración</h4>
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