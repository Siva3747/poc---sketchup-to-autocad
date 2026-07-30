import React, { useState } from 'react'
import { Brain, CheckCircle, XCircle, RefreshCcw, ChevronDown, ChevronUp, AlertTriangle, Eye, EyeOff } from 'lucide-react'
import { useViewerStore } from '../store/viewerStore'
import { apiService, CorrectionPayload } from '../services/api'

const TYPE_COLORS: Record<string, string> = {
  wall: 'text-gray-300', door: 'text-red-400', window: 'text-cyan-400',
  room: 'text-amber-400', bathroom: 'text-blue-400', bedroom: 'text-purple-400',
  living_room: 'text-green-400', kitchen: 'text-orange-400', unknown: 'text-yellow-400',
  slab: 'text-slate-400', beam: 'text-stone-400', hallway: 'text-pink-400',
}

const typeColor = (t: string) => TYPE_COLORS[t] ?? 'text-gray-300'

const OBJECT_TYPES = [
  'wall','door','window','room','bathroom','bedroom','living_room','dining_room',
  'kitchen','hallway','office','closet','storage','garage','slab','beam','stair','column',
]

export const AIReviewPanel: React.FC = () => {
  const {
    aiDetections, aiMetadata, showAiOverlay, toggleAiOverlay,
    aiConfidenceThreshold, setAiThreshold, updateDetection,
    projectId, setAiData,
  } = useViewerStore()

  const [expanded, setExpanded] = useState(true)
  const [pendingCorrections, setPendingCorrections] = useState<Record<string, CorrectionPayload>>({})
  const [saving, setSaving] = useState(false)
  const [rerunning, setRerunning] = useState(false)
  const [reclassifyId, setReclassifyId] = useState<string | null>(null)

  const needsReview = aiDetections.filter(d => d.needs_review && !d.rejected && !d.user_accepted)
  const accepted = aiDetections.filter(d => d.user_accepted)
  const rejected = aiDetections.filter(d => d.rejected)

  const queueCorrection = (id: string, action: CorrectionPayload['action'], new_type?: string) => {
    setPendingCorrections(prev => ({ ...prev, [id]: { id, action, new_type } }))
    updateDetection(id, {
      needs_review: false,
      user_accepted: action === 'accept',
      rejected: action === 'reject',
      user_reclassified: action === 'reclassify',
      ...(new_type ? { type: new_type, confidence: 1.0 } : {}),
    })
  }

  const saveCorrections = async () => {
    if (!projectId || !Object.keys(pendingCorrections).length) return
    setSaving(true)
    try {
      const updated = await apiService.applyCorrections(projectId, Object.values(pendingCorrections))
      const newDetections = (updated as any).ai_detections ?? aiDetections
      setAiData(newDetections, aiMetadata)
      setPendingCorrections({})
    } catch (e) {
      console.error('Failed to save corrections', e)
    } finally {
      setSaving(false)
    }
  }

  const rerunDetection = async () => {
    if (!projectId) return
    setRerunning(true)
    try {
      const result = await apiService.runDetection(projectId, aiConfidenceThreshold)
      const newDetections = (result as any).ai_detections ?? []
      const newMeta = (result as any).ai_metadata ?? null
      setAiData(newDetections, newMeta)
      setPendingCorrections({})
    } catch (e) {
      console.error('Failed to re-run detection', e)
    } finally {
      setRerunning(false)
    }
  }

  if (!aiDetections.length) {
    return (
      <div className="bg-card/60 border border-gray-900 rounded-xl p-4 text-center text-gray-500 text-xs">
        <Brain className="h-6 w-6 mx-auto mb-2 text-gray-700" />
        No AI detections yet.
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-0 bg-[#0d0e12] border border-gray-900/60 rounded-xl overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer border-b border-gray-900/60 hover:bg-gray-900/20"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-purple-400" />
          <span className="text-xs font-bold text-white uppercase tracking-wider">AI Review</span>
          {needsReview.length > 0 && (
            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-yellow-500/20 text-yellow-400 border border-yellow-500/20">
              {needsReview.length} to review
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => { e.stopPropagation(); toggleAiOverlay() }}
            className="text-gray-500 hover:text-blue-400 transition-colors p-0.5"
            title="Toggle AI overlay"
          >
            {showAiOverlay ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
          </button>
          {expanded ? <ChevronUp className="h-3.5 w-3.5 text-gray-600" /> : <ChevronDown className="h-3.5 w-3.5 text-gray-600" />}
        </div>
      </div>

      {expanded && (
        <div className="flex flex-col gap-3 p-4 max-h-[60vh] overflow-y-auto">
          {/* Stats */}
          {aiMetadata && (
            <div className="grid grid-cols-3 gap-2 text-center text-[10px]">
              <div className="bg-gray-900/40 rounded-lg p-2">
                <div className="text-white font-bold text-sm">{aiMetadata.total_detections}</div>
                <div className="text-gray-500">Detected</div>
              </div>
              <div className="bg-yellow-500/10 rounded-lg p-2">
                <div className="text-yellow-400 font-bold text-sm">{aiMetadata.needs_review_count}</div>
                <div className="text-gray-500">Review</div>
              </div>
              <div className="bg-green-500/10 rounded-lg p-2">
                <div className="text-green-400 font-bold text-sm">{accepted.length}</div>
                <div className="text-gray-500">Accepted</div>
              </div>
            </div>
          )}

          {/* Confidence threshold */}
          <div className="flex flex-col gap-1">
            <div className="flex justify-between text-[10px]">
              <span className="text-gray-500">Confidence threshold</span>
              <span className="text-gray-300 font-mono">{(aiConfidenceThreshold * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range" min={0.5} max={1.0} step={0.05}
              value={aiConfidenceThreshold}
              onChange={e => setAiThreshold(parseFloat(e.target.value))}
              className="w-full accent-purple-500 h-1"
            />
          </div>

          {/* Items needing review */}
          {needsReview.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <div className="text-[10px] text-yellow-400 font-bold uppercase tracking-wider flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" /> Needs Review
              </div>
              {needsReview.map(det => (
                <div key={det.id} className="bg-yellow-500/5 border border-yellow-500/20 rounded-lg p-2.5 flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className={`text-xs font-semibold ${typeColor(det.type)}`}>{det.type}</span>
                      <span className="text-[10px] text-gray-500 ml-2">{(det.confidence * 100).toFixed(0)}% conf</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => queueCorrection(det.id, 'accept')}
                        className="p-1 rounded hover:bg-green-500/20 text-green-400 transition-colors"
                        title="Accept"
                      >
                        <CheckCircle className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => setReclassifyId(reclassifyId === det.id ? null : det.id)}
                        className="p-1 rounded hover:bg-blue-500/20 text-blue-400 transition-colors"
                        title="Reclassify"
                      >
                        <RefreshCcw className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => queueCorrection(det.id, 'reject')}
                        className="p-1 rounded hover:bg-red-500/20 text-red-400 transition-colors"
                        title="Reject"
                      >
                        <XCircle className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                  {reclassifyId === det.id && (
                    <select
                      className="text-[10px] bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-300 w-full"
                      defaultValue={det.type}
                      onChange={e => {
                        queueCorrection(det.id, 'reclassify', e.target.value)
                        setReclassifyId(null)
                      }}
                    >
                      {OBJECT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Accepted / rejected summary */}
          {(accepted.length > 0 || rejected.length > 0) && (
            <div className="flex gap-2 text-[10px]">
              {accepted.length > 0 && (
                <div className="flex items-center gap-1 text-green-400">
                  <CheckCircle className="h-3 w-3" /> {accepted.length} accepted
                </div>
              )}
              {rejected.length > 0 && (
                <div className="flex items-center gap-1 text-red-400">
                  <XCircle className="h-3 w-3" /> {rejected.length} rejected
                </div>
              )}
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-2 pt-1">
            {Object.keys(pendingCorrections).length > 0 && (
              <button
                onClick={saveCorrections}
                disabled={saving}
                className="flex-1 text-[10px] font-bold py-1.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white transition-colors disabled:opacity-50"
              >
                {saving ? 'Saving…' : `Save ${Object.keys(pendingCorrections).length} corrections`}
              </button>
            )}
            <button
              onClick={rerunDetection}
              disabled={rerunning}
              className="flex-1 text-[10px] font-bold py-1.5 rounded-lg border border-gray-800 hover:border-gray-700 text-gray-400 hover:text-white transition-colors disabled:opacity-50 flex items-center justify-center gap-1"
            >
              <RefreshCcw className={`h-3 w-3 ${rerunning ? 'animate-spin' : ''}`} />
              {rerunning ? 'Running…' : 'Re-run AI'}
            </button>
          </div>

          {aiMetadata && (
            <div className="text-[9px] text-gray-600 text-center">
              Model: {aiMetadata.model} · threshold {(aiMetadata.threshold * 100).toFixed(0)}%
            </div>
          )}
        </div>
      )}
    </div>
  )
}
