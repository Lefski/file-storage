import React from 'react'
import { getUserData } from '../../api/services'
import Header from '../../components/header/header'
import Navbar from '../../components/navbar/navbar'
import Sidebar from '../../components/sidebar/sidebar'
import Board from '../../components/board/board'
import './Mainpage.css'
export default function Mainpage() {
  return (
    <>
        <Header/>
        <Navbar />
        <Sidebar />
        <button className='special' onClick={getUserData}>апи</button>
        <Board />
    </>
  )
}
