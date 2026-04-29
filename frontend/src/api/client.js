import axios from 'axios'
import useStore from '../store/useStore'

const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add JWT token
apiClient.interceptors.request.use(
  (config) => {
    const token = useStore.getState().token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor to handle 401s (logout)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Clear store on auth error
      useStore.getState().logout()
      // Optionally redirect to login here, though ProtectedRoute handles it
    }
    return Promise.reject(error)
  }
)

export default apiClient
