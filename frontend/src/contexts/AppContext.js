import React, { createContext, useContext, useReducer } from 'react';

const initialState = {
  isLoading: false,
  error: null,
  
  // Estados del proceso de anonimización
  inputText: '',
  inputFile: null,
  inputImage: null,
  
  // Estados de los paneles
  anonymizedText: '',
  modelResponse: '',
  finalResponse: '',
  
  // Estados de streaming
  isStreaming: false,
  streamingText: '',
  
  // Estado de procesamiento de documentos
  isProcessingDocument: false,
  
  apiEndpoint: process.env.REACT_APP_API_ENDPOINT || 'http://localhost:8000',
  sessionId: null
};

const actionTypes = {
  SET_LOADING: 'SET_LOADING',
  SET_ERROR: 'SET_ERROR',
  CLEAR_ERROR: 'CLEAR_ERROR',
  
  SET_INPUT_TEXT: 'SET_INPUT_TEXT',
  SET_INPUT_FILE: 'SET_INPUT_FILE',
  SET_INPUT_IMAGE: 'SET_INPUT_IMAGE',
  
  SET_ANONYMIZED_TEXT: 'SET_ANONYMIZED_TEXT',
  SET_MODEL_RESPONSE: 'SET_MODEL_RESPONSE',
  SET_FINAL_RESPONSE: 'SET_FINAL_RESPONSE',
  
  START_STREAMING: 'START_STREAMING',
  STOP_STREAMING: 'STOP_STREAMING',
  UPDATE_STREAMING_TEXT: 'UPDATE_STREAMING_TEXT',
  
  SET_PROCESSING_DOCUMENT: 'SET_PROCESSING_DOCUMENT',
  
  SET_SESSION_ID: 'SET_SESSION_ID',
  RESET_PROCESS: 'RESET_PROCESS'
};

function appReducer(state, action) {
  switch (action.type) {
    case actionTypes.SET_LOADING:
      return { ...state, isLoading: action.payload };
    
    case actionTypes.SET_ERROR:
      return { ...state, error: action.payload, isLoading: false };
    
    case actionTypes.CLEAR_ERROR:
      return { ...state, error: null };
    
    case actionTypes.SET_INPUT_TEXT:
      return { ...state, inputText: action.payload };
    
    case actionTypes.SET_INPUT_FILE:
      return { ...state, inputFile: action.payload };
    
    case actionTypes.SET_INPUT_IMAGE:
      return { ...state, inputImage: action.payload };
    
    case actionTypes.SET_ANONYMIZED_TEXT:
      return { ...state, anonymizedText: action.payload };
    
    case actionTypes.SET_MODEL_RESPONSE:
      return { ...state, modelResponse: action.payload };
    
    case actionTypes.SET_FINAL_RESPONSE:
      return { ...state, finalResponse: action.payload };
    
    case actionTypes.START_STREAMING:
      return { ...state, isStreaming: true, streamingText: '' };
    
    case actionTypes.STOP_STREAMING:
      return { ...state, isStreaming: false };
    
    case actionTypes.UPDATE_STREAMING_TEXT:
      return { ...state, streamingText: action.payload };
    
    case actionTypes.SET_PROCESSING_DOCUMENT:
      return { ...state, isProcessingDocument: action.payload };
    
    case actionTypes.SET_SESSION_ID:
      return { ...state, sessionId: action.payload };
    
    case actionTypes.RESET_PROCESS:
      return {
        ...state,
        anonymizedText: '',
        modelResponse: '',
        finalResponse: '',
        streamingText: '',
        isStreaming: false,
        isProcessingDocument: false,
        error: null
      };
    
    default:
      return state;
  }
}

const AppContext = createContext();

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  const actions = {
    setLoading: (loading) => dispatch({ type: actionTypes.SET_LOADING, payload: loading }),
    setError: (error) => dispatch({ type: actionTypes.SET_ERROR, payload: error }),
    clearError: () => dispatch({ type: actionTypes.CLEAR_ERROR }),
    
    setInputText: (text) => dispatch({ type: actionTypes.SET_INPUT_TEXT, payload: text }),
    setInputFile: (file) => dispatch({ type: actionTypes.SET_INPUT_FILE, payload: file }),
    setInputImage: (image) => dispatch({ type: actionTypes.SET_INPUT_IMAGE, payload: image }),
    
    setAnonymizedText: (text) => dispatch({ type: actionTypes.SET_ANONYMIZED_TEXT, payload: text }),
    setModelResponse: (response) => dispatch({ type: actionTypes.SET_MODEL_RESPONSE, payload: response }),
    setFinalResponse: (response) => dispatch({ type: actionTypes.SET_FINAL_RESPONSE, payload: response }),
    
    startStreaming: () => dispatch({ type: actionTypes.START_STREAMING }),
    stopStreaming: () => dispatch({ type: actionTypes.STOP_STREAMING }),
    updateStreamingText: (text) => dispatch({ type: actionTypes.UPDATE_STREAMING_TEXT, payload: text }),
    
    setProcessingDocument: (processing) => dispatch({ type: actionTypes.SET_PROCESSING_DOCUMENT, payload: processing }),
    
    setSessionId: (id) => dispatch({ type: actionTypes.SET_SESSION_ID, payload: id }),
    resetProcess: () => dispatch({ type: actionTypes.RESET_PROCESS })
  };

  return (
    <AppContext.Provider value={{ state, actions }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp debe ser usado dentro de AppProvider');
  }
  return context;
}