import { create } from 'zustand'
import { AIDetection, AIMetadata } from '../services/api'

export interface Point { x: number; y: number }

export interface Wall {
  id: string; start: Point; end: Point
  thickness: number; height: number; layer: string
}

export interface Door {
  id: string; wallId: string; position: number
  width: number; height: number
  hand: 'left' | 'right'; direction: 'in' | 'out'; layer: string
}

export interface Window {
  id: string; wallId: string; position: number
  width: number; height: number; elevation: number; layer: string
}

export interface Room {
  id: string; name: string; points: Point[]
  area: number; layer: string
}

export interface Metadata {
  name: string; unit: string; scale: number
  created_at?: string; updated_at?: string
}

export interface FloorPlan {
  metadata: Metadata
  walls: Wall[]; doors: Door[]; windows: Window[]; rooms: Room[]
}

interface HistoryState {
  walls: Wall[]; doors: Door[]; windows: Window[]; rooms: Room[]
}

export type ViewMode = '2d' | '3d' | 'ai'
export type ActiveTool = 'select' | 'draw_wall' | 'add_door' | 'add_window' | 'measure'

interface ViewerStore {
  // Project
  projectId: string | null
  filename: string
  sourceFormat: string

  // Geometry
  metadata: Metadata
  walls: Wall[]; doors: Door[]; windows: Window[]; rooms: Room[]

  // AI
  aiDetections: AIDetection[]
  aiMetadata: AIMetadata | null
  showAiOverlay: boolean
  aiConfidenceThreshold: number
  hasAi: boolean

  // UI
  viewMode: ViewMode
  selectedId: string | null
  activeTool: ActiveTool
  zoom: number; pan: Point
  visibleLayers: Record<string, boolean>
  drawingStart: Point | null
  drawingCurrent: Point | null
  measurementPoints: Point[]
  isSaving: boolean; isLoading: boolean; error: string | null
  undoStack: HistoryState[]; redoStack: HistoryState[]

  // Actions
  setProject: (id: string, filename: string, data: FloorPlan, sourceFormat?: string) => void
  setAiData: (detections: AIDetection[], meta: AIMetadata | null) => void
  updateDetection: (id: string, updates: Partial<AIDetection>) => void
  setViewMode: (mode: ViewMode) => void
  toggleAiOverlay: () => void
  setAiThreshold: (t: number) => void
  setLoading: (v: boolean) => void
  setError: (e: string | null) => void
  setSaving: (v: boolean) => void
  setZoom: (z: number) => void
  setPan: (p: Point | ((prev: Point) => Point)) => void
  setActiveTool: (t: ActiveTool) => void
  selectElement: (id: string | null) => void
  toggleLayer: (name: string) => void
  pushHistory: () => void; undo: () => void; redo: () => void
  addWall: (start: Point, end: Point) => void
  updateWall: (id: string, updates: Partial<Wall>) => void
  addDoor: (wallId: string, position: number, width?: number) => void
  updateDoor: (id: string, updates: Partial<Door>) => void
  addWindow: (wallId: string, position: number, width?: number) => void
  updateWindow: (id: string, updates: Partial<Window>) => void
  deleteElement: (id: string) => void
  setMeasurementPoint: (pt: Point) => void
  clearMeasurement: () => void
  recalculateRooms: () => void
}

const defaultMetadata: Metadata = { name: 'Untitled', unit: 'mm', scale: 1.0 }

export const useViewerStore = create<ViewerStore>((set, get) => ({
  projectId: null, filename: '', sourceFormat: 'skp',
  metadata: defaultMetadata,
  walls: [], doors: [], windows: [], rooms: [],
  aiDetections: [], aiMetadata: null,
  showAiOverlay: true, aiConfidenceThreshold: 0.8, hasAi: false,
  viewMode: '2d',
  selectedId: null, activeTool: 'select',
  zoom: 0.05, pan: { x: 100, y: 100 },
  visibleLayers: { Walls: true, Doors: true, Windows: true, Rooms: true, Grid: true, Dimensions: true },
  drawingStart: null, drawingCurrent: null, measurementPoints: [],
  isSaving: false, isLoading: false, error: null,
  undoStack: [], redoStack: [],

  setProject: (id, filename, data, sourceFormat = 'skp') => set({
    projectId: id, filename, sourceFormat,
    metadata: data?.metadata || defaultMetadata,
    walls: data?.walls || [], doors: data?.doors || [],
    windows: data?.windows || [], rooms: data?.rooms || [],
    selectedId: null, undoStack: [], redoStack: [],
    aiDetections: [], aiMetadata: null, hasAi: false,
  }),

  setAiData: (detections, meta) => set({ aiDetections: detections, aiMetadata: meta, hasAi: detections.length > 0 }),

  updateDetection: (id, updates) => set(s => ({
    aiDetections: s.aiDetections.map(d => d.id === id ? { ...d, ...updates } : d)
  })),

  setViewMode: (mode) => set({ viewMode: mode }),
  toggleAiOverlay: () => set(s => ({ showAiOverlay: !s.showAiOverlay })),
  setAiThreshold: (t) => set({ aiConfidenceThreshold: t }),
  setLoading: (v) => set({ isLoading: v }),
  setError: (e) => set({ error: e }),
  setSaving: (v) => set({ isSaving: v }),
  setZoom: (z) => set({ zoom: Math.max(0.005, Math.min(1.0, z)) }),
  setPan: (p) => set(s => ({ pan: typeof p === 'function' ? p(s.pan) : p })),
  setActiveTool: (t) => set({ activeTool: t, selectedId: null, drawingStart: null, drawingCurrent: null, measurementPoints: [] }),
  selectElement: (id) => set({ selectedId: id }),
  toggleLayer: (name) => set(s => ({ visibleLayers: { ...s.visibleLayers, [name]: !s.visibleLayers[name] } })),

  pushHistory: () => {
    const { walls, doors, windows, rooms, undoStack } = get()
    const snap: HistoryState = {
      walls: JSON.parse(JSON.stringify(walls)),
      doors: JSON.parse(JSON.stringify(doors)),
      windows: JSON.parse(JSON.stringify(windows)),
      rooms: JSON.parse(JSON.stringify(rooms)),
    }
    set({ undoStack: [...undoStack, snap].slice(-30), redoStack: [] })
  },

  undo: () => {
    const { undoStack, redoStack, walls, doors, windows, rooms } = get()
    if (!undoStack.length) return
    const prev = undoStack[undoStack.length - 1]
    const cur: HistoryState = { walls: JSON.parse(JSON.stringify(walls)), doors: JSON.parse(JSON.stringify(doors)), windows: JSON.parse(JSON.stringify(windows)), rooms: JSON.parse(JSON.stringify(rooms)) }
    set({ walls: prev.walls, doors: prev.doors, windows: prev.windows, rooms: prev.rooms, selectedId: null, undoStack: undoStack.slice(0, -1), redoStack: [...redoStack, cur] })
  },

  redo: () => {
    const { undoStack, redoStack, walls, doors, windows, rooms } = get()
    if (!redoStack.length) return
    const next = redoStack[redoStack.length - 1]
    const cur: HistoryState = { walls: JSON.parse(JSON.stringify(walls)), doors: JSON.parse(JSON.stringify(doors)), windows: JSON.parse(JSON.stringify(windows)), rooms: JSON.parse(JSON.stringify(rooms)) }
    set({ walls: next.walls, doors: next.doors, windows: next.windows, rooms: next.rooms, selectedId: null, redoStack: redoStack.slice(0, -1), undoStack: [...undoStack, cur] })
  },

  addWall: (start, end) => {
    get().pushHistory()
    const w: Wall = { id: `w_${Math.random().toString(36).substr(2,6)}`, start, end, thickness: 200, height: 2800, layer: 'Walls' }
    set(s => ({ walls: [...s.walls, w] }))
    get().recalculateRooms()
  },

  updateWall: (id, updates) => {
    get().pushHistory()
    set(s => ({ walls: s.walls.map(w => w.id === id ? { ...w, ...updates } : w) }))
    get().recalculateRooms()
  },

  addDoor: (wallId, position, width = 900) => {
    get().pushHistory()
    const d: Door = { id: `d_${Math.random().toString(36).substr(2,6)}`, wallId, position, width, height: 2100, hand: 'left', direction: 'in', layer: 'Doors' }
    set(s => ({ doors: [...s.doors, d] }))
  },

  updateDoor: (id, updates) => {
    get().pushHistory()
    set(s => ({ doors: s.doors.map(d => d.id === id ? { ...d, ...updates } : d) }))
  },

  addWindow: (wallId, position, width = 1200) => {
    get().pushHistory()
    const w: Window = { id: `win_${Math.random().toString(36).substr(2,6)}`, wallId, position, width, height: 1200, elevation: 900, layer: 'Windows' }
    set(s => ({ windows: [...s.windows, w] }))
  },

  updateWindow: (id, updates) => {
    get().pushHistory()
    set(s => ({ windows: s.windows.map(w => w.id === id ? { ...w, ...updates } : w) }))
  },

  deleteElement: (id) => {
    get().pushHistory()
    set(s => {
      const isWall = s.walls.some(w => w.id === id)
      return {
        walls: s.walls.filter(w => w.id !== id),
        doors: s.doors.filter(d => d.id !== id && (!isWall || d.wallId !== id)),
        windows: s.windows.filter(w => w.id !== id && (!isWall || w.wallId !== id)),
        rooms: s.rooms.filter(r => r.id !== id),
        selectedId: s.selectedId === id ? null : s.selectedId,
      }
    })
    get().recalculateRooms()
  },

  setMeasurementPoint: (pt) => set(s => {
    const pts = [...s.measurementPoints, pt]
    return { measurementPoints: pts.length > 2 ? [pt] : pts }
  }),

  clearMeasurement: () => set({ measurementPoints: [] }),
  recalculateRooms: () => { /* rooms recalculated server-side via Shapely */ },
}))
