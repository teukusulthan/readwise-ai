import type { ApiResponse } from '@/types/api'
import { apiRequests } from './api-factory.service'

export interface IGetAllParams {
  page?: number
  size?: number
  search?: string
  search_by?: string[]
  [key: string]: unknown
}

export interface IGetOneParams {
  id: string
}

export interface IDeleteParams {
  id: string
}

export interface IResourceService<T, TCreate = Partial<T>, TUpdate = Partial<T>> {
  add: (data: TCreate) => Promise<ApiResponse<T>>
  getAll: (params?: IGetAllParams) => Promise<ApiResponse<T[]>>
  getOne: (params: IGetOneParams) => Promise<ApiResponse<T>>
  update: (data: TUpdate & { id: string }) => Promise<ApiResponse<T>>
  delete: (params: IDeleteParams) => Promise<ApiResponse<null>>
}

export function createResourceService<T, TCreate = Partial<T>, TUpdate = Partial<T>>(basePath: string): IResourceService<T, TCreate, TUpdate> {
  return {
    add: (data: TCreate) => apiRequests.post<T, TCreate>(`${basePath}/add`, data),

    getAll: (params?: IGetAllParams) => apiRequests.post<T[], IGetAllParams>(`${basePath}/get-all`, params ?? {}),

    getOne: (params: IGetOneParams) => apiRequests.get<T>(`${basePath}/get-one`, params),

    update: (data: TUpdate & { id: string }) => apiRequests.put<T, TUpdate & { id: string }>(`${basePath}/update`, data),

    delete: (params: IDeleteParams) => apiRequests.delete<null>(`${basePath}/delete`, params),
  }
}
