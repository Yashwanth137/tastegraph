import { Link } from 'react-router-dom'
import useStore from '../store/useStore'
import PromptInput from '../components/PromptInput'

export default function Landing() {
  const user = useStore((state) => state.user)

  return (
    <div className="relative overflow-hidden min-h-[calc(100vh-4rem)] flex flex-col justify-center">
      {/* Background decoration */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary/20 rounded-full blur-[120px] -z-10 animate-fade-in pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-secondary/10 rounded-full blur-[100px] -z-10 pointer-events-none"></div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center animate-slide-up">
        <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-6">
          <span className="block text-white">Find movies using</span>
          <span className="block text-transparent bg-clip-text bg-gradient-to-r from-primary to-secondary">
            AI Taste Graphs
          </span>
        </h1>
        
        <p className="mt-4 text-xl text-muted max-w-2xl mx-auto mb-10">
          Describe exactly what you're in the mood for. We map your prompt to a high-dimensional vector space to find the perfect cinematic match.
        </p>

        {user ? (
          <div className="max-w-2xl mx-auto text-left">
            <PromptInput />
          </div>
        ) : (
          <div className="flex justify-center gap-4">
            <Link to="/register" className="btn-primary text-lg px-8 py-3 rounded-xl shadow-lg shadow-primary/25">
              Get Started for Free
            </Link>
            <Link to="/login" className="btn-secondary text-lg px-8 py-3 rounded-xl">
              Log in
            </Link>
          </div>
        )}

        <div className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-8 text-left">
          <div className="glass-panel p-6">
            <div className="w-10 h-10 bg-primary/20 rounded-lg flex items-center justify-center mb-4">
              <span className="text-xl">🧠</span>
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Semantic Search</h3>
            <p className="text-muted text-sm">We don't use simple keywords. Our models understand the meaning behind your prompt to find true matches.</p>
          </div>
          <div className="glass-panel p-6">
            <div className="w-10 h-10 bg-secondary/20 rounded-lg flex items-center justify-center mb-4">
              <span className="text-xl">📊</span>
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Taste Graph</h3>
            <p className="text-muted text-sm">As you interact with your library, your taste vector evolves, creating a personalized map of your preferences.</p>
          </div>
          <div className="glass-panel p-6">
            <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center mb-4">
              <span className="text-xl">💬</span>
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Chat with Library</h3>
            <p className="text-muted text-sm">Manage your watchlist entirely through natural language commands. "Add Inception to watched, I loved it."</p>
          </div>
        </div>
      </div>
    </div>
  )
}
