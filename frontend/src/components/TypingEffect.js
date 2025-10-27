import React, { useState, useEffect } from 'react';
import './TypingEffect.css';

const TypingEffect = ({ text, delay = 100, className = '' }) => {
  const [displayedText, setDisplayedText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (currentIndex < text.length) {
      const timeout = setTimeout(() => {
        setDisplayedText(prev => prev + text[currentIndex]);
        setCurrentIndex(prev => prev + 1);
      }, delay);

      return () => clearTimeout(timeout);
    }
  }, [currentIndex, text, delay]);

  return (
    <span className={`typing-effect ${className}`}>
      {displayedText}
      {currentIndex < text.length && <span className="typing-cursor">|</span>}
    </span>
  );
};

export default TypingEffect;
