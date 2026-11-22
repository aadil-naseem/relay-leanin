import { createContext, useContext } from 'react'

export const RelayNavigationContext = createContext((path) => window.location.assign(path))

export function useRelayNavigate() {
  return useContext(RelayNavigationContext)
}
