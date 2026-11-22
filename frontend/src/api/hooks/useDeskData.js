import { useQuery } from '@tanstack/react-query'
import { apiRequest } from '../client'

export const FACTORY_ID = 'fac_owner'

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard', FACTORY_ID],
    queryFn: () => apiRequest(`/dashboard/${FACTORY_ID}`),
    staleTime: 30_000,
    refetchInterval: 5 * 60_000,
  })
}

export function useReadiness() {
  return useQuery({
    queryKey: ['readiness', FACTORY_ID],
    queryFn: () => apiRequest(`/readiness/${FACTORY_ID}`),
    staleTime: 30_000,
  })
}

export function useReadinessActions() {
  return useQuery({
    queryKey: ['readiness', FACTORY_ID, 'actions'],
    queryFn: () => apiRequest(`/readiness/${FACTORY_ID}/actions`),
    staleTime: 30_000,
  })
}

export function useExposureMap() {
  return useQuery({
    queryKey: ['exposure', 'map'],
    queryFn: () => apiRequest('/exposure/map'),
    staleTime: 30_000,
  })
}

export function useOwnerExposure() {
  return useQuery({
    queryKey: ['exposure', FACTORY_ID],
    queryFn: () => apiRequest(`/factories/${FACTORY_ID}/exposure`),
    staleTime: 30_000,
  })
}

export function useStressTest(stressId) {
  return useQuery({
    queryKey: ['stress-test', stressId],
    queryFn: () => apiRequest(`/stress-tests/${stressId}`),
    enabled: Boolean(stressId),
    staleTime: 30_000,
  })
}
