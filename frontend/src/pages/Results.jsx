import { useState, useEffect, useCallback } from 'react'
import apiClient from '../api/client'
import useStore from '../store/useStore'
import MovieCard from '../components/MovieCard'
import FilterBar from '../components/FilterBar'
import PromptInput from '../components/PromptInput'
import { AdjustmentsHorizontalIcon, SparklesIcon } from '@heroicons/react/24/outline'

export default function Results() {
  const profile = useStore((state) => state.profile)
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showRefine, setShowRefine] = useState(false)
  
  // Filtering state
  const [filters, setFilters] = useState({
    genre_filter: null,
    min_year: null,
    min_rating: null,
  })

  const fetchRecommendations = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.post('/recommend', {
        limit: 24,
        ...filters
      })
      setRecommendations(response.data.recommendations)
    } catch (err) {
      if (err.response?.status === 404) {
        setError("You don't have a taste profile yet.")
      } else {
        setError("Failed to load recommendations.")
      }
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    fetchRecommendations()
  }, [fetchRecommendations, profile?.version]) // Refetch if profile version changes

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters)
  }

  const handleProfileUpdate = () => {
    setShowRefine(false)
    // The useEffect will trigger fetchRecommendations because the profile in store changes
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 text-center">
        <div className="glass-panel p-12 inline-block">
          <SparklesIcon className="w-16 h-16 text-primary mx-auto mb-4" />
          <h2 className="text-2xl font-bold mb-4">{error}</h2>
          <p className="text-muted mb-8">Tell us what you're in the mood for to get started.</p>
          <PromptInput onComplete={handleProfileUpdate} />
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Recommended for You</h1>
          {profile && (
            <p className="text-muted text-sm max-w-2xl">
              Based on: <span className="italic text-white/80">"{profile.prompt}"</span>
            </p>
          )}
        </div>
        
        <div className="flex gap-3">
          <button 
            onClick={() => setShowRefine(!showRefine)}
            className={`btn-secondary flex items-center space-x-2 ${showRefine ? 'bg-white/10 ring-2 ring-white/20' : ''}`}
          >
            <SparklesIcon className="w-5 h-5" />
            <span>Refine Taste</span>
          </button>
        </div>
      </div>

      {showRefine && (
        <div className="mb-8 animate-slide-up">
          <div className="glass-panel p-6 border-primary/30">
            <h3 className="text-lg font-bold mb-4 flex items-center text-primary">
              <SparklesIcon className="w-5 h-5 mr-2" />
              Evolve Your Taste Profile
            </h3>
            <PromptInput onComplete={handleProfileUpdate} />
          </div>
        </div>
      )}

      <FilterBar onFilterChange={handleFilterChange} />

      {loading ? (
        <div className="flex justify-center items-center py-32">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      ) : recommendations.length === 0 ? (
        <div className="text-center py-32 glass-panel">
          <h3 className="text-xl font-bold text-white mb-2">No matches found</h3>
          <p className="text-muted">Try adjusting your filters or writing a new prompt.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-6">
          {recommendations.map((movie) => (
            <MovieCard key={movie.id} movie={movie} />
          ))}
        </div>
      )}
    </div>
  )
}
