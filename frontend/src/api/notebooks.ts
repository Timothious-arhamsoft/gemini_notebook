import { apiClient } from './client'
import type { CreateNotebookPayload, Notebook } from '../types'

export const notebooksApi = {
  list: async (): Promise<Notebook[]> => {
    const { data } = await apiClient.get<Notebook[]>('/notebooks/')
    return data
  },

  get: async (id: string): Promise<Notebook> => {
    const { data } = await apiClient.get<Notebook>(`/notebooks/${id}`)
    return data
  },

  create: async (payload: CreateNotebookPayload): Promise<Notebook> => {
    const { data } = await apiClient.post<Notebook>('/notebooks/', payload)
    return data
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/notebooks/${id}`)
  },
}
