import { useState, useEffect } from 'react'
import { Calendar, RefreshCw, MapPin } from 'lucide-react'
import { getReleases, updateReleases, ReleasesResponse } from '../api'
import { formatDateTime } from '../utils/dateFormatter'

export default function ReleaseDates() {
  const [releases, setReleases] = useState<ReleasesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')

  const fetchReleases = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await getReleases()
      setReleases(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Erro ao buscar datas de release')
    } finally {
      setLoading(false)
    }
  }

  const handleUpdate = async () => {
    try {
      setUpdating(true)
      setError(null)
      await updateReleases()
      await fetchReleases()
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Erro ao atualizar datas')
    } finally {
      setUpdating(false)
    }
  }

  useEffect(() => {
    fetchReleases()
  }, [])

  const filteredReleases = releases?.releases.filter((release) =>
    release.state.toLowerCase().includes(searchTerm.toLowerCase())
  ) || []

  if (loading) {
    return (
      <div className="card">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Datas de Release por Estado</h2>
          <p className="text-gray-600 mt-1">
            Consulte quando os dados de cada estado foram disponibilizados no SICAR
          </p>
        </div>
        <button
          onClick={handleUpdate}
          disabled={updating}
          className="btn-primary flex items-center"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${updating ? 'animate-spin' : ''}`} />
          {updating ? 'Atualizando...' : 'Atualizar Datas'}
        </button>
      </div>

      {error && (
        <div className="card border-red-200 bg-red-50">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {/* Resumo */}
      <div className="card">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500">Total de Estados</p>
            <p className="text-3xl font-bold text-gray-900">{releases?.count || 0}</p>
          </div>
          <Calendar className="w-12 h-12 text-primary-600" />
        </div>
      </div>

      {/* Busca */}
      <div className="card">
        <input
          type="text"
          placeholder="Buscar estado (ex: SP, MG, RJ...)"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="input"
        />
      </div>

      {/* Lista de Estados */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredReleases.map((release) => (
          <div key={release.state} className="card hover:shadow-lg transition-shadow">
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                  <MapPin className="w-5 h-5 text-primary-600" />
                </div>
                <div>
                  <h3 className="font-bold text-lg">{release.state}</h3>
                  <p className="text-sm text-gray-500">Estado</p>
                </div>
              </div>
            </div>
            <div className="mt-4 space-y-2">
              <div>
                <p className="text-xs text-gray-500">Data de Release</p>
                <p className="font-semibold text-primary-700">{release.release_date}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Última Verificação</p>
                <p className="text-sm text-gray-600">
                  {formatDateTime(release.last_checked)}
                </p>
              </div>
              {release.last_download && (
                <div>
                  <p className="text-xs text-gray-500">Último Download</p>
                  <p className="text-sm text-green-700 font-medium">
                    {formatDateTime(release.last_download)}
                  </p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {filteredReleases.length === 0 && (
        <div className="card text-center py-12">
          <p className="text-gray-500">Nenhum estado encontrado</p>
        </div>
      )}
    </div>
  )
}
