import { useState, useEffect } from 'react'
import { BarChart3, Download, CheckCircle, XCircle, Clock, TrendingUp } from 'lucide-react'
import { getDownloadStats, DownloadStats as StatsType } from '../api'

export default function Statistics() {
  const [stats, setStats] = useState<StatsType | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStats = async () => {
    try {
      setError(null)
      const response = await getDownloadStats()
      setStats(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Erro ao buscar estatísticas')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStats()
  }, [])

  const calculatePercentage = (value: number, total: number) => {
    if (total === 0) return 0
    return ((value / total) * 100).toFixed(1)
  }

  if (loading) {
    return (
      <div className="card">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card border-red-200 bg-red-50">
        <p className="text-red-700">{error}</p>
        <button onClick={fetchStats} className="btn-primary mt-4">
          Tentar Novamente
        </button>
      </div>
    )
  }

  const successRate = stats
    ? calculatePercentage(stats.completed, stats.completed + stats.failed)
    : 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Estatísticas de Downloads</h2>
        <button onClick={fetchStats} className="btn-secondary flex items-center">
          <TrendingUp className="w-4 h-4 mr-2" />
          Atualizar
        </button>
      </div>

      {/* Cards de Estatísticas */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Total */}
        <div className="card hover:shadow-lg transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total</p>
              <p className="text-3xl font-bold text-gray-900">{stats?.total_jobs || 0}</p>
            </div>
            <Download className="w-10 h-10 text-gray-400" />
          </div>
        </div>

        {/* Concluídos */}
        <div className="card hover:shadow-lg transition-shadow border-green-200 bg-green-50">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-green-700 font-medium">Concluídos</p>
              <p className="text-3xl font-bold text-green-900">{stats?.completed || 0}</p>
              <p className="text-xs text-green-600 mt-1">
                {calculatePercentage(stats?.completed || 0, stats?.total_jobs || 0)}% do total
              </p>
            </div>
            <CheckCircle className="w-10 h-10 text-green-600" />
          </div>
        </div>

        {/* Em Execução */}
        <div className="card hover:shadow-lg transition-shadow border-blue-200 bg-blue-50">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-blue-700 font-medium">Em Execução</p>
              <p className="text-3xl font-bold text-blue-900">{stats?.running || 0}</p>
              <p className="text-xs text-blue-600 mt-1">
                {calculatePercentage(stats?.running || 0, stats?.total_jobs || 0)}% do total
              </p>
            </div>
            <Clock className="w-10 h-10 text-blue-600" />
          </div>
        </div>

        {/* Pendentes */}
        <div className="card hover:shadow-lg transition-shadow border-yellow-200 bg-yellow-50">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-yellow-700 font-medium">Pendentes</p>
              <p className="text-3xl font-bold text-yellow-900">{stats?.pending || 0}</p>
              <p className="text-xs text-yellow-600 mt-1">
                {calculatePercentage(stats?.pending || 0, stats?.total_jobs || 0)}% do total
              </p>
            </div>
            <Clock className="w-10 h-10 text-yellow-600" />
          </div>
        </div>

        {/* Falhados */}
        <div className="card hover:shadow-lg transition-shadow border-red-200 bg-red-50">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-red-700 font-medium">Falhados</p>
              <p className="text-3xl font-bold text-red-900">{stats?.failed || 0}</p>
              <p className="text-xs text-red-600 mt-1">
                {calculatePercentage(stats?.failed || 0, stats?.total_jobs || 0)}% do total
              </p>
            </div>
            <XCircle className="w-10 h-10 text-red-600" />
          </div>
        </div>
      </div>

      {/* Taxa de Sucesso */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Taxa de Sucesso</h3>
          <BarChart3 className="w-6 h-6 text-primary-600" />
        </div>

        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-600">
                {stats?.completed || 0} de {(stats?.completed || 0) + (stats?.failed || 0)} finalizados
              </span>
              <span className="font-bold text-primary-700">{successRate}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
              <div
                className="bg-primary-600 h-4 rounded-full transition-all duration-500"
                style={{ width: `${successRate}%` }}
              ></div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 pt-4 border-t">
            <div className="text-center">
              <p className="text-2xl font-bold text-green-600">{stats?.completed || 0}</p>
              <p className="text-sm text-gray-600">Bem-sucedidos</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-red-600">{stats?.failed || 0}</p>
              <p className="text-sm text-gray-600">Com falha</p>
            </div>
          </div>
        </div>
      </div>

      {/* Distribuição de Status */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Distribuição de Status</h3>
        <div className="space-y-3">
          {[
            { label: 'Concluídos', value: stats?.completed || 0, color: 'bg-green-500' },
            { label: 'Em Execução', value: stats?.running || 0, color: 'bg-blue-500' },
            { label: 'Pendentes', value: stats?.pending || 0, color: 'bg-yellow-500' },
            { label: 'Falhados', value: stats?.failed || 0, color: 'bg-red-500' },
          ].map((item) => (
            <div key={item.label}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-700">{item.label}</span>
                <span className="font-medium">
                  {item.value} ({calculatePercentage(item.value, stats?.total_jobs || 0)}%)
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                <div
                  className={`${item.color} h-2 rounded-full transition-all duration-500`}
                  style={{ width: `${calculatePercentage(item.value, stats?.total_jobs || 0)}%` }}
                ></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Resumo */}
      <div className="card bg-gradient-to-br from-primary-50 to-blue-50 border-primary-200">
        <h3 className="text-lg font-semibold text-primary-900 mb-3">📊 Resumo Geral</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-primary-700">Total de Downloads Iniciados</p>
            <p className="text-2xl font-bold text-primary-900">{stats?.total_jobs || 0}</p>
          </div>
          <div>
            <p className="text-primary-700">Taxa de Sucesso</p>
            <p className="text-2xl font-bold text-primary-900">{successRate}%</p>
          </div>
          <div>
            <p className="text-primary-700">Em Processamento</p>
            <p className="text-2xl font-bold text-primary-900">
              {(stats?.running || 0) + (stats?.pending || 0)}
            </p>
          </div>
          <div>
            <p className="text-primary-700">Finalizados</p>
            <p className="text-2xl font-bold text-primary-900">
              {(stats?.completed || 0) + (stats?.failed || 0)}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
