import React, { useRef, useState } from 'react';
import { Upload, X, File } from 'lucide-react';
import { cn } from '../../utils/cn';

const FileUpload = ({
  accept,
  onFileSelect,
  disabled = false,
  selectedFile = null,
  icon: Icon = Upload,
  text = "Seleccionar archivo o arrastrar aquí",
  className = ''
}) => {
  const fileInputRef = useRef(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFileSelect = (file) => {
    if (file && onFileSelect) {
      onFileSelect(file);
    }
  };

  const handleInputChange = (e) => {
    const file = e.target.files[0];
    handleFileSelect(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    if (!disabled) {
      setIsDragOver(true);
    }
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    
    if (!disabled) {
      const file = e.dataTransfer.files[0];
      handleFileSelect(file);
    }
  };

  const handleClick = () => {
    if (!disabled && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleRemoveFile = (e) => {
    e.stopPropagation();
    if (onFileSelect) {
      onFileSelect(null);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className={cn('relative', className)}>
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        onChange={handleInputChange}
        disabled={disabled}
        className="hidden"
      />
      
      <div
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          'border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-all duration-200',
          {
            'border-brand-primary bg-brand-light bg-opacity-20': isDragOver && !disabled,
            'border-gray-300 hover:border-brand-primary hover:bg-gray-50': !isDragOver && !disabled,
            'border-gray-200 bg-gray-50 cursor-not-allowed': disabled,
          }
        )}
      >
        {selectedFile ? (
          <div className="flex items-center justify-between p-3 bg-white rounded border">
            <div className="flex items-center space-x-3">
              <File className="w-5 h-5 text-brand-primary" />
              <div className="text-left">
                <p className="text-sm font-medium text-gray-900 truncate max-w-48">
                  {selectedFile.name}
                </p>
                <p className="text-xs text-gray-500">
                  {formatFileSize(selectedFile.size)}
                </p>
              </div>
            </div>
            <button
              onClick={handleRemoveFile}
              disabled={disabled}
              className="p-1 rounded-full hover:bg-red-100 text-gray-400 hover:text-red-500 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <Icon className={cn(
              'w-8 h-8 mx-auto',
              disabled ? 'text-gray-400' : 'text-brand-primary'
            )} />
            <p className={cn(
              'text-sm font-medium',
              disabled ? 'text-gray-400' : 'text-gray-700'
            )}>
              {text}
            </p>
            {accept && (
              <p className="text-xs text-gray-500">
                Tipos permitidos: {accept.replace(/\./g, '').toUpperCase()}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default FileUpload;