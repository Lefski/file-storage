import React, { useState, useEffect } from 'react';
import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom';
import { getUserData } from './api/services';
import Login from './pages/login/login';
import Mainpage from './pages/mainpage/mainpage';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState("");

  
  async function checkAuth() {
    try {
      const res = await getUserData();

      if (res.status === 200) {
        console.log("Пользоветель найден!");
        setIsAuthenticated(true);
      }
    } catch (e) {
      console.log("Пользоветель НЕ найден!");
      setIsAuthenticated(false);  
    }
  }
  // Проверка токена при загрузке приложения
  useEffect(() => {
    checkAuth();
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route 
          path="/login" 
          element={<Login/>} 
        />

        <Route 
          path="/main" 
          element={!isAuthenticated ? <Mainpage/> : 
          <Navigate to = "/login"/>}
        />

        <Route 
          path="/" 
          element={<Navigate to="/login"/>}
        />

        <Route path="*" element={<Navigate to="/"/>} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
