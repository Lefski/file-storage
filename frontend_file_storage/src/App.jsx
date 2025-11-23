import React, { useState, useEffect } from 'react';
import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom';
import api from './api/api';
import Login from './pages/login/login';
import Mainpage from './pages/mainpage/mainpage';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true); // пока проверяем токен

  // Проверка токена при загрузке приложения
  useEffect(() => {
    const token = localStorage.getItem("token");

    if (!token) {
      setLoading(false);
      return;
    }

    async function checkAuth() {
      try {
        // Подстрой под свой реальный эндпоинт проверки!
        const res = await api.get("/me");

        if (res.status === 200) {
          setIsAuthenticated(true);
        }
      } catch (e) {
        localStorage.removeItem("token");
        setIsAuthenticated(false);
      } finally {
        setLoading(false);
      }
    }

    checkAuth();
  }, []);

  // Пока проверяем токен — можно выводить "Loading..."
  if (loading) return <div>Loading...</div>;

  return (
    <BrowserRouter>
      <Routes>

        {/* Страница логина */}
        <Route 
          path="/login" 
          element={
            isAuthenticated 
              ? <Navigate to="/main" /> 
              : <Login onLogin={() => setIsAuthenticated(true)} />
          } 
        />

        {/* Главная защищённая страница */}
        <Route 
          path="/main" 
          element={
            //isAuthenticated 
            //  ? 
            <Mainpage /> 
            //  : <Navigate to="/login" />
          }
        />

        {/* Корень — ведёт либо на main, либо на login */}
        <Route 
          path="/" 
          element={
            isAuthenticated 
              ? <Navigate to="/main" /> 
              : <Navigate to="/login" />
          }
        />

        {/* Ловушка для неизвестных роутов */}
        <Route path="*" element={<Navigate to="/" />} />

      </Routes>
    </BrowserRouter>
  );
}

export default App;
