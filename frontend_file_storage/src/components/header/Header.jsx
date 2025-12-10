import React, { useState, useEffect } from 'react'
import './Header.css'
import Logo from '../ui_components/logo/Logo'
import Button from '../ui_components/button/Button'
import { useNavigate } from 'react-router-dom';
import { getUserData, logout } from '../../api/services';


export default function Header() {
  const [username, setUsername] = useState("");
  const navigate = useNavigate();
  async function handleLogout() {
    try {
      await logout();
      navigate("/login");
    }
    catch (err) {
      console.error("Ошибка API:", err);
    }
  }

  useEffect(() => {
    async function fetchUser() {
      try {
        const user = await getUserData();   // ожидаем данные
        setUsername(user.data.username);         // сохраняем имя
      } catch (err) {
        console.error(err);
      }
    }

    fetchUser();
  }, []);

  return (
    <header className="header">
      <Logo></Logo>
      
      <div className='user-container'>
        <span className='username'>Здравствуйте, {username}</span>
        <Button type='button' onClick={handleLogout}>Выйти</Button>
      </div>
    </header>
  )
}
