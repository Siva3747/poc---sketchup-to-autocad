import axios from 'axios'
import { FloorPlan } from '../store/viewerStore'

// In dev the Vite proxy forwards /api → localhost:8000
// In production a relative URL works across all environments
const BASE_URL = '/api/v1'

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

export interface ProjectListResponse {
  id: string
  filename: string
  source_format: string
  status: string
  error: string | null
  created_at: string
  updated_at: string
  has_dxf: boolean
  has_dwg: boolean
  has_skp_script: boolean
  has_ai: boolean
}

export interface AIDetection {
  id: string
  type: string
  confidence: number
  needs_review: boolean
  geometry: Record<string, unknown>
  properties: Record<string, unknown>
  user_accepted?: boolean
  rejected?: boolean
  user_reclassified?: boolean
}

export interface AIMetadata {
  model: string
  threshold: number
  total_detections: number
  needs_review_count: number
  feature_summary: Record<string, number>
}

export interface ProjectDetailResponse {
  id: string
  filename: string
  source_format: string
  status: string
  has_dxf: boolean
  has_dwg: boolean
  has_skp_script: boolean
  has_ai: boolean
  floorplan: FloorPlan
  ai_detections: AIDetection[]
  ai_metadata: AIMetadata | null
}

export interface CorrectionPayload {
  id: string
  action: 'accept' | 'reject' | 'reclassify'
  new_type?: string
}

export const apiService = {
  // ── Upload ────────────────────────────────────────────────────────────────

  async uploadFile(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    const res = await apiClient.post<{
      id: string; filename: string; source_format: string; status: string; error: string | null; created_at: string
    }>('/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
    return res.data
  },

  // ── Convert ───────────────────────────────────────────────────────────────

  async convertFile(file: File, targetFormat: 'dxf' | 'dwg' | 'json' | 'skp') {
    const formData = new FormData()
    formData.append('file', file)
    const res = await apiClient.post<{
      id: string; source_format: string; target_format: string; download_url: string
    }>(`/convert?target_format=${targetFormat}`, formData, { headers: { 'Content-Type': 'multipart/form-data' } })
    return res.data
  },

  // ── Viewer ────────────────────────────────────────────────────────────────

  async getProjectData(id: string): Promise<ProjectDetailResponse> {
    const res = await apiClient.get<ProjectDetailResponse>(`/viewer/${id}`)
    return res.data
  },

  async updateProjectData(id: string, data: FloorPlan) {
    const res = await apiClient.put<{ id: string; status: string; has_dxf: boolean; has_dwg: boolean; has_skp_script: boolean }>(`/viewer/${id}`, data)
    return res.data
  },

  // ── AI ────────────────────────────────────────────────────────────────────

  async runDetection(projectId: string, threshold = 0.8) {
    const res = await apiClient.post<Record<string, unknown>>(`/detect?project_id=${projectId}&threshold=${threshold}`)
    return res.data
  },

  async applyCorrections(projectId: string, corrections: CorrectionPayload[]) {
    const res = await apiClient.post<Record<string, unknown>>('/detect/correct', { project_id: projectId, corrections })
    return res.data
  },

  // ── Export ────────────────────────────────────────────────────────────────

  getDownloadUrl(id: string, format: 'json' | 'dxf' | 'dwg' | 'skp'): string {
    return `${BASE_URL}/download/${id}?format=${format}`
  },

  async downloadProjectFile(id: string, format: 'json' | 'dxf' | 'dwg' | 'skp'): Promise<{ data: Blob; filename: string }> {
    const res = await apiClient.get(`/download/${id}?format=${format}`, { responseType: 'blob' })
    let filename = `project_${id}.${format === 'skp' ? 'rb' : format}`
    const disp = res.headers['content-disposition']
    if (disp) {
      const m = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disp)
      if (m?.[1]) filename = m[1].replace(/['"]/g, '')
    }
    return { data: res.data, filename }
  },

  // ── Projects list ─────────────────────────────────────────────────────────

  async listProjects(): Promise<ProjectListResponse[]> {
    const res = await apiClient.get<ProjectListResponse[]>('/projects')
    return res.data
  },

  async getSketchUpExporterScript(): Promise<string> {
    const res = await apiClient.get<string>('/sketchup-exporter')
    return res.data
  },
}
