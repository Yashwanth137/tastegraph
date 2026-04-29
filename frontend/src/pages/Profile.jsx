import { useState, useEffect } from 'react'
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts'
import apiClient from '../api/client'
import useStore from '../store/useStore'
import { UserCircleIcon, ClockIcon } from '@heroicons/react/24/outline'

export default function Profile() {
  const { user, profile: activeProfile } = useStore()
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await apiClient.get('/profile/history')
        setHistory(response.data)
      } catch (error) {
        console.error("Failed to fetch history", error)
      } finally {
        setLoading(false)
      }
    }
    fetchHistory()
  }, [])

  // Calculate tag frequencies for radar chart based on the active profile's tags
  // In a real app, this would be computed on the backend from the embeddings
  // For the MVP, we visualize the tags attached to the profile
  const chartData = activeProfile?.tags?.map(tag => ({
    subject: tag,
    A: 100, // Normalized score
    fullMark: 100,
  })) || []

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center space-x-4 mb-12">
        <div className="w-20 h-20 bg-primary/20 rounded-full flex items-center justify-center">
          <UserCircleIcon className="w-12 h-12 text-primary" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-white">{user?.username}</h1>
          <p className="text-muted">Taste Graph Version {activeProfile?.version || 0}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Radar Chart */}
        <div className="lg:col-span-2 glass-panel p-6 min-h-[400px] flex flex-col">
          <h2 className="text-xl font-bold text-white mb-6">Taste Fingerprint</h2>
          {chartData.length > 0 ? (
            <div className="flex-grow w-full h-[400px]">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="80%" data={chartData}>
                  <PolarGrid stroke="rgba(255,255,255,0.1)" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: '#9ca3af', fontSize: 12 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar name="Taste" dataKey="A" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.4} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex-grow flex items-center justify-center text-muted">
              Not enough data to map taste fingerprint.
            </div>
          )}
        </div>

        {/* History */}
        <div className="glass-panel p-6">
          <h2 className="text-xl font-bold text-white mb-6 flex items-center">
            <ClockIcon className="w-5 h-5 mr-2 text-primary" />
            Evolution History
          </h2>
          
          {loading ? (
            <div className="animate-pulse space-y-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-20 bg-white/5 rounded-lg"></div>
              ))}
            </div>
          ) : (
            <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
              {history.map((p) => (
                <div key={p.id} className={`p-4 rounded-lg border ${p.version === activeProfile?.version ? 'bg-primary/10 border-primary/30' : 'bg-surface/50 border-white/5'}`}>
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs font-bold text-primary uppercase tracking-wider">v{p.version}</span>
                    <span className="text-xs text-muted">{new Date(p.created_at).toLocaleDateString()}</span>
                  </div>
                  <p className="text-sm text-white italic mb-2 line-clamp-2">"{p.prompt}"</p>
                  <div className="flex flex-wrap gap-1">
                    {p.tags?.slice(0, 3).map(tag => (
                      <span key={tag} className="text-[10px] bg-white/10 text-muted px-2 py-0.5 rounded-full">
                        {tag}
                      </span>
                    ))}
                    {p.tags?.length > 3 && (
                      <span className="text-[10px] text-muted ml-1">+{p.tags.length - 3}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
