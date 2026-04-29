import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import useStore from './store/useStore'
import Navbar from './components/Navbar'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'
import Results from './pages/Results'
import Library from './pages/Library'
import Profile from './pages/Profile'
import Social from './pages/Social'

// Protected Route Wrapper
const ProtectedRoute = ({ children }) => {
  const token = useStore((state) => state.token)
  if (!token) return <Navigate to="/login" replace />
  return children
}

function App() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />
      <main className="flex-grow">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          
          <Route path="/results" element={
            <ProtectedRoute><Results /></ProtectedRoute>
          } />
          <Route path="/profile" element={
            <ProtectedRoute><Profile /></ProtectedRoute>
          } />
          <Route path="/library" element={
            <ProtectedRoute><Library /></ProtectedRoute>
          } />
          <Route path="/social" element={
            <ProtectedRoute><Social /></ProtectedRoute>
          } />
        </Routes>
      </main>
      <Toaster position="bottom-right" toastOptions={{
        style: { background: '#171717', color: '#f3f4f6', border: '1px solid rgba(255,255,255,0.1)' }
      }} />
    </div>
  )
}

export default App
