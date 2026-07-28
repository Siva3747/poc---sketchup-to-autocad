import React from 'react'
import { Hash, Locate, Info } from 'lucide-react'
import { useViewerStore } from '../store/viewerStore'

interface StatusBarProps {
  cursorPos: { x: number; y: number } | null
  snapActive: boolean
}

export const StatusBar: React.FC<StatusBarProps> = ({ cursorPos, snapActive }) => {
  const { activeTool, metadata } = useViewerStore()

  const getToolInstruction = () => {
    switch (activeTool) {
      case 'select':
        return 'Select: Click on an element to modify properties. Drag wall endpoints to resize. Press Del to delete.'
      case 'draw_wall':
        return 'Wall Tool: Click to place start point. Move cursor and click to place next wall node. Double-click or Esc to finish.'
      case 'add_door':
        return 'Door Tool: Hover over any wall centerline and click to insert a door. Doors auto-align to wall angles.'
      case 'add_window':
        return 'Window Tool: Hover over any wall centerline and click to insert a window.'
      case 'measure':
        return 'Ruler: Click two points to measure the straight-line distance between them in real-world units.'
      default:
        return ''
    }
  }

  return (
    <div className="absolute bottom-4 left-4 z-20 flex flex-col md:flex-row items-start md:items-center gap-3 pointer-events-none">
      {/* Dynamic Instruction */}
      <div className="flex items-center gap-2 px-3 py-2 rounded-xl glass-panel text-xs text-gray-300 shadow-premium pointer-events-auto border border-gray-800/80">
        <Info className="h-4 w-4 text-blue-400 shrink-0" />
        <span className="truncate max-w-xs sm:max-w-md md:max-w-lg lg:max-w-xl">{getToolInstruction()}</span>
      </div>

      {/* Snap and Coordinates */}
      <div className="flex items-center gap-3 px-3 py-2 rounded-xl glass-panel text-xs shadow-premium pointer-events-auto border border-gray-800/80 shrink-0">
        <div className="flex items-center gap-1 text-gray-400">
          <Hash className="h-3.5 w-3.5" />
          <span>Grid Snap:</span>
          <span className={snapActive ? "text-accent-emerald font-semibold" : "text-gray-500"}>
            {snapActive ? "ON" : "OFF"}
          </span>
        </div>
        
        <div className="h-3 w-px bg-gray-800" />
        
        <div className="flex items-center gap-1.5 font-mono text-gray-300">
          <Locate className="h-3.5 w-3.5 text-blue-400" />
          {cursorPos ? (
            <span>
              X: <span className="text-white">{Math.round(cursorPos.x)}</span> {metadata.unit} | 
              Y: <span className="text-white">{Math.round(cursorPos.y)}</span> {metadata.unit}
            </span>
          ) : (
            <span className="text-gray-500">X: -- | Y: --</span>
          )}
        </div>
      </div>
    </div>
  )
}
