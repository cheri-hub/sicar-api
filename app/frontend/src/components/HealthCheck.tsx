import { useState, useEffect } from 'react'
import { Activity, CheckCircle, XCircle, Database, Calendar } from 'lucide-react'
import { getHealth, HealthResponse } from '../api'
import { formatCurrentDateTime } from '../utils/dateFormatter'

export default function HealthCheck() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchHealth = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await getHealth()
      setHealth(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Erro ao verificar saúde da API')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHealth()
    const interval = setInterval(fetchHealth, 10000) // Atualiza a cada 10s
    return () => clearInterval(interval)
  }, [])

  const getStatusColor = (status: string) => {
    return status === 'healthy' || status === 'running' ? 'text-green-600' : 'text-red-600'
  }

  const getStatusIcon = (status: string) => {
    const Icon = status === 'healthy' || status === 'running' ? CheckCircle : XCircle
    return <Icon className="w-12 h-12" />
  }

  if (loading && !health) {
    return (
      <div className="card">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          <span className="ml-3 text-gray-600">Verificando saúde da API...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card border-red-200 bg-red-50">
        <div className="flex items-center">
          <XCircle className="w-6 h-6 text-red-600 mr-3" />
          <div>
            <h3 className="font-semibold text-red-900">Erro de Conexão</h3>
            <p className="text-sm text-red-700">{error}</p>
          </div>
        </div>
        <button onClick={fetchHealth} className="btn-primary mt-4">
          Tentar Novamente
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Health Check</h2>
        <button onClick={fetchHealth} className="btn-secondary flex items-center">
          <Activity className="w-4 h-4 mr-2" />
          Atualizar
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Status Geral */}
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Status Geral</p>
              <p className={`text-2xl font-bold ${getStatusColor(health?.status || '')}`}>
                {health?.status === 'healthy' ? 'Saudável' : 'Com Problemas'}
              </p>
            </div>
            {health && (
              <div className={getStatusColor(health.status)}>
                {getStatusIcon(health.status)}
              </div>
            )}
          </div>
        </div>

        {/* Banco de Dados */}
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Banco de Dados</p>
              <p className={`text-2xl font-bold ${getStatusColor(health?.database || '')}`}>
                {health?.database === 'healthy' ? 'Conectado' : 'Desconectado'}
              </p>
            </div>
            <Database className={`w-12 h-12 ${getStatusColor(health?.database || '')}`} />
          </div>
        </div>

        {/* Agendador */}
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Agendador</p>
              <p className={`text-2xl font-bold ${getStatusColor(health?.scheduler || '')}`}>
                {health?.scheduler === 'running' ? 'Rodando' : 'Parado'}
              </p>
              {health?.active_jobs !== undefined && (
                <p className="text-sm text-gray-500 mt-1">
                  {health.active_jobs} job{health.active_jobs !== 1 ? 's' : ''} ativo{health.active_jobs !== 1 ? 's' : ''}
                </p>
              )}
            </div>
            <Calendar className={`w-12 h-12 ${getStatusColor(health?.scheduler || '')}`} />
          </div>
        </div>
      </div>

      {/* Informações Adicionais */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Informações do Sistema</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-500">Versão da API</p>
            <p className="font-medium">{health?.version}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Última Verificação</p>
            <p className="font-medium">{formatCurrentDateTime()}</p>
          </div>
        </div>
      </div>

      {/* Endpoints Disponíveis */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Documentação da API</h3>
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between py-2">
            <div>
              <p className="text-gray-900 font-medium">Swagger UI</p>
              <p className="text-gray-500 text-xs">Documentação interativa com teste de endpoints</p>
            </div>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              Abrir →
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
