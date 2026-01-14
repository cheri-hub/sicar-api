import { useState, useEffect } from 'react'
import { Key, Save, X, Eye, EyeOff, Check } from 'lucide-react'
import { getStoredApiKey, setStoredApiKey, clearStoredApiKey } from '../api'

interface ApiKeyConfigProps {
  onClose: () => void
}

export default function ApiKeyConfig({ onClose }: ApiKeyConfigProps) {
  const [apiKey, setApiKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const storedKey = getStoredApiKey()
    if (storedKey) {
      setApiKey(storedKey)
    }
  }, [])

  const handleSave = () => {
    if (apiKey.trim()) {
      setStoredApiKey(apiKey.trim())
      setSaved(true)
      setTimeout(() => {
        setSaved(false)
        onClose()
      }, 1000)
    }
  }

  const handleClear = () => {
    clearStoredApiKey()
    setApiKey('')
    setSaved(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSave()
    } else if (e.key === 'Escape') {
      onClose()
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md mx-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Key className="w-5 h-5 text-primary-600" />
            <h2 className="text-lg font-semibold text-gray-900">Configurar API Key</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-sm text-gray-600 mb-4">
          A API Key é necessária para operações que modificam dados (downloads, atualizações, etc.).
          Consultas de leitura funcionam sem autenticação.
        </p>

        <div className="space-y-4">
          <div>
            <label htmlFor="apiKey" className="block text-sm font-medium text-gray-700 mb-1">
              API Key
            </label>
            <div className="relative">
              <input
                id="apiKey"
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Insira sua API Key"
                className="input pr-10"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showKey ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={!apiKey.trim()}
              className={`btn flex-1 flex items-center justify-center gap-2 ${
                saved ? 'bg-green-600 hover:bg-green-700' : ''
              }`}
            >
              {saved ? (
                <>
                  <Check className="w-4 h-4" />
                  Salvo!
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  Salvar
                </>
              )}
            </button>
            <button
              onClick={handleClear}
              className="btn-secondary flex items-center justify-center gap-2"
            >
              <X className="w-4 h-4" />
              Limpar
            </button>
          </div>
        </div>

        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-xs text-yellow-800">
            <strong>Nota:</strong> A API Key é armazenada apenas no seu navegador (localStorage).
            Ela será enviada automaticamente em todas as requisições à API.
          </p>
        </div>
      </div>
    </div>
  )
}
