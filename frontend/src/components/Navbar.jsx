import { Link, useNavigate } from 'react-router-dom'
import useStore from '../store/useStore'
import { FilmIcon, UserCircleIcon, ArrowRightOnRectangleIcon } from '@heroicons/react/24/outline'

export default function Navbar() {
  const { user, logout } = useStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <nav className="border-b border-white/5 bg-background/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link to="/" className="flex items-center space-x-2 group">
              <div className="bg-primary/20 p-1.5 rounded-lg group-hover:bg-primary/30 transition-colors">
                <FilmIcon className="w-6 h-6 text-primary" />
              </div>
              <span className="font-bold text-xl tracking-tight text-white">TasteGraph</span>
            </Link>
          </div>

          <div className="flex items-center space-x-4">
            {user ? (
              <>
                <Link to="/results" className="text-muted hover:text-white transition-colors text-sm font-medium">Discover</Link>
                <Link to="/library" className="text-muted hover:text-white transition-colors text-sm font-medium">Library</Link>
                <Link to="/social" className="text-muted hover:text-white transition-colors text-sm font-medium">Community</Link>
                <div className="h-4 w-px bg-white/10 mx-2"></div>
                <Link to="/profile" className="flex items-center space-x-2 text-muted hover:text-white transition-colors">
                  <UserCircleIcon className="w-5 h-5" />
                  <span className="text-sm font-medium">{user.username}</span>
                </Link>
                <button onClick={handleLogout} className="text-muted hover:text-red-400 transition-colors" title="Logout">
                  <ArrowRightOnRectangleIcon className="w-5 h-5" />
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="text-muted hover:text-white transition-colors text-sm font-medium">Log in</Link>
                <Link to="/register" className="btn-primary py-1.5 text-sm">Sign up</Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
