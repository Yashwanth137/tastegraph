import { useState, useEffect, useCallback } from 'react'
import apiClient from '../api/client'
import useStore from '../store/useStore'
import MovieCard from '../components/MovieCard'
import { SparklesIcon, DocumentArrowUpIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

export default function Library() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('watchlist') // watchlist | watched | liked
  const [prompt, setPrompt] = useState('')
  const [promptLoading, setPromptLoading] = useState(false)
  const [resolutionData, setResolutionData] = useState(null)
  
  const setProfile = useStore(state => state.setProfile)

  const fetchLibrary = useCallback(async () => {
    setLoading(true)
    try {
      let params = { per_page: 50 }
      if (activeTab === 'watchlist') params.status = 'watchlist'
      if (activeTab === 'watched') params.status = 'watched'
      if (activeTab === 'liked') {
        params.status = 'watched'
        params.sentiment = 'liked'
      }

      const response = await apiClient.get('/library', { params })
      setItems(response.data.items)
    } catch (error) {
      toast.error('Failed to load library')
    } finally {
      setLoading(false)
    }
  }, [activeTab])

  useEffect(() => {
    fetchLibrary()
  }, [fetchLibrary])

  const handlePromptSubmit = async (e) => {
    e.preventDefault()
    if (!prompt.trim()) return

    setPromptLoading(true)
    try {
      const response = await apiClient.post('/library/prompt', { prompt })
      setPrompt('')
      
      if (response.data.ambiguous_items?.length > 0) {
        setResolutionData(response.data.ambiguous_items)
      } else {
        toast.success(`Action applied: ${response.data.parsed_action}`)
        fetchLibrary() // Refresh list
        if (response.data.taste_updated) {
           // We could refetch the profile here if we want the UI to immediately reflect it
           const profResponse = await apiClient.get('/profile/me')
           setProfile(profResponse.data)
        }
      }
    } catch (error) {
      toast.error('Failed to process command')
    } finally {
      setPromptLoading(false)
    }
  }

  const handleResolve = async (movieId, inputTitle, candidates) => {
    try {
      const action = 'add_watchlist' // Simple fallback for now
      await apiClient.post('/library/resolve', {
        resolutions: [{ input_title: inputTitle, movie_id: movieId, action }]
      })
      toast.success('Movie resolved and added!')
      setResolutionData(null)
      fetchLibrary()
    } catch (error) {
      toast.error('Failed to resolve movie')
    }
  }

  // Handle file import
  const handleImport = async (e, source) => {
    const file = e.target.files[0]
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)
    formData.append('source', source)

    toast.loading(`Importing from ${source}...`, { id: 'import' })
    try {
      const res = await apiClient.post('/library/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      toast.success(`Import complete! Matched: ${res.data.matched}, Failed: ${res.data.failed}`, { id: 'import' })
      fetchLibrary()
    } catch (error) {
      toast.error('Import failed', { id: 'import' })
    }
    // reset file input
    e.target.value = null
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      
      {/* Header & Prompt Input */}
      <div className="mb-12">
        <h1 className="text-3xl font-bold tracking-tight text-white mb-6">Your Library</h1>
        
        <div className="glass-panel p-6 mb-6 relative overflow-hidden group border-primary/20 hover:border-primary/50 transition-colors">
          <div className="absolute -inset-1 bg-gradient-to-r from-primary to-secondary blur opacity-10 group-hover:opacity-20 transition duration-1000"></div>
          <div className="relative flex flex-col md:flex-row gap-4 items-start md:items-center">
            <div className="flex-1 w-full">
              <h3 className="text-lg font-bold text-white flex items-center mb-2">
                <SparklesIcon className="w-5 h-5 mr-2 text-primary" />
                Chat with your library
              </h3>
              <form onSubmit={handlePromptSubmit} className="flex gap-2">
                <input
                  type="text"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder='e.g., "Add Interstellar to my watchlist" or "I hated Tenet, remove it"'
                  className="input-field py-3"
                  disabled={promptLoading}
                />
                <button type="submit" disabled={promptLoading} className="btn-primary whitespace-nowrap">
                  {promptLoading ? 'Thinking...' : 'Execute'}
                </button>
              </form>
            </div>
          </div>
        </div>

        {/* Ambiguity Resolution UI */}
        {resolutionData && (
          <div className="glass-panel p-6 border-yellow-500/50 bg-yellow-500/10 mb-6">
            <h3 className="text-lg font-bold text-yellow-400 mb-4 flex items-center">
              We found multiple matches. Which one did you mean?
            </h3>
            {resolutionData.map((item, idx) => (
              <div key={idx} className="mb-4 last:mb-0">
                <p className="font-semibold text-white mb-2">"{item.input_title}"</p>
                <div className="flex gap-3 overflow-x-auto pb-2">
                  {item.candidates.map(candidate => (
                    <button
                      key={candidate.id}
                      onClick={() => handleResolve(candidate.id, item.input_title, item.candidates)}
                      className="btn-secondary whitespace-nowrap text-sm"
                    >
                      {candidate.title}
                    </button>
                  ))}
                  <button onClick={() => setResolutionData(null)} className="btn-secondary text-red-400 whitespace-nowrap text-sm">
                    Cancel
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Import tools */}
        <div className="flex gap-4 items-center text-sm">
          <span className="text-muted">Import from:</span>
          <label className="cursor-pointer flex items-center space-x-1 text-primary hover:text-primary/80 transition-colors">
            <DocumentArrowUpIcon className="w-4 h-4" />
            <span>Letterboxd</span>
            <input type="file" accept=".csv" className="hidden" onChange={(e) => handleImport(e, 'letterboxd')} />
          </label>
          <span className="text-white/20">|</span>
          <label className="cursor-pointer flex items-center space-x-1 text-yellow-500 hover:text-yellow-400 transition-colors">
            <DocumentArrowUpIcon className="w-4 h-4" />
            <span>IMDb</span>
            <input type="file" accept=".csv" className="hidden" onChange={(e) => handleImport(e, 'imdb')} />
          </label>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-1 border-b border-white/10 mb-8">
        {['watchlist', 'watched', 'liked'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`py-2 px-6 font-medium text-sm transition-colors relative ${
              activeTab === tab ? 'text-primary' : 'text-muted hover:text-white'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
            {activeTab === tab && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-t-full"></div>
            )}
          </button>
        ))}
      </div>

      {/* Grid */}
      {loading ? (
        <div className="flex justify-center items-center py-32">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-32 glass-panel">
          <h3 className="text-xl font-bold text-white mb-2">It's quiet here</h3>
          <p className="text-muted">No movies found in this section.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-6">
          {items.map((item) => (
            <div key={item.id} className="relative group">
               <MovieCard movie={item.movie} />
               {/* Quick status indicator overlay for library context */}
               <div className="absolute top-2 left-2 pointer-events-none">
                  {item.sentiment === 'liked' && <div className="bg-secondary/90 text-white p-1 rounded-full"><CheckCircleIcon className="w-4 h-4" /></div>}
                  {item.sentiment === 'disliked' && <div className="bg-red-500/90 text-white p-1 rounded-full"><XCircleIcon className="w-4 h-4" /></div>}
               </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
