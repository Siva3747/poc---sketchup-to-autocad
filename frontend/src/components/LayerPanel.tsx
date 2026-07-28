import React, { useState } from 'react'
import { Layers, Eye, EyeOff, Menu } from 'lucide-react'
import { useViewerStore } from '../store/viewerStore'

export const LayerPanel: React.FC = () => {
  const { visibleLayers, toggleLayer } = useViewerStore()
  const [isOpen, setIsOpen] = useState(false)

  const layerLabels: Record<string, string> = {
    "Walls": "Walls Layer",
    "Doors": "Doors Layer",
    "Windows": "Windows Layer",
    "Rooms": "Room Boundaries",
    "Dimensions": "CAD Dimensions",
    "Grid": "Canvas Grid"
  }

  return (
    <div className="absolute top-4 right-4 z-20 flex flex-col items-end gap-2 pointer-events-none">
      {/* Toggle Button (three lines) */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2.5 rounded-xl glass-panel shadow-premium text-gray-300 hover:text-white pointer-events-auto transition-colors flex items-center justify-center border border-gray-800/80 hover:bg-gray-800/40"
        title="Toggle Layers Panel"
      >
        <Menu className="h-5 w-5 text-blue-400" />
      </button>

      {/* Layer Options List Panel */}
      {isOpen && (
        <div className="p-3 rounded-2xl glass-panel shadow-premium flex flex-col gap-2.5 w-56 pointer-events-auto border border-gray-800/80">
          <div className="flex items-center gap-2 border-b border-gray-800 pb-2 mb-1 px-1">
            <Layers className="h-4 w-4 text-blue-400" />
            <span className="text-xs font-bold text-white uppercase tracking-wider">CAD Tag Layers</span>
          </div>

          <div className="flex flex-col gap-1.5">
            {Object.entries(visibleLayers).map(([layerName, isVisible]) => (
              <button
                key={layerName}
                onClick={() => toggleLayer(layerName)}
                className="flex items-center justify-between px-2 py-1.5 rounded-lg text-left text-xs font-medium transition-all duration-150 hover:bg-gray-800/40 text-gray-300 hover:text-white"
              >
                <span>{layerLabels[layerName] || layerName}</span>
                {isVisible ? (
                  <Eye className="h-4 w-4 text-blue-500" />
                ) : (
                  <EyeOff className="h-4 w-4 text-gray-600" />
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
