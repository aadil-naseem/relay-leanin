import { useQuery } from '@tanstack/react-query'
import { getHealth } from '../client'

export function useHealth({ enabled = true } = {}) {
  return useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 60_000,
    enabled,
  })
}
