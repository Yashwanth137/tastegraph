import { useState, useEffect } from 'react'
import apiClient from '../api/client'
import { UserCircleIcon, UsersIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

export default function Social() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchSimilar = async () => {
      try {
        const response = await apiClient.get('/social/similar-users')
        setUsers(response.data.users)
      } catch (error) {
        toast.error('Failed to find similar users')
      } finally {
        setLoading(false)
      }
    }
    fetchSimilar()
  }, [])

  const handleFollow = async (userId, isFollowing) => {
    try {
      if (isFollowing) {
        await apiClient.delete(`/social/follow/${userId}`)
        toast.success('Unfollowed user')
      } else {
        await apiClient.post(`/social/follow/${userId}`)
        toast.success('Followed user')
      }
      
      // Optimistic update
      setUsers(users.map(u => u.id === userId ? { ...u, is_following: !isFollowing } : u))
    } catch (error) {
      toast.error('Action failed')
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-12 text-center max-w-2xl mx-auto">
        <UsersIcon className="w-16 h-16 text-primary mx-auto mb-4" />
        <h1 className="text-3xl font-bold tracking-tight text-white mb-4">Taste Neighbors</h1>
        <p className="text-muted text-lg">
          We've mapped your taste vector against the community. These are the users whose cinematic DNA closest matches yours.
        </p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
           {[1, 2, 3, 4, 5, 6].map(i => (
             <div key={i} className="glass-panel p-6 h-40 animate-pulse"></div>
           ))}
        </div>
      ) : users.length === 0 ? (
        <div className="text-center py-20 glass-panel">
          <p className="text-muted">You're a true pioneer. No close matches found yet.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {users.map(user => (
            <div key={user.id} className="glass-panel p-6 flex flex-col justify-between animate-fade-in hover:border-primary/30 transition-colors">
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center space-x-3">
                  <UserCircleIcon className="w-10 h-10 text-muted" />
                  <div>
                    <h3 className="font-bold text-white">{user.username}</h3>
                    <p className="text-xs text-primary font-medium tracking-wide">
                      {(user.similarity * 100).toFixed(1)}% MATCH
                    </p>
                  </div>
                </div>
                <button 
                  onClick={() => handleFollow(user.id, user.is_following)}
                  className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
                    user.is_following 
                      ? 'bg-surface border border-white/20 text-white hover:bg-red-500/20 hover:text-red-400 hover:border-red-500/50'
                      : 'bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30'
                  }`}
                >
                  {user.is_following ? 'Following' : 'Follow'}
                </button>
              </div>

              <div>
                <p className="text-xs text-muted uppercase tracking-wider mb-2">Shared Vibes</p>
                <div className="flex flex-wrap gap-2">
                  {user.shared_tags.slice(0, 4).map(tag => (
                    <span key={tag} className="text-xs bg-white/5 text-white/80 px-2 py-1 rounded-md">
                      {tag}
                    </span>
                  ))}
                  {user.shared_tags.length === 0 && (
                    <span className="text-xs text-muted italic">Hard to pin down...</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
