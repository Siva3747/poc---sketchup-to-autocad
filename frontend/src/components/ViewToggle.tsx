import React from 'react'
import { Square, Box, Brain } from 'lucide-react'
import { useViewerStore, ViewMode } from '../store/viewerStore'

const MODES: { id: ViewMode; label: string; Icon: React.ElementType; title: string }[] = [
  { id: '2d', label: '2D', Icon: Square, title: '2D Floor Plan (Konva)' },
  { id: '3d', label: '3D', Icon: Box, title: '3D Model Viewer (Three.js)' },
  { id: 'ai', label: 'AI', Icon: Brain, title: 'AI Detection Review' },
]

export const ViewToggle: React.FC = () => {
  const { viewMode, setViewMode, hasAi } = useViewerStore()

  return (
    <div className="flex items-center gap-0.5 bg-gray-950/80 border border-gray-800 rounded-xl p-0.5 backdrop-blur-md">
      {MODES.map(({ id, label, Icon, title }) => {
        const active = viewMode === id
        const disabled = id === 'ai' && !hasAi
        return (
          <button
            key={id}
            onClick={() => !disabled && setViewMode(id)}
            disabled={disabled}
            title={disabled ? 'Run AI detection first' : title}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              active
                ? 'bg-blue-600 text-white shadow'
                : disabled
                ? 'text-gray-700 cursor-not-allowed'
                : 'text-gray-400 hover:text-white hover:bg-gray-800/60'
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        )
      })}
    </div>
  )
}
