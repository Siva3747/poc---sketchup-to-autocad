import React from 'react'
import { 
  MousePointer, 
  PenTool, 
  DoorClosed, 
  Maximize2, 
  Ruler, 
  Undo2, 
  Redo2,
  Trash2
} from 'lucide-react'
import { useViewerStore } from '../store/viewerStore'

export const Toolbar: React.FC = () => {
  const { 
    activeTool, 
    setActiveTool, 
    undo, 
    redo,
    undoStack,
    redoStack,
    selectedId,
    deleteElement
  } = useViewerStore()

  const tools = [
    { id: 'select', label: 'Select Object', icon: MousePointer, tooltip: 'Select & Move elements (Esc)' },
    { id: 'draw_wall', label: 'Draw Wall', icon: PenTool, tooltip: 'Click on canvas to draw walls (W)' },
    { id: 'add_door', label: 'Place Door', icon: DoorClosed, tooltip: 'Click on a wall to snap a door (D)' },
    { id: 'add_window', label: 'Place Window', icon: Maximize2, tooltip: 'Click on a wall to snap a window (Shift+W)' },
    { id: 'measure', label: 'Ruler', icon: Ruler, tooltip: 'Measure distances between two points (M)' },
  ] as const

  return (
    <div className="absolute top-4 left-4 flex flex-col gap-2 z-20">
      {/* Tools Panel */}
      <div className="flex flex-col p-1.5 rounded-2xl glass-panel shadow-premium gap-1">
        {tools.map((t) => {
          const Icon = t.icon
          const isActive = activeTool === t.id
          
          return (
            <button
              key={t.id}
              onClick={() => setActiveTool(t.id)}
              className={`p-3 rounded-xl transition-all duration-200 group relative flex items-center justify-center ${
                isActive 
                  ? 'bg-blue-600 text-white shadow-[0_0_12px_rgba(37,99,235,0.4)]' 
                  : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
              }`}
              title={t.tooltip}
            >
              <Icon className="h-5 w-5" />
              
              {/* Tooltip */}
              <div className="absolute left-full ml-3 px-3 py-1.5 rounded-lg bg-gray-950 text-xs font-semibold text-gray-200 opacity-0 group-hover:opacity-100 transition-opacity duration-150 pointer-events-none whitespace-nowrap shadow-xl border border-gray-800">
                {t.label} <span className="text-gray-500 font-normal">({t.tooltip.match(/\(([^)]+)\)/)?.[1]})</span>
              </div>
            </button>
          )
        })}
      </div>

      {/* Undo/Redo/Delete Panel */}
      <div className="flex flex-col p-1.5 rounded-2xl glass-panel shadow-premium gap-1">
        <button
          onClick={undo}
          disabled={undoStack.length === 0}
          className={`p-3 rounded-xl transition-all duration-200 flex items-center justify-center ${
            undoStack.length > 0 
              ? 'text-gray-300 hover:text-white hover:bg-gray-800/50' 
              : 'text-gray-600 cursor-not-allowed'
          }`}
          title="Undo (Ctrl+Z)"
        >
          <Undo2 className="h-5 w-5" />
        </button>
        
        <button
          onClick={redo}
          disabled={redoStack.length === 0}
          className={`p-3 rounded-xl transition-all duration-200 flex items-center justify-center ${
            redoStack.length > 0 
              ? 'text-gray-300 hover:text-white hover:bg-gray-800/50' 
              : 'text-gray-600 cursor-not-allowed'
          }`}
          title="Redo (Ctrl+Y)"
        >
          <Redo2 className="h-5 w-5" />
        </button>

        {selectedId && (
          <button
            onClick={() => deleteElement(selectedId)}
            className="p-3 rounded-xl transition-all duration-200 flex items-center justify-center text-rose-500 hover:bg-rose-500/10 hover:text-rose-400"
            title="Delete Selected (Del)"
          >
            <Trash2 className="h-5 w-5 animate-pulse" />
          </button>
        )}
      </div>
    </div>
  )
}
