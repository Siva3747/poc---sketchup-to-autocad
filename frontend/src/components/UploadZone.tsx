import React, { useRef, useState } from 'react'
import { Upload, FileCode, CheckCircle, AlertCircle, Loader, Cpu } from 'lucide-react'
import { apiService } from '../services/api'

interface UploadZoneProps {
  onUploadSuccess: (projectId: string) => void
}

const ACCEPTED_EXTS = ['.skp', '.dxf', '.dwg', '.json']
const FORMAT_COLORS: Record<string, string> = {
  skp: 'text-blue-400', dxf: 'text-amber-400', dwg: 'text-emerald-400', json: 'text-purple-400'
}

export const UploadZone: React.FC<UploadZoneProps> = ({ onUploadSuccess }) => {
  const [isDragActive, setIsDragActive] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation()
    setIsDragActive(e.type === 'dragenter' || e.type === 'dragover')
  }

  const processFile = async (file: File) => {
    const ext = '.' + (file.name.split('.').pop()?.toLowerCase() ?? '')
    if (!ACCEPTED_EXTS.includes(ext)) {
      setError(`Unsupported format "${ext}". Accepted: ${ACCEPTED_EXTS.join(', ')}`)
      return
    }
    setUploading(true); setError(null); setSuccess(null)
    try {
      const response = await apiService.uploadFile(file)
      setSuccess(`"${file.name}" uploaded. Running AI pipeline…`)
      setTimeout(() => onUploadSuccess(response.id), 900)
    } catch (err: any) {
      setError(err.response?.data?.detail ?? 'Upload failed. Check backend connection.')
    } finally {
      setUploading(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation(); setIsDragActive(false)
    if (e.dataTransfer.files?.[0]) processFile(e.dataTransfer.files[0])
  }

  return (
    <div className="flex flex-col items-center justify-center p-8 w-full max-w-xl">
      <div
        onDragEnter={handleDrag} onDragOver={handleDrag}
        onDragLeave={handleDrag} onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`w-full h-80 rounded-2xl border-2 border-dashed flex flex-col items-center justify-center p-6 text-center cursor-pointer transition-all duration-300 relative overflow-hidden ${
          isDragActive
            ? 'border-blue-500 bg-blue-500/5 shadow-[0_0_20px_rgba(59,130,246,0.15)]'
            : 'border-gray-800 bg-card hover:border-blue-500/50 hover:bg-card/80 hover:shadow-lg'
        }`}
      >
        <input
          ref={fileInputRef} type="file"
          accept={ACCEPTED_EXTS.join(',')}
          className="hidden" disabled={uploading}
          onChange={e => e.target.files?.[0] && processFile(e.target.files[0])}
        />
        {/* Blueprint grid BG */}
        <div className="absolute inset-0 opacity-[0.02] pointer-events-none bg-[linear-gradient(rgba(255,255,255,0.1)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.1)_1px,transparent_1px)] bg-[size:20px_20px]" />

        {uploading ? (
          <div className="flex flex-col items-center animate-pulse">
            <Loader className="h-12 w-12 text-blue-500 animate-spin mb-4" />
            <h3 className="text-lg font-semibold text-white mb-2">Running AI Pipeline</h3>
            <p className="text-sm text-gray-400 max-w-xs">Detecting geometry, extracting elements, running AI classification…</p>
          </div>
        ) : success ? (
          <div className="flex flex-col items-center text-emerald-400">
            <CheckCircle className="h-12 w-12 mb-4 animate-bounce" />
            <h3 className="text-lg font-semibold mb-2">Upload Complete</h3>
            <p className="text-sm text-gray-400 max-w-xs">{success}</p>
          </div>
        ) : (
          <div className="flex flex-col items-center z-10">
            <div className="h-16 w-16 rounded-full bg-blue-500/10 flex items-center justify-center mb-5">
              <Upload className="h-8 w-8 text-blue-500" />
            </div>
            <h3 className="text-xl font-bold text-white mb-2 font-display">Upload CAD / BIM File</h3>
            <p className="text-sm text-gray-400 mb-5 max-w-sm">
              Drag & drop or browse — supports{' '}
              {ACCEPTED_EXTS.map((ext, i) => (
                <span key={ext}>
                  <span className={FORMAT_COLORS[ext.slice(1)] ?? 'text-blue-400'} style={{fontWeight:600}}>{ext}</span>
                  {i < ACCEPTED_EXTS.length - 1 ? ', ' : ''}
                </span>
              ))}
            </p>
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 text-xs font-semibold tracking-wide uppercase transition-colors border border-blue-500/20">
              <Cpu className="h-3.5 w-3.5" />
              Browse Files
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-4 w-full p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="text-xs text-rose-300">
            <p className="font-semibold text-sm text-white mb-0.5">Upload Error</p>
            {error}
          </div>
        </div>
      )}

      <div className="mt-6 flex items-center justify-center gap-2 text-xs text-gray-500 border border-gray-900 rounded-full px-4 py-1.5 bg-gray-950/40">
        <FileCode className="h-4 w-4" />
        <span>Need SketchUp precision? Download the Ruby Plugin inside the editor.</span>
      </div>
    </div>
  )
}
