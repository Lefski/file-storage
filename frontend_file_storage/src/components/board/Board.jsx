import React from "react";
import "./Board.css";

import FileIcon from "./File.png";
import ImageFileIcon from "./Image_File.png";
import FolderIcon from "./Folder.png";
import DocumentIcon from "./Document.png";

// Данные файлов
const files = [
  { id: 1, name: "Документ.pdf", type: "document" },
  { id: 2, name: "Фото.jpg", type: "image" },
  { id: 3, name: "Работа", type: "folder" },
  { id: 4, name: "Музыка.mp3", type: "file" },
];

// Функция для выбора иконки по типу
const getIcon = (type) => {
  switch(type) {
    case "folder": return FolderIcon;
    case "image": return ImageFileIcon;
    case "document": return DocumentIcon;
    case "file": return FileIcon;
    default: return FileIcon;
  }
}

export default function Board() {
  return (
    <div className="board">
      {files.map(file => (
        <div key={file.id} className="board-item">
          <img
            src={getIcon(file.type)}
            alt={file.type}
            className="file-icon"
          />
          <div className="file-name">
            {file.name}
          </div>
        </div>
      ))}
    </div>
  );
}