import axios from 'axios'
import { FloorPlan } from '../store/viewerStore'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface ProjectListResponse {
  id: string
  filename: string
  status: string
  error: string | null
  created_at: string
  updated_at: string
  has_dxf: boolean
  has_dwg: boolean
}

export const apiService = {
  /**
   * Upload a .skp or .json file to trigger conversion
   */
  async uploadFile(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await apiClient.post<{
      id: string
      filename: string
      status: string
      error: string | null
      created_at: string
    }>('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  /**
   * Get the floor plan JSON and conversion status
   */
  async getProjectData(id: string) {
    const response = await apiClient.get<{
      id: string
      filename: string
      status: string
      has_dxf: boolean
      has_dwg: boolean
      floorplan: FloorPlan
    }>(`/viewer/${id}`)
    return response.data
  },

  /**
   * Save the updated floor plan JSON and trigger CAD regeneration
   */
  async updateProjectData(id: string, data: FloorPlan) {
    const response = await apiClient.put<{
      id: string
      status: string
      has_dxf: boolean
      has_dwg: boolean
    }>(`/viewer/${id}`, data)
    return response.data
  },

  /**
   * Returns download URL for JSON, DXF, or DWG
   */
  getDownloadUrl(id: string, format: 'json' | 'dxf' | 'dwg'): string {
    return `${BASE_URL}/download/${id}?format=${format}`
  },

  /**
   * Downloads a project file (json, dxf, dwg) as a blob
   */
  async downloadProjectFile(id: string, format: 'json' | 'dxf' | 'dwg'): Promise<{ data: Blob, filename: string }> {
    const response = await apiClient.get(`/download/${id}?format=${format}`, {
      responseType: 'blob'
    })
    
    let filename = `project_${id}.${format}`
    const disposition = response.headers['content-disposition']
    if (disposition && disposition.indexOf('attachment') !== -1) {
      const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/
      const matches = filenameRegex.exec(disposition)
      if (matches != null && matches[1]) {
        filename = matches[1].replace(/['"]/g, '')
      }
    }
    
    return {
      data: response.data,
      filename
    }
  },

  /**
   * Lists all projects
   */
  async listProjects() {
    const response = await apiClient.get<ProjectListResponse[]>('/projects')
    return response.data
  },

  /**
   * Downloads the SketchUp Ruby Plugin Exporter script
   */
  async getSketchUpExporterScript(): Promise<string> {
    const response = await apiClient.get<string>('/sketchup-exporter')
    return response.data
  }
}
