import React from 'react';

interface EthereumIconProps {
  className?: string;
  size?: number;
}

const EthereumIcon: React.FC<EthereumIconProps> = ({ className = "", size = 24 }) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <path
        d="M12 2L5.5 12.5L12 16L18.5 12.5L12 2Z"
        fill="#627EEA"
        fillOpacity="0.8"
      />
      <path
        d="M12 16L5.5 12.5L12 22L18.5 12.5L12 16Z"
        fill="#627EEA"
        fillOpacity="0.6"
      />
    </svg>
  );
};

export default EthereumIcon; 