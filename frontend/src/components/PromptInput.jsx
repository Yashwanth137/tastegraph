import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import apiClient from '../api/client'
import useStore from '../store/useStore'
import { SparklesIcon } from '@heroicons/react/24/solid'

export default function PromptInput({ onComplete, className = '' }) {
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const setProfile = useStore((state) => state.setProfile)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!prompt.trim() || prompt.length < 10) {
      toast.error('Please enter a more descriptive prompt (at least 10 chars).')
      return
    }

    setLoading(true)
    try {
      const response = await apiClient.post('/profile/generate', { prompt })
      setProfile(response.data)
      toast.success('Taste profile generated!')
      if (onComplete) {
        onComplete(response.data)
      } else {
        navigate('/results')
      }
    } catch (error) {
      console.error(error)
      toast.error(error.response?.data?.detail || 'Failed to generate profile')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className={`w-full relative ${className}`}>
      <div className="relative group">
        <div className="absolute -inset-1 bg-gradient-to-r from-primary to-secondary rounded-xl blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200"></div>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g. I love slow-burn psychological thrillers with unreliable narrators and stunning cinematography..."
          className="relative w-full h-32 bg-surface border border-white/10 rounded-xl px-4 py-3 text-text placeholder-muted focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none transition-colors resize-none"
          disabled={loading}
        />
        <div className="absolute bottom-3 right-3">
          <button
            type="submit"
            disabled={loading}
            className="btn-primary flex items-center space-x-2 py-1.5 px-3 text-sm"
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white/20 border-t-white"></div>
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <span>Generate</span>
                <SparklesIcon className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>
      <p className="text-xs text-muted mt-2 px-1">
        Be descriptive! Mention genres, moods, themes, or specific directors.
      </p>
    </form>
  )
}
