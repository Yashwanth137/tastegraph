import { useState } from 'react'
import { PlusIcon, CheckIcon, StarIcon, EyeIcon } from '@heroicons/react/24/solid'
import toast from 'react-hot-toast'
import apiClient from '../api/client'

export default function MovieCard({ movie, onAction }) {
  const [loading, setLoading] = useState(false)
  const [inLibrary, setInLibrary] = useState(false)
  const [watched, setWatched] = useState(false)

  const handleLibraryAction = async (action, sentiment = null) => {
    setLoading(true)
    try {
      // Instead of relying purely on natural language here, we can construct a prompt
      // or use a direct REST endpoint if we added one. Since we added a PATCH /library/{movie_id}
      // and the prompt parser, let's use the natural language prompt parser for the "wow" factor,
      // or directly use the PATCH if the movie is already there. For simplicity and robustness on a specific card,
      // we'll use a direct prompt to the parser:
      
      const promptMap = {
        'watchlist': `Add "${movie.title}" to my watchlist`,
        'watched': `Mark "${movie.title}" as watched`,
      }

      await apiClient.post('/library/prompt', { prompt: promptMap[action] })
      
      if (action === 'watchlist') setInLibrary(true)
      if (action === 'watched') setWatched(true)
      
      toast.success(`Added ${movie.title} to ${action}`)
      if (onAction) onAction(movie.id, action)
    } catch (error) {
      toast.error('Failed to update library')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="glass-panel group relative overflow-hidden flex flex-col h-full animate-fade-in">
      {/* Poster */}
      <div className="relative aspect-[2/3] w-full overflow-hidden bg-surface">
        {movie.poster ? (
          <img 
            src={movie.poster} 
            alt={movie.title} 
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-muted">
            No Poster
          </div>
        )}
        
        {/* Similarity Badge */}
        {movie.similarity !== undefined && (
          <div className="absolute top-2 right-2 bg-background/80 backdrop-blur-md border border-white/10 px-2 py-1 rounded-md flex flex-col items-center shadow-lg">
            <span className="text-xs text-muted uppercase font-bold tracking-wider">Match</span>
            <span className="text-sm font-bold text-primary">{(movie.similarity * 100).toFixed(0)}%</span>
          </div>
        )}

        {/* Hover Overlay Actions */}
        <div className="absolute inset-0 bg-background/60 backdrop-blur-sm opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col items-center justify-center space-y-3 p-4">
          <button 
            onClick={() => handleLibraryAction('watchlist')}
            disabled={loading || inLibrary}
            className="w-full btn-primary py-2 flex items-center justify-center space-x-2"
          >
            {inLibrary ? <CheckIcon className="w-5 h-5" /> : <PlusIcon className="w-5 h-5" />}
            <span>{inLibrary ? 'In Watchlist' : 'Watchlist'}</span>
          </button>
          
          <button 
            onClick={() => handleLibraryAction('watched')}
            disabled={loading || watched}
            className="w-full btn-secondary py-2 flex items-center justify-center space-x-2"
          >
            {watched ? <CheckIcon className="w-5 h-5 text-secondary" /> : <EyeIcon className="w-5 h-5" />}
            <span>{watched ? 'Watched' : 'Mark Watched'}</span>
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 flex flex-col flex-grow">
        <h3 className="font-bold text-lg text-white line-clamp-1 mb-1" title={movie.title}>
          {movie.title}
        </h3>
        
        <div className="flex items-center space-x-2 mb-2 text-sm">
          <div className="flex items-center text-yellow-500">
            <StarIcon className="w-4 h-4 mr-1" />
            <span className="font-medium text-white">{movie.rating.toFixed(1)}</span>
          </div>
          <span className="text-muted">•</span>
          <span className="text-muted truncate">{movie.genres?.slice(0, 2).join(', ')}</span>
        </div>
        
        <p className="text-sm text-muted line-clamp-3 mt-auto">
          {movie.overview}
        </p>
      </div>
    </div>
  )
}
