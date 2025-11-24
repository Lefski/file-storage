import React from 'react'
import './Header.css'
import Logo from '../ui_components/logo/Logo'
import Button from '../ui_components/button/Button'
import { useNavigate } from 'react-router-dom';


export default function Header() {
  const navigate = useNavigate();
  async function handleLogout(e) {
  }
  
  return (
    <header className="header">
      <Logo></Logo>
      
      <div className='user-container'>
        <span className='username'>Пользователь</span>
        <Button type='button' onClick={handleLogout}>Выйти</Button>
      </div>
    </header>
  )
}
