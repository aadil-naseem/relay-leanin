import { useQuery } from '@tanstack/react-query'
import { apiRequest } from '../client'

export function useSpof(factoryId = 'fac_owner') {
  return useQuery({
    queryKey: ['spof', factoryId],
    queryFn: () => apiRequest(`/factories/${factoryId}/spof`),
    staleTime: 30_000,
  })
}

export function useFactoryOrders(factoryId = 'fac_owner') {
  return useQuery({
    queryKey: ['orders', factoryId],
    queryFn: () => apiRequest(`/factories/${factoryId}/orders`),
    staleTime: 30_000,
  })
}
