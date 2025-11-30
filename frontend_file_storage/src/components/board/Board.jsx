import React, { useState } from "react";
import "./Board.css";
import FileIcon from "./File.png";
import ImageFileIcon from "./Image_File.png";
import FolderIcon from "./Folder.png";
import DocumentIcon from "./Document.png";
import ContextMenu from "../ContextMenu";

const files = [
  { id: 1, name: "Документ.pdf", type: "document", createdAt: "2025-11-25", time: "14:30", size: "1.2 MB" },
  { id: 2, name: "Фото.jpg", type: "image", createdAt: "2025-11-20", time: "09:15", size: "2.3 MB" },
  { id: 3, name: "Работа", type: "folder", createdAt: "2025-11-10", time: "11:00" },
  { id: 4, name: "Музыка.mp3", type: "file", createdAt: "2025-11-22", time: "18:45", size: "5.5 MB" },
];

const getIcon = (type) => {
  switch(type) {
    case "folder": return FolderIcon;
    case "image": return ImageFileIcon;
    case "document": return DocumentIcon;
    case "file": return FileIcon;
    default: return FileIcon;
  }
}

function FileGrid({ files }) {
  return (
    <div className="board grid-view">
      {files.map(file => (
        <div key={file.id} className="board-item">
          <img src={getIcon(file.type)} alt={file.type} className="file-icon" />
          <div className="file-name">{file.name}</div>
        </div>
      ))}
    </div>
  );
}

function FileList({ files }) {
  return (
    <div className="board list-view">
      {files.map(file => (
        <div key={file.id} className="board-item list-item">
          <img src={getIcon(file.type)} alt={file.type} className="file-icon" />
          <div className="file-name">{file.name}</div>
          <div className="file-info">
            <div>{file.createdAt}</div>
            <div>{file.time}</div>
            {file.type !== "folder" && <div>Размер: {file.size}</div>}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function Board() {
  const [view, setView] = useState("grid");
  const [contextMenu, setContextMenu] = useState({ visible: false, x: 0, y: 0 });

  const handleContextMenu = (e) => {
    e.preventDefault();
    setContextMenu({
      visible: true,
      x: e.pageX,
      y: e.pageY
    });
  };

  const handleClick = () => {
    if (contextMenu.visible) setContextMenu({ ...contextMenu, visible: false });
  };

  return (
    <div 
      onContextMenu={handleContextMenu} 
      onClick={handleClick}
      style={{ position: "relative" }}
    >
      <div className="view-toggle">
        <button onClick={() => setView("grid")}>Сетка</button>
        <button onClick={() => setView("list")}>Список</button>
      </div>

      {view === "grid" ? <FileGrid files={files} /> : <FileList files={files} />}

      <ContextMenu 
        visible={contextMenu.visible} 
        x={contextMenu.x} 
        y={contextMenu.y} 
        onClose={() => setContextMenu({ ...contextMenu, visible: false })}
      />
    </div>
  );
}
