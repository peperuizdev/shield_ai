# Shield AI - Frontend

## Características

- **Interfaz moderna y responsive** diseñada con React y Tailwind CSS
- **Tres paneles de visualización** para mostrar el proceso completo de anonimización
- **Soporte para múltiples tipos de entrada**: texto, archivos PDF/Word/Excel e imágenes
- **Streaming en tiempo real** de las respuestas del modelo de IA
- **Manejo robusto de estados** con Context API de React
- **Gestión de errores** con Error Boundary
- **Conexión HTTP optimizada** con Axios
- **Estética corporativa**

## Arquitectura

```
src/
├── components/           # Componentes React
│   ├── Common/          # Componentes reutilizables
│   │   ├── Button.js
│   │   ├── TextArea.js
│   │   ├── FileUpload.js
│   │   ├── StreamingText.js
│   │   └── ErrorBoundary.js
│   ├── Layout/          # Componentes de layout
│   │   ├── Header.js
│   │   ├── MainContainer.js
│   │   └── Footer.js
│   └── Panels/          # Paneles principales
│       ├── InputPanel.js
│       └── ProcessingPanels.js
├── contexts/            # Context para estados globales
│   └── AppContext.js
├── services/            # Servicios para API
│   └── anonymizationService.js
├── utils/               # Utilidades
│   └── cn.js
├── App.js               # Componente principal
├── App.css              # Estilos globales
└── index.js             # Punto de entrada
```

## 🛠️ Tecnologías Utilizadas

- **React 18** - Framework principal
- **Tailwind CSS 3** - Framework de estilos
- **Axios** - Cliente HTTP
- **Lucide React** - Iconos
- **Context API** - Manejo de estados
- **Docker** - Contenerización
- **Nginx** - Servidor web de producción

## 📋 Requisitos Previos

- Node.js 18 o superior
- npm o yarn
- Docker (opcional, para despliegue)

## 🚀 Instalación y Configuración

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd shield-ai-frontend
```

2. **Instalar dependencias**
```bash
npm install
```

3. **Configurar variables de entorno**
```bash
cp .env.example .env
```

Editar `.env` con los valores apropiados:
```env
REACT_APP_API_ENDPOINT=http://localhost:8000
REACT_APP_APP_NAME=Shield AI
REACT_APP_VERSION=1.0.0
```

4. **Iniciar en modo desarrollo**
```bash
npm start
```

La aplicación estará disponible en `http://localhost:3000`

## 🐳 Despliegue con Docker

1. **Construir la imagen**
```bash
docker build -t shield-ai-frontend .
```

2. **Ejecutar el contenedor**
```bash
docker run -p 80:80 shield-ai-frontend
```

## 🧪 Comandos Disponibles

- `npm start` - Inicia el servidor de desarrollo
- `npm build` - Construye la aplicación para producción
- `npm test` - Ejecuta los tests
- `npm run eject` - Eyecta la configuración de Create React App

## 📱 Funcionalidades Principales

### Panel de Entrada
- **Entrada de texto**: Área para escribir consultas con datos personales
- **Carga de archivos**: Soporte para PDF, Word y Excel (opcional)
- **Carga de imágenes**: Procesamiento de imágenes con detección facial y matrículas (opcional)

### Paneles de Procesamiento

1. **Panel de Datos Anonimizados**
   - Muestra el texto con PII reemplazada por datos sintéticos
   - Opciones para copiar y descargar

2. **Panel de Respuesta del Modelo**
   - Visualización en streaming de la respuesta de IA
   - Indicadores de estado en tiempo real

3. **Panel de Respuesta Final**
   - Texto con datos originales restaurados
   - Confirmación de proceso completado

## 🛡️ Seguridad

- Validación de tipos de archivo en cliente
- Sanitización de entrada de usuario
- Headers de seguridad en Nginx
- Manejo seguro de sesiones temporales

## 🔄 Manejo de Estados

La aplicación utiliza un Context Provider centralizado que gestiona:

- Estados de carga y error
- Datos de entrada (texto, archivo, imagen)
- Respuestas de los tres paneles
- Control de streaming
- Información de sesión

## 📊 Monitoreo y Logs

**El servicio incluye:**

- Logging de errores en consola
- Interceptors de Axios para manejo de errores HTTP
- Health checks para verificar conectividad con backend

## 🤝 Contribución

1. Fork del proyecto
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit de cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## 📄 Licencia

Este proyecto es parte del sistema Shield AI.
