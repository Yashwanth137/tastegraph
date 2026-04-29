import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const useStore = create(
  persist(
    (set) => ({
      user: null,
      token: null,
      profile: null,
      
      setAuth: (user, token) => set({ user, token }),
      
      logout: () => set({ user: null, token: null, profile: null }),
      
      setProfile: (profile) => set({ profile }),
    }),
    {
      name: 'tastegraph-storage', // name of the item in the storage (must be unique)
      partialize: (state) => ({ user: state.user, token: state.token }), // only save user & token
    }
  )
)

export default useStore
