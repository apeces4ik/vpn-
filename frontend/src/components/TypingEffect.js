import React, { useState, useEffect } from 'react';
import './TypingEffect.css';

const TypingEffect = ({ text, delay = 150, className = '' }) => {
  const [displayedText, setDisplayedText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showCursor, setShowCursor] = useState(true);

  useEffect(() => {
    if (currentIndex < text.length) {
      const timeout = setTimeout(() => {
        setDisplayedText(prev => prev + text[currentIndex]);
        setCurrentIndex(prev => prev + 1);
      }, delay);

      return () => clearTimeout(timeout);
    } else {
      // Blink cursor when done typing
      const cursorInterval = setInterval(() => {
        setShowCursor(prev => !prev);
      }, 530);
      return () => clearInterval(cursorInterval);
    }
  }, [currentIndex, text, delay]);

  return (
    <span className={`typing-effect ${className}`}>
      {displayedText}
      {showCursor && <span className="typing-cursor">|</span>}
    </span>
  );
};

export default TypingEffect;
