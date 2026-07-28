import { create } from 'zustand'

export interface Point {
  x: number
  y: number
}

export interface Wall {
  id: string
  start: Point
  end: Point
  thickness: number
  height: number
  layer: string
}

export interface Door {
  id: string
  wallId: string
  position: number // 0.0 to 1.0 along the wall
  width: number
  height: number
  hand: 'left' | 'right'
  direction: 'in' | 'out'
  layer: string
}

export interface Window {
  id: string
  wallId: string
  position: number // 0.0 to 1.0 along the wall
  width: number
  height: number
  elevation: number
  layer: string
}

export interface Room {
  id: string
  name: string
  points: Point[]
  area: number
  layer: string
}

export interface Metadata {
  name: string
  unit: string
  scale: number
  created_at?: string
  updated_at?: string
}

export interface FloorPlan {
  metadata: Metadata
  walls: Wall[]
  doors: Door[]
  windows: Window[]
  rooms: Room[]
}

interface HistoryState {
  walls: Wall[]
  doors: Door[]
  windows: Window[]
  rooms: Room[]
}

interface ViewerStore {
  // Project ID
  projectId: string | null
  filename: string
  
  // Floorplan geometry state
  metadata: Metadata
  walls: Wall[]
  doors: Door[]
  windows: Window[]
  rooms: Room[]
  
  // UI / View State
  selectedId: string | null
  activeTool: 'select' | 'draw_wall' | 'add_door' | 'add_window' | 'measure'
  zoom: number
  pan: Point
  visibleLayers: Record<string, boolean>
  
  // Interactive drawing states
  drawingStart: Point | null
  drawingCurrent: Point | null
  measurementPoints: Point[]
  
  // Statuses
  isSaving: boolean
  isLoading: boolean
  error: string | null
  
  // Undo/Redo Stacks
  undoStack: HistoryState[]
  redoStack: HistoryState[]
  
  // Core Actions
  setProject: (id: string, filename: string, data: FloorPlan) => void
  setLoading: (loading: boolean) => void
  setError: (err: string | null) => void
  setSaving: (saving: boolean) => void
  
  // View Actions
  setZoom: (zoom: number) => void
  setPan: (pan: Point | ((prev: Point) => Point)) => void
  setActiveTool: (tool: 'select' | 'draw_wall' | 'add_door' | 'add_window' | 'measure') => void
  selectElement: (id: string | null) => void
  toggleLayer: (layerName: string) => void
  
  // Interactive Editing Actions
  pushHistory: () => void
  undo: () => void
  redo: () => void
  
  addWall: (start: Point, end: Point) => void
  updateWall: (id: string, updates: Partial<Wall>) => void
  addDoor: (wallId: string, position: number, width?: number) => void
  updateDoor: (id: string, updates: Partial<Door>) => void
  addWindow: (wallId: string, position: number, width?: number) => void
  updateWindow: (id: string, updates: Partial<Window>) => void
  deleteElement: (id: string) => void
  setMeasurementPoint: (pt: Point) => void
  clearMeasurement: () => void
  
  // Room area recalculation (simplified frontend version)
  recalculateRooms: () => void
}

const defaultMetadata: Metadata = {
  name: 'Untitled Model',
  unit: 'mm',
  scale: 1.0
}

export const useViewerStore = create<ViewerStore>((set, get) => ({
  projectId: null,
  filename: '',
  metadata: defaultMetadata,
  walls: [],
  doors: [],
  windows: [],
  rooms: [],
  
  selectedId: null,
  activeTool: 'select',
  zoom: 0.05, // millimeters to pixels, default: 0.05
  pan: { x: 100, y: 100 },
  visibleLayers: {
    "Walls": true,
    "Doors": true,
    "Windows": true,
    "Rooms": true,
    "Grid": true,
    "Dimensions": true
  },
  
  drawingStart: null,
  drawingCurrent: null,
  measurementPoints: [],
  
  isSaving: false,
  isLoading: false,
  error: null,
  
  undoStack: [],
  redoStack: [],
  
  setProject: (id, filename, data) => set({
    projectId: id,
    filename,
    metadata: data.metadata || defaultMetadata,
    walls: data.walls || [],
    doors: data.doors || [],
    windows: data.windows || [],
    rooms: data.rooms || [],
    selectedId: null,
    undoStack: [],
    redoStack: []
  }),
  
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (err) => set({ error: err }),
  setSaving: (saving) => set({ isSaving: saving }),
  
  setZoom: (zoom) => set({ zoom: Math.max(0.005, Math.min(1.0, zoom)) }),
  setPan: (pan) => set((state) => ({
    pan: typeof pan === 'function' ? pan(state.pan) : pan
  })),
  
  setActiveTool: (tool) => set({
    activeTool: tool,
    selectedId: null,
    drawingStart: null,
    drawingCurrent: null,
    measurementPoints: []
  }),
  
  selectElement: (id) => set({ selectedId: id }),
  
  toggleLayer: (layerName) => set((state) => ({
    visibleLayers: {
      ...state.visibleLayers,
      [layerName]: !state.visibleLayers[layerName]
    }
  })),
  
  pushHistory: () => {
    const { walls, doors, windows, rooms, undoStack } = get()
    const snapState: HistoryState = {
      walls: JSON.parse(JSON.stringify(walls)),
      doors: JSON.parse(JSON.stringify(doors)),
      windows: JSON.parse(JSON.stringify(windows)),
      rooms: JSON.parse(JSON.stringify(rooms))
    }
    set({
      undoStack: [...undoStack, snapState].slice(-30), // Max 30 undo steps
      redoStack: [] // Clear redo on action
    })
  },
  
  undo: () => {
    const { undoStack, redoStack, walls, doors, windows, rooms } = get()
    if (undoStack.length === 0) return
    
    const previous = undoStack[undoStack.length - 1]
    const currentSnap: HistoryState = {
      walls: JSON.parse(JSON.stringify(walls)),
      doors: JSON.parse(JSON.stringify(doors)),
      windows: JSON.parse(JSON.stringify(windows)),
      rooms: JSON.parse(JSON.stringify(rooms))
    }
    
    set({
      walls: previous.walls,
      doors: previous.doors,
      windows: previous.windows,
      rooms: previous.rooms,
      selectedId: null,
      undoStack: undoStack.slice(0, -1),
      redoStack: [...redoStack, currentSnap]
    })
  },
  
  redo: () => {
    const { undoStack, redoStack, walls, doors, windows, rooms } = get()
    if (redoStack.length === 0) return
    
    const next = redoStack[redoStack.length - 1]
    const currentSnap: HistoryState = {
      walls: JSON.parse(JSON.stringify(walls)),
      doors: JSON.parse(JSON.stringify(doors)),
      windows: JSON.parse(JSON.stringify(windows)),
      rooms: JSON.parse(JSON.stringify(rooms))
    }
    
    set({
      walls: next.walls,
      doors: next.doors,
      windows: next.windows,
      rooms: next.rooms,
      selectedId: null,
      redoStack: redoStack.slice(0, -1),
      undoStack: [...undoStack, currentSnap]
    })
  },
  
  addWall: (start, end) => {
    get().pushHistory()
    const newWall: Wall = {
      id: `w_${Math.random().toString(36).substr(2, 6)}`,
      start,
      end,
      thickness: 200,
      height: 2800,
      layer: 'Walls'
    }
    set((state) => ({
      walls: [...state.walls, newWall]
    }))
    get().recalculateRooms()
  },
  
  updateWall: (id, updates) => {
    get().pushHistory()
    set((state) => ({
      walls: state.walls.map(w => w.id === id ? { ...w, ...updates } : w)
    }))
    get().recalculateRooms()
  },
  
  addDoor: (wallId, position, width = 900) => {
    get().pushHistory()
    const newDoor: Door = {
      id: `d_${Math.random().toString(36).substr(2, 6)}`,
      wallId,
      position,
      width,
      height: 2100,
      hand: 'left',
      direction: 'in',
      layer: 'Doors'
    }
    set((state) => ({
      doors: [...state.doors, newDoor]
    }))
  },
  
  updateDoor: (id, updates) => {
    get().pushHistory()
    set((state) => ({
      doors: state.doors.map(d => d.id === id ? { ...d, ...updates } : d)
    }))
  },
  
  addWindow: (wallId, position, width = 1200) => {
    get().pushHistory()
    const newWindow: Window = {
      id: `win_${Math.random().toString(36).substr(2, 6)}`,
      wallId,
      position,
      width,
      height: 1200,
      elevation: 900,
      layer: 'Windows'
    }
    set((state) => ({
      windows: [...state.windows, newWindow]
    }))
  },
  
  updateWindow: (id, updates) => {
    get().pushHistory()
    set((state) => ({
      windows: state.windows.map(w => w.id === id ? { ...w, ...updates } : w)
    }))
  },
  
  deleteElement: (id) => {
    get().pushHistory()
    set((state) => {
      // Check if it's a wall, and delete any associated doors or windows
      const isWall = state.walls.some(w => w.id === id)
      return {
        walls: state.walls.filter(w => w.id !== id),
        doors: state.doors.filter(d => d.id !== id && (!isWall || d.wallId !== id)),
        windows: state.windows.filter(w => w.id !== id && (!isWall || w.wallId !== id)),
        rooms: state.rooms.filter(r => r.id !== id),
        selectedId: state.selectedId === id ? null : state.selectedId
      }
    })
    get().recalculateRooms()
  },
  
  setMeasurementPoint: (pt) => set((state) => {
    const pts = [...state.measurementPoints, pt]
    if (pts.length > 2) {
      return { measurementPoints: [pt] }
    }
    return { measurementPoints: pts }
  }),
  
  clearMeasurement: () => set({ measurementPoints: [] }),
  
  recalculateRooms: () => {
    // Quick frontend room re-calculation trigger stub
    // Rooms are calculated reliably on the backend server via Shapely, 
    // but on the client we can keep the existing rooms unless walls are added or deleted,
    // or trigger an API call to let the server re-calculate the rooms dynamically.
    // For local responsiveness, we leave the active room list or mark it dirty.
  }
}))
