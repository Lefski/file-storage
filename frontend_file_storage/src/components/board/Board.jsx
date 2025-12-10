import React, {useState, useEffect} from "react";
import "./Board.css";
import { getUserFiles } from "../../api/services";
import FileIcon from "./File.png";
import ImageFileIcon from "./Image_File.png";
import FolderIcon from "./Folder.png";
import DocumentIcon from "./Document.png";


const files = [
  { id: 1, name: "Документ.pdf", type: "document" },
  { id: 2, name: "Фото.jpg", type: "image" },
  { id: 3, name: "Работа", type: "folder" },
  { id: 4, name: "Музыка.mp3", type: "file" },
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


export default function Board() {
  const [userFiles, setUserFiles] = useState([]);
    useEffect(() => {
      async function fetchUserFiles() {
        try {
          const files = await getUserFiles();   // ожидаем данные
          setUserFiles(user.username);         // сохраняем имя
        } catch (err) {
          console.error(err);
        }
      }
  
      fetchUserFiles();
    }, []);

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