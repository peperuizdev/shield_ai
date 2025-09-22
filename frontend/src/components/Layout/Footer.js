import React from 'react';

const Footer = () => {
  return (
    <footer className="bg-white border-t border-gray-200 mt-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
          
          <div className="flex items-center space-x-4">
            <div className="text-sm text-gray-600">
              Shield AI
            </div>
          </div>

          <div className="flex items-center space-x-6 text-sm text-gray-600">
            <span className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span>Privacidad Garantizada</span>
            </span>
            <span>Versión 1.0.0</span>
            <span>© 2025 Shield AI</span>
          </div>
        </div>
        
        <div className="mt-4 pt-4 border-t border-gray-100">
          <p className="text-xs text-gray-500 text-center max-w-4xl mx-auto">
            Este sistema garantiza la privacidad de los datos mediante técnicas avanzadas de anonimización. 
            Los datos personales son procesados temporalmente y no se almacenan de forma permanente. 
            Para más información sobre el tratamiento de datos, consulta nuestra política de privacidad.
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;