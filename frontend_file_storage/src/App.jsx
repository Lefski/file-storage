import { useState } from 'react'
import './App.css'
import Header from './components/header/header'
import Navbar from './components/navbar/navbar'
import Sidebar from './components/sidebar/sidebar'
import Board from './components/board/board'

function App() {
  const [count, setCount] = useState(0)

  return (
    <>
      <Header />
      <Navbar />
      <Sidebar />
      <Board />
    </>
  )
}

export default App
