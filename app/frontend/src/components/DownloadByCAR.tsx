import { useState } from 'react'
import { Search, Download, FileText, MapPin, CheckCircle, Clock, XCircle, AlertCircle } from 'lucide-react'
import { searchCAR, downloadByCAR, getDownloadByCAR, PropertyData, DownloadJob } from '../api'
import { formatDateTime } from '../utils/dateFormatter'

export default function DownloadByCAR() {
  const [carNumber, setCarNumber] = useState('')
  const [searchResult, setSearchResult] = useState<PropertyData | null>(null)
  const [downloadStatus, setDownloadStatus] = useState<DownloadJob | null>(null)
  const [searching, setSearching] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [checkingStatus, setCheckingStatus] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [force, setForce] = useState(false)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!carNumber.trim()) return

    try {
      setSearching(true)
      setError(null)
      setSearchResult(null)
      const response = await searchCAR(carNumber)
      setSearchResult(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'CAR não encontrado')
    } finally {
      setSearching(false)
    }
  }

  const handleDownload = async () => {
    if (!carNumber.trim()) return

    try {
      setDownloading(true)
      setError(null)
      await downloadByCAR({ car_number: carNumber, force })
      // Buscar status imediatamente
      await handleCheckStatus()
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Erro ao iniciar download')
    } finally {
      setDownloading(false)
    }
  }

  const handleCheckStatus = async () => {
    if (!carNumber.trim()) return

    try {
      setCheckingStatus(true)
      setError(null)
      const response = await getDownloadByCAR(carNumber)
      setDownloadStatus(response.data)
    } catch (err: any) {
      if (err.response?.status === 404) {
        setError('Nenhum download encontrado para este CAR')
      } else {
        setError(err.response?.data?.detail || err.message || 'Erro ao verificar status')
      }
    } finally {
      setCheckingStatus(false)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
            <CheckCircle className="w-4 h-4 mr-2" />
            Concluído
          </span>
        )
      case 'running':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
            <Clock className="w-4 h-4 mr-2" />
            Em execução
          </span>
        )
      case 'failed':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800">
            <XCircle className="w-4 h-4 mr-2" />
            Falhou
          </span>
        )
      case 'pending':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800">
            <Clock className="w-4 h-4 mr-2" />
            Pendente
          </span>
        )
      default:
        return <span className="badge">{status}</span>
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Download por Número CAR</h2>
        <p className="text-gray-600 mt-1">
          Busque e baixe shapefiles de propriedades individuais pelo número CAR
        </p>
      </div>

      {error && (
        <div className="card border-red-200 bg-red-50">
          <div className="flex items-center">
            <AlertCircle className="w-5 h-5 text-red-600 mr-2" />
            <p className="text-red-700">{error}</p>
          </div>
        </div>
      )}

      {/* Busca de CAR */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">1. Buscar Propriedade</h3>
        <form onSubmit={handleSearch} className="space-y-4">
          <div>
            <label className="label">Número CAR</label>
            <input
              type="text"
              value={carNumber}
              onChange={(e) => setCarNumber(e.target.value)}
              placeholder="Ex: SP-3538709-E398FD1AAE3E4AAC8E074A6532A3B9FA"
              className="input"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Formato: UF-CÓDIGO-HASH (ex: SP-3538709-E398FD1AAE3E4AAC8E074A6532A3B9FA)
            </p>
          </div>

          <button
            type="submit"
            disabled={searching || !carNumber.trim()}
            className="btn-primary w-full flex items-center justify-center"
          >
            <Search className="w-4 h-4 mr-2" />
            {searching ? 'Buscando...' : 'Buscar Propriedade'}
          </button>
        </form>
      </div>

      {/* Resultado da Busca */}
      {searchResult && (
        <div className="card border-primary-200 bg-primary-50">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center">
              <FileText className="w-8 h-8 text-primary-600 mr-3" />
              <div>
                <h3 className="text-lg font-semibold text-primary-900">Propriedade Encontrada</h3>
                <p className="text-sm text-primary-700">Dados da propriedade no SICAR</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="badge bg-primary-200 text-primary-900">
                {searchResult.uf}
              </span>
              <a
                href={`https://car.gov.br/#/consultar/${searchResult.car_number}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 hover:text-primary-800 text-sm font-medium flex items-center"
                title="Ver no site do SICAR"
              >
                Ver no SICAR →
              </a>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <p className="text-xs text-primary-700 font-medium">Número CAR</p>
              <p className="text-sm text-primary-900 font-mono">{searchResult.car_number}</p>
            </div>
            <div>
              <p className="text-xs text-primary-700 font-medium">Código</p>
              <p className="text-sm text-primary-900">{searchResult.codigo}</p>
            </div>
            <div>
              <p className="text-xs text-primary-700 font-medium">Município</p>
              <p className="text-sm text-primary-900 flex items-center">
                <MapPin className="w-3 h-3 mr-1" />
                {searchResult.municipio}
              </p>
            </div>
            <div>
              <p className="text-xs text-primary-700 font-medium">Área</p>
              <p className="text-sm text-primary-900">{searchResult.area.toFixed(2)} ha</p>
            </div>
            <div>
              <p className="text-xs text-primary-700 font-medium">Status</p>
              <p className="text-sm text-primary-900">{searchResult.status}</p>
            </div>
            <div>
              <p className="text-xs text-primary-700 font-medium">Tipo</p>
              <p className="text-sm text-primary-900">{searchResult.tipo}</p>
            </div>
          </div>

          <div className="pt-4 border-t border-primary-200">
            <p className="text-xs text-primary-700 mb-2">ID Interno (para download)</p>
            <p className="text-sm text-primary-900 font-mono bg-primary-100 px-3 py-2 rounded">
              {searchResult.internal_id}
            </p>
          </div>
        </div>
      )}

      {/* Download */}
      {searchResult && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">2. Baixar Shapefile</h3>
          
          <div className="flex items-center mb-4">
            <input
              type="checkbox"
              id="force-download"
              checked={force}
              onChange={(e) => setForce(e.target.checked)}
              className="w-4 h-4 text-primary-600 rounded"
            />
            <label htmlFor="force-download" className="ml-2 text-sm text-gray-700">
              Forçar re-download (ignorar cache)
            </label>
          </div>

          <button
            onClick={handleDownload}
            disabled={downloading}
            className="btn-primary w-full flex items-center justify-center"
          >
            <Download className="w-4 h-4 mr-2" />
            {downloading ? 'Iniciando Download...' : 'Iniciar Download'}
          </button>
        </div>
      )}

      {/* Status do Download */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">3. Verificar Status do Download</h3>
        
        <button
          onClick={handleCheckStatus}
          disabled={checkingStatus || !carNumber.trim()}
          className="btn-secondary w-full flex items-center justify-center mb-4"
        >
          <Search className="w-4 h-4 mr-2" />
          {checkingStatus ? 'Verificando...' : 'Verificar Status'}
        </button>

        {downloadStatus && (
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <span className="text-sm font-medium text-gray-700">Status</span>
              {getStatusBadge(downloadStatus.status)}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500">Job ID</p>
                <p className="text-sm font-medium">#{downloadStatus.id}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Estado</p>
                <p className="text-sm font-medium">{downloadStatus.state}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Tentativas</p>
                <p className="text-sm font-medium">{downloadStatus.retry_count}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Tamanho</p>
                <p className="text-sm font-medium">
                  {downloadStatus.file_size
                    ? `${(downloadStatus.file_size / (1024 * 1024)).toFixed(2)} MB`
                    : 'N/A'}
                </p>
              </div>
            </div>

            {downloadStatus.file_path && (
              <div>
                <p className="text-xs text-gray-500 mb-1">Caminho do Arquivo</p>
                <p className="text-sm font-mono bg-gray-100 p-2 rounded break-all">
                  {downloadStatus.file_path}
                </p>
              </div>
            )}

            {downloadStatus.error_message && (
              <div className="p-3 bg-red-50 border border-red-200 rounded">
                <p className="text-xs text-red-700 font-medium mb-1">Erro</p>
                <p className="text-sm text-red-800">{downloadStatus.error_message}</p>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-gray-500">
              <div>
                <p className="font-medium">Criado</p>
                <p>{new Date(downloadStatus.created_at).toLocaleString('pt-BR')}</p>
              </div>
              {downloadStatus.started_at && (
                <div>
                  <p className="font-medium">Iniciado</p>
                  <p>{formatDateTime(downloadStatus.started_at)}</p>
                </div>
              )}
              {downloadStatus.completed_at && (
                <div>
                  <p className="font-medium">Concluído</p>
                  <p>{formatDateTime(downloadStatus.completed_at)}</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Exemplo de Uso */}
      <div className="card bg-blue-50 border-blue-200">
        <h3 className="text-lg font-semibold text-blue-900 mb-3">💡 Exemplo de Uso</h3>
        <div className="space-y-2 text-sm text-blue-800">
          <p>1. Digite um número CAR válido (ex: SP-3538709-E398FD1AAE3E4AAC8E074A6532A3B9FA)</p>
          <p>2. Clique em "Buscar Propriedade" para ver os dados</p>
          <p>3. Clique em "Iniciar Download" para baixar o shapefile</p>
          <p>4. Use "Verificar Status" para acompanhar o progresso</p>
          <p className="pt-2 border-t border-blue-300">
            <strong>Nota:</strong> Downloads CAR individuais são rápidos (30-60 segundos) comparados 
            aos downloads em massa.
          </p>
        </div>
      </div>
    </div>
  )
}
