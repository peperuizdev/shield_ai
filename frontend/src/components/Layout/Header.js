import React from 'react';
import { Shield, Brain, Lock } from 'lucide-react';

const Header = () => {
  return (
    <header className="bg-white shadow-brand border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-4">
          {/* Logo y título */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <div className="relative">
                <Shield className="w-8 h-8 text-brand-primary" />
                <div className="absolute inset-0 w-8 h-8 text-brand-accent opacity-30 animate-pulse-slow">
                  <Brain className="w-8 h-8" />
                </div>
              </div>
              <div>
                <h1 className="text-xl font-bold text-brand-dark">
                  Shield AI
                </h1>
                <p className="text-xs text-gray-500 font-medium">
                  Sistema de Anonimización Inteligente
                </p>
              </div>
            </div>
          </div>

          {/* Información de seguridad */}
          <div className="flex items-center space-x-2 text-sm text-gray-600">
            <Lock className="w-4 h-4 text-brand-success" />
            <span className="hidden sm:inline">Conexión Segura</span>
            <div className="w-2 h-2 bg-brand-success rounded-full animate-pulse"></div>
          </div>
        </div>

        {/* Breadcrumb / Descripción */}
        <div className="pb-4">
          <p className="text-sm text-gray-600 leading-relaxed">
            Sistema inteligente para la anonimización de datos personales en texto e imágenes, 
            garantizando la privacidad en modelos de IA generativa.
          </p>
        </div>
      </div>
    </header>
  );
};

export default Header;