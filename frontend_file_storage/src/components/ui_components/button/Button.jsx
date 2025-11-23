import React from "react";
import "./Button.css";

export default function Button({
    children,
    type = "button",
    onClick,
    className = "",
    disabled = false
}) {
    return (
        <button
            type={type}
            onClick={onClick}
            disabled={disabled}
            className={`custom-button ${className}`}
        >
            {children}
        </button>
    );
}