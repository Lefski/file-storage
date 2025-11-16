import './searchComponent.css'
const SearchComponent = () => {
  return (
    <label class="search__container">
      <input
        class="search__input" 
        type="text" 
        placeholder="Поиск" 
      />
    </label>
  );
};

export default SearchComponent;