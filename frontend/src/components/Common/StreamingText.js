import React, { useState, useEffect } from 'react';

const StreamingText = ({ text, speed = 20 }) => {
  const [displayedText, setDisplayedText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (currentIndex < text.length) {
      const timeout = setTimeout(() => {
        setDisplayedText(text.slice(0, currentIndex + 1));
        setCurrentIndex(currentIndex + 1);
      }, speed);

      return () => clearTimeout(timeout);
    }
  }, [text, currentIndex, speed]);

  useEffect(() => {
    // Reset cuando cambia el texto
    setCurrentIndex(0);
    setDisplayedText('');
  }, [text]);

  return (
    <div className="text-sm text-gray-700">
      <span className="whitespace-pre-wrap">{displayedText}</span>
      {currentIndex < text.length && (
        <span className="inline-block w-2 h-5 bg-brand-primary animate-pulse ml-1"></span>
      )}
    </div>
  );
};

export default StreamingText;