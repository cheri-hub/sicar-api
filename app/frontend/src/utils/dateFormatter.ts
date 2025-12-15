/**
 * Utilitário para formatação de datas com fuso horário configurável
 */

/**
 * Obtém o fuso horário configurado pelo usuário
 */
export const getTimezone = (): string => {
  return localStorage.getItem('app_timezone') || 'America/Sao_Paulo'
}

/**
 * Formata uma data ISO string para o fuso horário configurado
 */
export const formatDateTime = (
  isoString: string | null | undefined,
  options?: Intl.DateTimeFormatOptions
): string => {
  if (!isoString) return '-'
  
  const timezone = getTimezone()
  const date = new Date(isoString)
  
  const defaultOptions: Intl.DateTimeFormatOptions = {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    ...options
  }
  
  return date.toLocaleString('pt-BR', defaultOptions)
}

/**
 * Formata a data/hora atual no fuso horário configurado
 */
export const formatCurrentDateTime = (): string => {
  // Usar toISOString() para garantir que estamos trabalhando com UTC
  return formatDateTime(new Date().toISOString())
}

/**
 * Formata apenas a data (sem hora)
 */
export const formatDate = (isoString: string | null | undefined): string => {
  if (!isoString) return '-'
  
  const timezone = getTimezone()
  const date = new Date(isoString)
  
  return date.toLocaleDateString('pt-BR', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

/**
 * Formata apenas a hora
 */
export const formatTime = (isoString: string | null | undefined): string => {
  if (!isoString) return '-'
  
  const timezone = getTimezone()
  const date = new Date(isoString)
  
  return date.toLocaleTimeString('pt-BR', {
    timeZone: timezone,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

/**
 * Hook para escutar mudanças no fuso horário
 */
export const useTimezoneListener = (callback: () => void) => {
  const handleTimezoneChange = () => {
    callback()
  }
  
  window.addEventListener('timezoneChange', handleTimezoneChange)
  
  return () => {
    window.removeEventListener('timezoneChange', handleTimezoneChange)
  }
}
