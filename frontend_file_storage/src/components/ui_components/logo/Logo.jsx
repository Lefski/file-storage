import React from 'react'
import './Logo.css'
import logo from './Logo.svg'
export default function Logo() {
  return (
    <div className='logo-container'>
        <img className='logo__image' src={logo}></img>
        <label className='logo__text'>FileStorage</label>
    </div>
  )
}
