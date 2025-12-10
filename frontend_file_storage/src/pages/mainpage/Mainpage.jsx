import React from 'react'
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
        <Board />
    </>
  )
}
