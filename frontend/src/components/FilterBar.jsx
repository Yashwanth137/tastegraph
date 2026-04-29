import { useState } from 'react'

const GENRES = [
  "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary",
  "Drama", "Family", "Fantasy", "History", "Horror", "Music", "Mystery",
  "Romance", "Science Fiction", "Thriller", "War", "Western"
]

export default function FilterBar({ onFilterChange }) {
  const [selectedGenre, setSelectedGenre] = useState('')
  const [minYear, setMinYear] = useState('')
  const [minRating, setMinRating] = useState('')

  const handleApply = () => {
    onFilterChange({
      genre_filter: selectedGenre ? [selectedGenre] : null,
      min_year: minYear ? parseInt(minYear) : null,
      min_rating: minRating ? parseFloat(minRating) : null,
    })
  }

  const handleReset = () => {
    setSelectedGenre('')
    setMinYear('')
    setMinRating('')
    onFilterChange({ genre_filter: null, min_year: null, min_rating: null })
  }

  return (
    <div className="glass-panel p-4 mb-8 flex flex-col md:flex-row gap-4 items-center animate-slide-up">
      <div className="w-full md:w-auto flex-1">
        <select 
          value={selectedGenre}
          onChange={(e) => setSelectedGenre(e.target.value)}
          className="input-field appearance-none cursor-pointer"
        >
          <option value="">All Genres</option>
          {GENRES.map(g => (
            <option key={g} value={g}>{g}</option>
          ))}
        </select>
      </div>

      <div className="w-full md:w-auto flex-1">
        <select 
          value={minYear}
          onChange={(e) => setMinYear(e.target.value)}
          className="input-field appearance-none cursor-pointer"
        >
          <option value="">Any Year</option>
          <option value="2020">2020 & Newer</option>
          <option value="2010">2010 & Newer</option>
          <option value="2000">2000 & Newer</option>
          <option value="1990">1990 & Newer</option>
        </select>
      </div>

      <div className="w-full md:w-auto flex-1">
        <select 
          value={minRating}
          onChange={(e) => setMinRating(e.target.value)}
          className="input-field appearance-none cursor-pointer"
        >
          <option value="">Any Rating</option>
          <option value="8.0">8.0+ ⭐</option>
          <option value="7.0">7.0+ ⭐</option>
          <option value="6.0">6.0+ ⭐</option>
        </select>
      </div>

      <div className="w-full md:w-auto flex gap-2">
        <button onClick={handleApply} className="btn-primary flex-1 md:flex-none">
          Apply Filters
        </button>
        <button onClick={handleReset} className="btn-secondary px-3" title="Reset Filters">
          ↺
        </button>
      </div>
    </div>
  )
}
