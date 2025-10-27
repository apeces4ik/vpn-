import React, { useState, useEffect } from 'react';
import './TypingEffect.css';

const TypingEffect = ({ 
  text, 
  delay = 150, 
  startDelay = 0, 
  className = '',
  splitAt = null,
  firstPartClassName = '',
  secondPartClassName = ''
}) => {
  const [displayedText, setDisplayedText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showCursor, setShowCursor] = useState(true);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    if (startDelay > 0 && !started) {
      const startTimeout = setTimeout(() => {
        setStarted(true);
      }, startDelay);
      return () => clearTimeout(startTimeout);
    } else {
      setStarted(true);
    }
  }, [startDelay, started]);

  useEffect(() => {
    if (!started) return;

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
  }, [currentIndex, text, delay, started]);

  // If splitAt is provided, split the text and apply different styles
  if (splitAt !== null && displayedText.length > 0) {
    const firstPart = displayedText.slice(0, splitAt);
    const secondPart = displayedText.slice(splitAt);
    
    return (
      <span className={`typing-effect ${className}`}>
        <span className={firstPartClassName}>{firstPart}</span>
        {secondPart && (
          <>
            <br />
            <span className={secondPartClassName}>{secondPart}</span>
          </>
        )}
        {showCursor && <span className="typing-cursor">|</span>}
      </span>
    );
  }

  return (
    <span className={`typing-effect ${className}`}>
      {displayedText}
      {showCursor && <span className="typing-cursor">|</span>}
    </span>
  );
};

export default TypingEffect;
