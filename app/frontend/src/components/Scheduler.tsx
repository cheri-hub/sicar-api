import { useState, useEffect } from 'react'
import { Settings, Play, RefreshCw, Clock, CheckCircle, XCircle, AlertTriangle, Pause, PlayCircle, Edit2, ChevronDown, ChevronUp } from 'lucide-react'
import { getSchedulerJobs, runSchedulerJob, pauseSchedulerJob, resumeSchedulerJob, rescheduleJob, getScheduledTasks, SchedulerJob, ScheduledTask } from '../api'
import { formatDateTime } from '../utils/dateFormatter'

export default function Scheduler() {
  const [jobs, setJobs] = useState<SchedulerJob[]>([])
  const [tasks, setTasks] = useState<ScheduledTask[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [runningJob, setRunningJob] = useState<string | null>(null)
  const [editingJob, setEditingJob] = useState<string | null>(null)
  const [expandedJob, setExpandedJob] = useState<string | null>(null)
  
  // Configurações de agendamento
  const [scheduleType, setScheduleType] = useState<'daily' | 'weekly' | 'interval'>('daily')
  const [hour, setHour] = useState('02')
  const [minute, setMinute] = useState('00')
  const [dayOfWeek, setDayOfWeek] = useState('mon')
  const [intervalHours, setIntervalHours] = useState('')
  const [intervalMinutes, setIntervalMinutes] = useState('')

  // Descrições dos jobs
  const jobDescriptions: Record<string, string> = {
    'daily_sicar_collection': 'Coleta diária automática de dados do SICAR. Verifica datas de release, identifica estados com novos dados disponíveis e realiza downloads dos shapefiles configurados.',
    'check_release_dates': 'Verifica e atualiza as datas de release de todos os estados brasileiros no SICAR, identificando quando novos dados são disponibilizados.',
    'update_release_dates': 'Verifica e atualiza as datas de release de todos os estados brasileiros no SICAR, identificando quando novos dados são disponibilizados.'
  }

  const fetchData = async () => {
    try {
      setError(null)
      const [jobsResponse, tasksResponse] = await Promise.all([
        getSchedulerJobs(),
        getScheduledTasks({ limit: 20 })
      ])
      setJobs(jobsResponse.data.jobs)
      setTasks(tasksResponse.data.tasks)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Erro ao buscar dados do agendador')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [])

  const handleRunJob = async (jobId: string) => {
    try {
      setRunningJob(jobId)
      setError(null)
      await runSchedulerJob(jobId)
      await fetchData()
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Erro ao executar job')
    } finally {
      setRunningJob(null)
    }
  }

  const handlePauseJob = async (jobId: string) => {
    try {
      setError(null)
      await pauseSchedulerJob(jobId)
      await fetchData()
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Erro ao pausar job')
    }
  }

  const handleResumeJob = async (jobId: string) => {
    try {
      setError(null)
      await resumeSchedulerJob(jobId)
      await fetchData()
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Erro ao resumir job')
    }
  }

  const handleReschedule = async (jobId: string) => {
    try {
      setError(null)
      
      const options: any = {}
      
      if (scheduleType === 'daily') {
        const h = parseInt(hour)
        const m = parseInt(minute)
        
        if (isNaN(h) || h < 0 || h > 23) {
          setError('Hora deve estar entre 0 e 23')
          return
        }
        
        if (isNaN(m) || m < 0 || m > 59) {
          setError('Minuto deve estar entre 0 e 59')
          return
        }
        
        options.hour = h
        options.minute = m
        
      } else if (scheduleType === 'weekly') {
        const h = parseInt(hour)
        const m = parseInt(minute)
        
        if (isNaN(h) || h < 0 || h > 23) {
          setError('Hora deve estar entre 0 e 23')
          return
        }
        
        if (isNaN(m) || m < 0 || m > 59) {
          setError('Minuto deve estar entre 0 e 59')
          return
        }
        
        options.hour = h
        options.minute = m
        options.day_of_week = dayOfWeek
        
      } else if (scheduleType === 'interval') {
        const hours = intervalHours ? parseInt(intervalHours) : null
        const minutes = intervalMinutes ? parseInt(intervalMinutes) : null
        
        if (!hours && !minutes) {
          setError('Especifique pelo menos horas ou minutos')
          return
        }
        
        if (hours !== null && (isNaN(hours) || hours < 1)) {
          setError('Horas deve ser maior que 0')
          return
        }
        
        if (minutes !== null && (isNaN(minutes) || minutes < 1)) {
          setError('Minutos deve ser maior que 0')
          return
        }
        
        if (hours) options.interval_hours = hours
        if (minutes) options.interval_minutes = minutes
      }
      
      await rescheduleJob(jobId, scheduleType, options)
      setEditingJob(null)
      await fetchData()
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Erro ao reagendar job')
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
            <CheckCircle className="w-3 h-3 mr-1" />
            Concluído
          </span>
        )
      case 'failed':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
            <XCircle className="w-3 h-3 mr-1" />
            Falhou
          </span>
        )
      case 'running':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            <Clock className="w-3 h-3 mr-1 animate-pulse" />
            Executando
          </span>
        )
      default:
        return <span className="badge">{status}</span>
    }
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Agendador de Tarefas</h2>
        <button onClick={fetchData} className="btn-secondary flex items-center">
          <RefreshCw className="w-4 h-4 mr-2" />
          Atualizar
        </button>
      </div>

      {error && (
        <div className="card border-red-200 bg-red-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <AlertTriangle className="w-5 h-5 text-red-600 mr-2" />
              <p className="text-red-700">{error}</p>
            </div>
            <button onClick={() => setError(null)} className="text-red-600 hover:text-red-800">
              <XCircle className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}

      {/* Jobs Agendados */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4 flex items-center">
          <Settings className="w-5 h-5 mr-2 text-primary-600" />
          Jobs Configurados
        </h3>

        <div className="space-y-3">
          {jobs.length === 0 ? (
            <p className="text-center text-gray-500 py-8">Nenhum job configurado</p>
          ) : (
            jobs.map((job) => (
              <div
                key={job.id}
                className={`p-4 border rounded-lg hover:shadow-md transition-shadow ${
                  job.paused ? 'border-gray-300 bg-gray-50' : 'border-gray-200'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-semibold text-gray-900">{job.name}</h4>
                      {job.paused && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-200 text-gray-700">
                          <Pause className="w-3 h-3 mr-1" />
                          Pausado
                        </span>
                      )}
                      {editingJob !== job.id && (
                        <button
                          onClick={(e) => {
                            e.preventDefault()
                            e.stopPropagation()
                            setExpandedJob(expandedJob === job.id ? null : job.id)
                          }}
                          className="text-gray-500 hover:text-gray-700 ml-2 p-1"
                          title={expandedJob === job.id ? "Ocultar descrição" : "Ver descrição"}
                          type="button"
                        >
                          {expandedJob === job.id ? (
                            <ChevronUp className="w-4 h-4" />
                          ) : (
                            <ChevronDown className="w-4 h-4" />
                          )}
                        </button>
                      )}
                    </div>
                    
                    {/* Descrição expandida */}
                    {expandedJob === job.id && editingJob !== job.id && jobDescriptions[job.id] && (
                      <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded text-sm text-blue-900">
                        <p className="font-medium text-xs text-blue-700 mb-1">O que faz:</p>
                        <p>{jobDescriptions[job.id]}</p>
                      </div>
                    )}
                    {editingJob === job.id ? (
                      <div className="mt-3 space-y-3 max-w-2xl">
                        {/* Tipo de Agendamento */}
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Tipo de Agendamento
                          </label>
                          <div className="flex gap-2">
                            <button
                              onClick={() => setScheduleType('daily')}
                              className={`px-3 py-1 text-sm rounded ${
                                scheduleType === 'daily'
                                  ? 'bg-primary-600 text-white'
                                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                              }`}
                            >
                              Diário
                            </button>
                            <button
                              onClick={() => setScheduleType('weekly')}
                              className={`px-3 py-1 text-sm rounded ${
                                scheduleType === 'weekly'
                                  ? 'bg-primary-600 text-white'
                                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                              }`}
                            >
                              Semanal
                            </button>
                            <button
                              onClick={() => setScheduleType('interval')}
                              className={`px-3 py-1 text-sm rounded ${
                                scheduleType === 'interval'
                                  ? 'bg-primary-600 text-white'
                                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                              }`}
                            >
                              Intervalo
                            </button>
                          </div>
                        </div>

                        {/* Configuração Diária */}
                        {scheduleType === 'daily' && (
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Horário (todos os dias)
                            </label>
                            <div className="flex items-center gap-2">
                              <input
                                type="number"
                                min="0"
                                max="23"
                                value={hour}
                                onChange={(e) => setHour(e.target.value)}
                                className="w-16 px-2 py-1 border border-gray-300 rounded text-center"
                                placeholder="HH"
                              />
                              <span className="text-gray-600">:</span>
                              <input
                                type="number"
                                min="0"
                                max="59"
                                value={minute}
                                onChange={(e) => setMinute(e.target.value)}
                                className="w-16 px-2 py-1 border border-gray-300 rounded text-center"
                                placeholder="MM"
                              />
                            </div>
                          </div>
                        )}

                        {/* Configuração Semanal */}
                        {scheduleType === 'weekly' && (
                          <div className="space-y-2">
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                Dia da Semana
                              </label>
                              <select
                                value={dayOfWeek}
                                onChange={(e) => setDayOfWeek(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded"
                              >
                                <option value="mon">Segunda-feira</option>
                                <option value="tue">Terça-feira</option>
                                <option value="wed">Quarta-feira</option>
                                <option value="thu">Quinta-feira</option>
                                <option value="fri">Sexta-feira</option>
                                <option value="sat">Sábado</option>
                                <option value="sun">Domingo</option>
                              </select>
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                Horário
                              </label>
                              <div className="flex items-center gap-2">
                                <input
                                  type="number"
                                  min="0"
                                  max="23"
                                  value={hour}
                                  onChange={(e) => setHour(e.target.value)}
                                  className="w-16 px-2 py-1 border border-gray-300 rounded text-center"
                                  placeholder="HH"
                                />
                                <span className="text-gray-600">:</span>
                                <input
                                  type="number"
                                  min="0"
                                  max="59"
                                  value={minute}
                                  onChange={(e) => setMinute(e.target.value)}
                                  className="w-16 px-2 py-1 border border-gray-300 rounded text-center"
                                  placeholder="MM"
                                />
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Configuração por Intervalo */}
                        {scheduleType === 'interval' && (
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              Repetir a cada
                            </label>
                            <div className="flex items-center gap-2">
                              <input
                                type="number"
                                min="1"
                                value={intervalHours}
                                onChange={(e) => setIntervalHours(e.target.value)}
                                className="w-20 px-2 py-1 border border-gray-300 rounded text-center"
                                placeholder="0"
                              />
                              <span className="text-gray-600">horas</span>
                              <input
                                type="number"
                                min="1"
                                value={intervalMinutes}
                                onChange={(e) => setIntervalMinutes(e.target.value)}
                                className="w-20 px-2 py-1 border border-gray-300 rounded text-center"
                                placeholder="0"
                              />
                              <span className="text-gray-600">minutos</span>
                            </div>
                            <p className="text-xs text-gray-500 mt-1">
                              Especifique pelo menos horas ou minutos
                            </p>
                          </div>
                        )}

                        <div className="flex gap-2 pt-2">
                          <button
                            onClick={() => handleReschedule(job.id)}
                            className="btn-primary text-sm py-1 px-4"
                          >
                            Salvar Configuração
                          </button>
                          <button
                            onClick={() => setEditingJob(null)}
                            className="btn-secondary text-sm py-1 px-4"
                          >
                            Cancelar
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="mt-2 space-y-1 text-sm text-gray-600">
                        <div className="flex items-center">
                          <Clock className="w-4 h-4 mr-2" />
                          <span>
                            Próxima Execução:{' '}
                            {job.paused ? (
                              <span className="text-gray-500 italic">Pausado</span>
                            ) : job.next_run_time ? (
                              formatDateTime(job.next_run_time)
                            ) : (
                              'Não agendado'
                            )}
                          </span>
                        </div>
                        <div className="flex items-center">
                          <Settings className="w-4 h-4 mr-2" />
                          <span>Agendamento: {job.trigger}</span>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex flex-col gap-2 ml-4">
                    {editingJob !== job.id && (
                      <>
                        <button
                          onClick={() => handleRunJob(job.id)}
                          disabled={runningJob === job.id}
                          className="btn-primary flex items-center text-sm py-1 px-3 whitespace-nowrap"
                        >
                          <Play className={`w-3 h-3 mr-1 ${runningJob === job.id ? 'animate-pulse' : ''}`} />
                          {runningJob === job.id ? 'Executando...' : 'Executar Agora'}
                        </button>
                        
                        {job.paused ? (
                          <button
                            onClick={() => handleResumeJob(job.id)}
                            className="btn-secondary flex items-center text-sm py-1 px-3 whitespace-nowrap"
                          >
                            <PlayCircle className="w-3 h-3 mr-1" />
                            Ativar
                          </button>
                        ) : (
                          <button
                            onClick={() => handlePauseJob(job.id)}
                            className="btn-secondary flex items-center text-sm py-1 px-3 whitespace-nowrap"
                          >
                            <Pause className="w-3 h-3 mr-1" />
                            Pausar
                          </button>
                        )}
                        
                        <button
                          onClick={() => {
                            setEditingJob(job.id)
                            setExpandedJob(null)
                            // Resetar valores
                            setScheduleType('daily')
                            setHour('02')
                            setMinute('00')
                            setDayOfWeek('mon')
                            setIntervalHours('')
                            setIntervalMinutes('')
                          }}
                          className="btn-secondary flex items-center text-sm py-1 px-3 whitespace-nowrap"
                        >
                          <Edit2 className="w-3 h-3 mr-1" />
                          Configurar
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Histórico de Execuções */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Histórico de Execuções</h3>

        {tasks.length === 0 ? (
          <p className="text-center text-gray-500 py-8">Nenhuma execução registrada</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Job
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Início
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Conclusão
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Duração
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {tasks.map((task) => {
                  return (
                    <tr key={task.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {task.task_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(task.status)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDateTime(task.started_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDateTime(task.completed_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {task.duration_seconds ? `${task.duration_seconds}s` : '-'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="card bg-blue-50 border-blue-200">
        <h3 className="text-lg font-semibold text-blue-900 mb-3">ℹ️ Tipos de Agendamento</h3>
        <div className="space-y-2 text-sm text-blue-800">
          <p>
            <strong>Diário:</strong> Executa todos os dias em um horário específico (ex: 02:00)
          </p>
          <p>
            <strong>Semanal:</strong> Executa uma vez por semana em dia e horário específicos (ex: Segunda às 10:00)
          </p>
          <p>
            <strong>Intervalo:</strong> Executa repetidamente a cada X horas/minutos (ex: a cada 6 horas)
          </p>
          <p className="pt-2 border-t border-blue-300">
            💡 <strong>Dica:</strong> Jobs pausados não executarão automaticamente, mas podem ser executados manualmente.
          </p>
        </div>
      </div>
    </div>
  )
}
