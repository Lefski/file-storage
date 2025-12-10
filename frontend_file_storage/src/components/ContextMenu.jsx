// ContextMenu.jsx
import React from "react";
import "./ContextMenu.css";

export default function ContextMenu({ visible, x, y, onClose }) {
  if (!visible) return null;

  return (
    <ul 
      className="context-menu"
      style={{ top: y, left: x }}
      onClick={onClose} // закрываем меню при выборе пункта
    >
      <li>Переименовать</li>
      <li>Удалить</li>
      <li>Скачать</li>
      <li>Подробная информация</li>
    </ul>
  );
}