import './Navbar.css'
import SearchComponent from '../ui_components/search-bar/searchComponent'
export default function Navbar() {
  return (
    <nav class="navbar">
      <h1>Файлы</h1>
      <SearchComponent></SearchComponent>
    </nav>
  )
}
