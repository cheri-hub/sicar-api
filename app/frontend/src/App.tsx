import { useState, useEffect } from 'react'
import { Activity, Download, Calendar, Database, Search, Settings, Wrench, FileText, Key } from 'lucide-react'
import HealthCheck from './components/HealthCheck'
import ReleaseDates from './components/ReleaseDates'
import Downloads from './components/Downloads'
import DownloadByCAR from './components/DownloadByCAR'
import Statistics from './components/Statistics'
import Scheduler from './components/Scheduler'
import SettingsPage from './components/SettingsPage'
import Logs from './components/Logs'
import ApiKeyConfig from './components/ApiKeyConfig'
import { getStoredApiKey } from './api'

type Tab = 'health' | 'releases' | 'downloads' | 'car' | 'stats' | 'scheduler' | 'settings' | 'logs'

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('health')
  const [showApiKeyConfig, setShowApiKeyConfig] = useState(false)
  const [hasApiKey, setHasApiKey] = useState(false)

  useEffect(() => {
    setHasApiKey(!!getStoredApiKey())
  }, [showApiKeyConfig])

  const tabs = [
    { id: 'health' as Tab, label: 'Health Check', icon: Activity },
    { id: 'releases' as Tab, label: 'Datas de Release', icon: Calendar },
    { id: 'downloads' as Tab, label: 'Downloads', icon: Download },
    { id: 'car' as Tab, label: 'Download por CAR', icon: Search },
    { id: 'stats' as Tab, label: 'Estatísticas', icon: Database },
    { id: 'scheduler' as Tab, label: 'Agendador', icon: Settings },
    { id: 'logs' as Tab, label: 'Logs', icon: FileText },
    { id: 'settings' as Tab, label: 'Configurações', icon: Wrench },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
                <Database className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">SICAR API</h1>
                <p className="text-sm text-gray-500">Dashboard de Controle</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={() => setShowApiKeyConfig(true)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  hasApiKey
                    ? 'bg-green-100 text-green-700 hover:bg-green-200'
                    : 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200'
                }`}
                title={hasApiKey ? 'API Key configurada' : 'Configurar API Key'}
              >
                <Key className="w-4 h-4" />
                <span className="hidden sm:inline">{hasApiKey ? 'API Key ✓' : 'API Key'}</span>
              </button>
              <div className="text-right">
                <p className="text-sm text-gray-500">Versão 1.1.0</p>
                <p className="text-xs text-gray-400">Sistema Nacional de Cadastro Ambiental Rural</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8 overflow-x-auto">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm whitespace-nowrap
                    ${activeTab === tab.id
                      ? 'border-primary-600 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }
                  `}
                >
                  <Icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                </button>
              )
            })}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'health' && <HealthCheck />}
        {activeTab === 'releases' && <ReleaseDates />}
        {activeTab === 'downloads' && <Downloads />}
        {activeTab === 'car' && <DownloadByCAR />}
        {activeTab === 'stats' && <Statistics />}
        {activeTab === 'scheduler' && <Scheduler />}
        {activeTab === 'logs' && <Logs />}
        {activeTab === 'settings' && <SettingsPage />}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-sm text-gray-500">
            SICAR API Dashboard - Sistema de Download Automático do SICAR
          </p>
          <p className="text-center text-xs text-gray-400 mt-1">
            Desenvolvido por cheri-hub &copy; 2025
          </p>
        </div>
      </footer>

      {/* API Key Config Modal */}
      {showApiKeyConfig && (
        <ApiKeyConfig onClose={() => setShowApiKeyConfig(false)} />
      )}
    </div>
  )
}

export default App
