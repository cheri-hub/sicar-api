import { useState, useEffect } from 'react'
import { Settings, Clock, Save, RotateCcw } from 'lucide-react'
import { getSettings, updateSetting } from '../api'

const TIMEZONES = [
  { value: 'America/Sao_Paulo', label: 'Brasília (BRT - UTC-3)' },
  { value: 'America/Manaus', label: 'Manaus (AMT - UTC-4)' },
  { value: 'America/Rio_Branco', label: 'Acre (ACT - UTC-5)' },
  { value: 'America/Noronha', label: 'Fernando de Noronha (FNT - UTC-2)' },
  { value: 'UTC', label: 'UTC (Horário Universal)' },
  { value: 'America/New_York', label: 'Nova York (EST - UTC-5)' },
  { value: 'Europe/London', label: 'Londres (GMT - UTC+0)' },
  { value: 'Europe/Paris', label: 'Paris (CET - UTC+1)' },
  { value: 'Asia/Tokyo', label: 'Tóquio (JST - UTC+9)' },
]

export default function SettingsPage() {
  const [timezone, setTimezone] = useState('America/Sao_Paulo')
  const [saved, setSaved] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      // Tentar carregar do backend primeiro
      const response = await getSettings()
      const backendTimezone = response.data.settings?.timezone
      
      if (backendTimezone) {
        setTimezone(backendTimezone)
        localStorage.setItem('app_timezone', backendTimezone)
      } else {
        // Fallback para localStorage se não houver no backend
        const savedTimezone = localStorage.getItem('app_timezone')
        if (savedTimezone) {
          setTimezone(savedTimezone)
        }
      }
    } catch (error) {
      console.error('Erro ao carregar configurações:', error)
      // Fallback para localStorage em caso de erro
      const savedTimezone = localStorage.getItem('app_timezone')
      if (savedTimezone) {
        setTimezone(savedTimezone)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      // Salvar no backend
      await updateSetting('timezone', timezone, 'Fuso horário para exibição de datas')
      
      // Salvar no localStorage também (para acesso rápido)
      localStorage.setItem('app_timezone', timezone)
      
      setSaved(true)
      
      // Disparar evento customizado para notificar outros componentes
      window.dispatchEvent(new CustomEvent('timezoneChange', { detail: timezone }))
      
      setTimeout(() => setSaved(false), 3000)
    } catch (error) {
      console.error('Erro ao salvar configurações:', error)
      alert('Erro ao salvar configurações no servidor')
    }
  }

  const handleReset = async () => {
    const defaultTimezone = 'America/Sao_Paulo'
    try {
      // Resetar no backend
      await updateSetting('timezone', defaultTimezone, 'Fuso horário para exibição de datas')
      
      setTimezone(defaultTimezone)
      localStorage.setItem('app_timezone', defaultTimezone)
      window.dispatchEvent(new CustomEvent('timezoneChange', { detail: defaultTimezone }))
      
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (error) {
      console.error('Erro ao resetar configurações:', error)
      // Fazer reset local mesmo em caso de erro
      setTimezone(defaultTimezone)
      localStorage.setItem('app_timezone', defaultTimezone)
      window.dispatchEvent(new CustomEvent('timezoneChange', { detail: defaultTimezone }))
    }
  }

  const getCurrentTime = () => {
    const now = new Date()
    return now.toLocaleString('pt-BR', { 
      timeZone: timezone,
      dateStyle: 'full',
      timeStyle: 'long'
    })
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Configurações</h2>
        <p className="text-gray-600 mt-1">
          Personalize o comportamento do sistema
        </p>
      </div>

      {loading && (
        <div className="card">
          <p className="text-gray-600">Carregando configurações...</p>
        </div>
      )}

      {saved && (
        <div className="card border-green-200 bg-green-50">
          <div className="flex items-center">
            <Save className="w-5 h-5 text-green-600 mr-2" />
            <p className="text-green-700">Configurações salvas com sucesso no banco de dados!</p>
          </div>
        </div>
      )}

      {/* Fuso Horário */}
      <div className="card">
        <div className="flex items-center mb-4">
          <Clock className="w-6 h-6 text-primary-600 mr-3" />
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Fuso Horário</h3>
            <p className="text-sm text-gray-600">Configure como as datas e horários são exibidos</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="label">Fuso Horário de Exibição</label>
            <select
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className="input"
            >
              {TIMEZONES.map((tz) => (
                <option key={tz.value} value={tz.value}>
                  {tz.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Todas as datas e horários serão convertidos para este fuso horário
            </p>
          </div>

          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-900 font-medium mb-1">Horário atual no fuso selecionado:</p>
            <p className="text-lg text-blue-700 font-mono">{getCurrentTime()}</p>
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleSave}
              className="btn-primary flex items-center"
            >
              <Save className="w-4 h-4 mr-2" />
              Salvar Configurações
            </button>
            <button
              onClick={handleReset}
              className="btn-secondary flex items-center"
            >
              <RotateCcw className="w-4 h-4 mr-2" />
              Restaurar Padrão
            </button>
          </div>
        </div>
      </div>

      {/* Informações */}
      <div className="card bg-gray-50 border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
          <Settings className="w-5 h-5 mr-2" />
          ℹ️ Sobre as Configurações
        </h3>
        <div className="space-y-2 text-sm text-gray-700">
          <p>
            <strong>Fuso Horário:</strong> Os dados são armazenados em UTC (horário universal) no banco de dados. 
            Ao selecionar um fuso horário aqui, você está apenas alterando como as datas e horas são exibidas na interface.
          </p>
          <p>
            <strong>Recomendação:</strong> Use o fuso de Brasília (BRT) se estiver no Brasil, ou UTC se quiser ver os horários sem conversão.
          </p>
          <p className="pt-2 border-t border-gray-300">
            � <strong>Persistência:</strong> As configurações são salvas no banco de dados e sincronizadas entre sessões e dispositivos.
          </p>
        </div>
      </div>

      {/* Placeholder para futuras configurações */}
      <div className="card border-dashed border-2 border-gray-300 bg-gray-50">
        <div className="text-center py-8">
          <Settings className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-gray-600 mb-2">Mais Configurações em Breve</h3>
          <p className="text-sm text-gray-500">
            Novas opções de personalização serão adicionadas aqui no futuro
          </p>
        </div>
      </div>
    </div>
  )
}
