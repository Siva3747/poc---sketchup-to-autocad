import React, { useRef, useState } from 'react'
import { Upload, FileCode, CheckCircle, AlertCircle, Loader } from 'lucide-react'
import { apiService } from '../services/api'

interface UploadZoneProps {
  onUploadSuccess: (projectId: string) => void
}

export const UploadZone: React.FC<UploadZoneProps> = ({ onUploadSuccess }) => {
  const [isDragActive, setIsDragActive] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragActive(true)
    } else if (e.type === "dragleave") {
      setIsDragActive(false)
    }
  }

  const processFile = async (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase()
    if (ext !== 'skp' && ext !== 'json') {
      setError("Unsupported file format. Please upload a SketchUp (.skp) or exported JSON file.")
      return
    }
    
    setUploading(true)
    setError(null)
    setSuccess(null)
    
    try {
      const response = await apiService.uploadFile(file)
      setSuccess(`File "${file.name}" uploaded successfully! Processing geometry...`)
      // Wait a tiny bit for the animation to look premium
      setTimeout(() => {
        onUploadSuccess(response.id)
      }, 1000)
    } catch (err: any) {
      setError(err.response?.data?.detail || "Upload failed. Please check backend connection.")
    } finally {
      setUploading(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0])
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0])
    }
  }

  const triggerFileInput = () => {
    fileInputRef.current?.click()
  }

  return (
    <div className="flex flex-col items-center justify-center p-8 w-full max-w-xl">
      <div 
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={triggerFileInput}
        className={`w-full h-80 rounded-2xl border-2 border-dashed flex flex-col items-center justify-center p-6 text-center cursor-pointer transition-all duration-300 relative overflow-hidden ${
          isDragActive 
            ? 'border-blue-500 bg-blue-500/5 shadow-[0_0_20px_rgba(59,130,246,0.15)]Scale-98' 
            : 'border-gray-800 bg-card hover:border-blue-500/50 hover:bg-card/80 hover:shadow-lg'
        }`}
      >
        <input 
          ref={fileInputRef}
          type="file" 
          accept=".skp,.json" 
          className="hidden" 
          onChange={handleFileChange}
          disabled={uploading}
        />
        
        {/* Subtle grid lines background to resemble blueprint/CAD */}
        <div className="absolute inset-0 opacity-[0.02] pointer-events-none bg-[linear-gradient(rgba(255,255,255,0.1)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.1)_1px,transparent_1px)] bg-[size:20px_20px]" />

        {uploading ? (
          <div className="flex flex-col items-center animate-pulse">
            <Loader className="h-12 w-12 text-blue-500 animate-spin mb-4" />
            <h3 className="text-lg font-semibold text-white mb-2">Analyzing Architecture</h3>
            <p className="text-sm text-gray-400 max-w-xs">
              Detecting vertical faces, grouping walls, and segmenting rooms...
            </p>
          </div>
        ) : success ? (
          <div className="flex flex-col items-center text-accent-emerald">
            <CheckCircle className="h-12 w-12 mb-4 animate-bounce" />
            <h3 className="text-lg font-semibold mb-2">Upload Complete</h3>
            <p className="text-sm text-gray-400 max-w-xs">{success}</p>
          </div>
        ) : (
          <div className="flex flex-col items-center z-10">
            <div className="h-16 w-16 rounded-full bg-blue-500/10 flex items-center justify-center mb-5 group-hover:scale-110 transition-transform duration-300">
              <Upload className="h-8 w-8 text-blue-500" />
            </div>
            
            <h3 className="text-xl font-bold text-white mb-2 font-display">
              Upload SketchUp Model
            </h3>
            
            <p className="text-sm text-gray-400 mb-6 max-w-sm">
              Drag & drop a <span className="text-blue-400 font-semibold">.skp</span> file, or a pre-exported <span className="text-blue-400 font-semibold">.json</span> blueprint.
            </p>
            
            <div className="inline-flex items-center px-4 py-2 rounded-xl bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 text-xs font-semibold tracking-wide uppercase transition-colors border border-blue-500/20">
              Browse Files
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-4 w-full p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-start gap-3 animate-headshake">
          <AlertCircle className="h-5 w-5 text-accent-rose shrink-0 mt-0.5" />
          <div className="text-xs text-rose-300 font-medium">
            <p className="font-semibold text-sm text-white mb-0.5">Process Error</p>
            {error}
          </div>
        </div>
      )}
      
      <div className="mt-6 flex items-center justify-center gap-2 text-xs text-gray-500 border border-gray-900 rounded-full px-4 py-1.5 bg-gray-950/40">
        <FileCode className="h-4 w-4" />
        <span>Looking for SketchUp Extension? See side panel inside editor.</span>
      </div>
    </div>
  )
}
