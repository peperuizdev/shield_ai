import React from 'react';
import { cn } from '../../utils/cn';

const TextArea = ({
  placeholder,
  value,
  onChange,
  disabled = false,
  rows = 4,
  className = '',
  ...props
}) => {
  const handleChange = (e) => {
    if (onChange) {
      onChange(e.target.value);
    }
  };

  return (
    <textarea
      placeholder={placeholder}
      value={value}
      onChange={handleChange}
      disabled={disabled}
      rows={rows}
      className={cn(
        'w-full px-4 py-3 border border-gray-300 rounded-lg text-sm',
        'focus:ring-2 focus:ring-brand-primary focus:border-brand-primary',
        'disabled:bg-gray-50 disabled:cursor-not-allowed',
        'placeholder-gray-500 resize-none',
        'transition-colors duration-200',
        className
      )}
      {...props}
    />
  );
};

export default TextArea;