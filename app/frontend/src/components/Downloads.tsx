import { useState, useEffect } from 'react'
import { Download, RefreshCw, FileArchive, AlertCircle, CheckCircle, Clock, XCircle } from 'lucide-react'
import { createStateDownload, getDownloads, DownloadJob } from '../api'
import { formatDateTime } from '../utils/dateFormatter'

const ESTADOS_BR = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
  'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
  'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
]

const POLYGON_TYPES = [
  'AREA_PROPERTY',
  'APPS',
  'NATIVE_VEGETATION',
  'CONSOLIDATED_AREA',
  'AREA_FALL',
  'HYDROGRAPHY',
  'RESTRICTED_USE',
  'ADMINISTRATIVE_SERVICE',
  'LEGAL_RESERVE'
]

export default function Downloads() {
  const [downloads, setDownloads] = useState<DownloadJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Form states
  const [selectedState, setSelectedState] = useState('')
  const [selectedPolygons, setSelectedPolygons] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)

  const fetchDownloads = async () => {
    try {
      setError(null)
      const response = await getDownloads({ limit: 50 })
      setDownloads(response.data.downloads)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Erro ao buscar downloads')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDownloads()
    const interval = setInterval(fetchDownloads, 5000)
    return () => clearInterval(interval)
  }, [])

  const handleDownload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedState || selectedPolygons.length === 0) return

    try {
      setSubmitting(true)
      setError(null)
      await createStateDownload({
        state: selectedState,
        polygons: selectedPolygons
      })
      await fetchDownloads()
      setSelectedState('')
      setSelectedPolygons([])
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Erro ao iniciar download')
    } finally {
      setSubmitting(false)
    }
  }

  const togglePolygon = (polygon: string) => {
    setSelectedPolygons(prev =>
      prev.includes(polygon)
        ? prev.filter(p => p !== polygon)
        : [...prev, polygon]
    )
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <span className="badge-success flex items-center"><CheckCircle className="w-3 h-3 mr-1" />Concluído</span>
      case 'running':
        return <span className="badge-info flex items-center"><Clock className="w-3 h-3 mr-1" />Em execução</span>
      case 'failed':
        return <span className="badge-danger flex items-center"><XCircle className="w-3 h-3 mr-1" />Falhou</span>
      case 'pending':
        return <span className="badge-warning flex items-center"><Clock className="w-3 h-3 mr-1" />Pendente</span>
      default:
        return <span className="badge">{status}</span>
    }
  }

  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return 'N/A'
    const mb = bytes / (1024 * 1024)
    return `${mb.toFixed(2)} MB`
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Downloads</h2>
        <button onClick={fetchDownloads} className="btn-secondary flex items-center">
          <RefreshCw className="w-4 h-4 mr-2" />
          Atualizar
        </button>
      </div>

      {error && (
        <div className="card border-red-200 bg-red-50">
          <div className="flex items-center">
            <AlertCircle className="w-5 h-5 text-red-600 mr-2" />
            <p className="text-red-700">{error}</p>
          </div>
        </div>
      )}

      {/* Form de Novo Download */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Novo Download</h3>
        
        <form onSubmit={handleDownload} className="space-y-4">
          <div>
            <label className="label">Estado</label>
            <select
              value={selectedState}
              onChange={(e) => setSelectedState(e.target.value)}
              className="input"
              required
            >
              <option value="">Selecione um estado</option>
              {ESTADOS_BR.map((state) => (
                <option key={state} value={state}>{state}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">Tipos de Polígonos (selecione um ou mais)</label>
            <div className="grid grid-cols-2 gap-2 mt-2">
              {POLYGON_TYPES.map((type) => (
                <div key={type} className="flex items-center">
                  <input
                    type="checkbox"
                    id={`poly-${type}`}
                    checked={selectedPolygons.includes(type)}
                    onChange={() => togglePolygon(type)}
                    className="w-4 h-4 text-primary-600 rounded"
                  />
                  <label htmlFor={`poly-${type}`} className="ml-2 text-sm text-gray-700">
                    {type}
                  </label>
                </div>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting || !selectedState || selectedPolygons.length === 0}
            className="btn-primary w-full flex items-center justify-center"
          >
            <Download className="w-4 h-4 mr-2" />
            {submitting ? 'Iniciando...' : `Iniciar ${selectedPolygons.length} Download${selectedPolygons.length > 1 ? 's' : ''}`}
          </button>
        </form>
      </div>

      {/* Lista de Downloads */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Downloads Recentes</h3>
        
        {loading && downloads.length === 0 ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        ) : downloads.length === 0 ? (
          <p className="text-center text-gray-500 py-8">Nenhum download encontrado</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Polígono</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tamanho</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Criado</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {downloads.map((download) => (
                  <tr key={download.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      #{download.id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {download.state}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {download.polygon}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(download.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatFileSize(download.file_size)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDateTime(download.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
