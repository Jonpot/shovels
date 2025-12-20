import React from 'react';
import './Button.css';

const Button = ({ children, onClick, variant = 'primary', disabled = false, className = '' }) => {
    return (
        <button
            className={`shovels-button ${variant} ${className}`}
            onClick={onClick}
            disabled={disabled}
        >
            <span className="button-content">
                {children}
            </span>
        </button>
    );
};

export default Button;
