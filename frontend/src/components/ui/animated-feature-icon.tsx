"use client";

import React, { useState, useEffect } from 'react';
import { cn } from '@/lib/utils'; // Assuming you have a cn utility

interface AnimatedFeatureIconProps {
  IconComponent: React.ElementType; // To pass Lucide icons like Wallet, Shield, Zap
  iconSizeClassName?: string;
  containerSizeClassName?: string;
}

const AnimatedFeatureIcon: React.FC<AnimatedFeatureIconProps> = ({
  IconComponent,
  iconSizeClassName = 'h-8 w-8',
  containerSizeClassName = 'w-16 h-16',
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const [isExploding, setIsExploding] = useState(false);
  const [iconColor, setIconColor] = useState('text-white'); // Initial color white

  useEffect(() => {
    let fillTimeout: NodeJS.Timeout;
    let explodeTimeout: NodeJS.Timeout;

    if (isHovered) {
      // Start fill effect (color change)
      setIconColor('text-green-400'); // Main theme green

      // Schedule explosion after a short delay (simulates fill completion)
      fillTimeout = setTimeout(() => {
        setIsExploding(true);
        // Reset explosion after animation duration
        explodeTimeout = setTimeout(() => {
          setIsExploding(false);
        }, 300); // Corresponds to animate-icon-explode duration (0.3s)
      }, 100); // Delay before explosion starts (ms)
    } else {
      setIconColor('text-white');
      setIsExploding(false); // Ensure explosion stops if unhovered quickly
    }

    return () => {
      clearTimeout(fillTimeout);
      clearTimeout(explodeTimeout);
    };
  }, [isHovered]);

  return (
    <div
      className={cn(
        containerSizeClassName,
        'rounded-full flex items-center justify-center mb-8 group-hover:scale-110 transition-all duration-300',
        'bg-green-700/30 group-hover:bg-green-600/40', // Existing container style
        'relative overflow-visible' // Added for potential pseudo-element effects if needed later
      )}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <IconComponent
        className={cn(
          iconSizeClassName,
          iconColor,
          'transition-colors duration-150 ease-in-out', // Color transition for the icon
          { 'animate-icon-explode': isExploding }
        )}
      />
    </div>
  );
};

export { AnimatedFeatureIcon }; 