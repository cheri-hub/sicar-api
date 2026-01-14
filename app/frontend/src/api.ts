import axios from 'axios'

const API_BASE_URL = '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface HealthResponse {
  status: string
  database: string
  scheduler: string
  active_jobs: number
  version: string
}

export interface ReleaseDate {
  state: string
  release_date: string
  last_checked: string
  last_download: string | null
}

export interface ReleasesResponse {
  count: number
  releases: ReleaseDate[]
}

export interface DownloadJob {
  id: number
  state: string
  polygon: string
  status: string
  file_path: string | null
  file_size: number | null
  error_message: string | null
  retry_count: number
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface DownloadsResponse {
  count: number
  downloads: DownloadJob[]
}

export interface DownloadStats {
  total_jobs: number
  completed: number
  failed: number
  running: number
  pending: number
  total_size_bytes: number
  total_size_mb: number
}

export interface PropertyData {
  internal_id: string
  car_number: string
  codigo: string
  area: number
  status: string
  tipo: string
  municipio: string
  uf: string
  geometry: any
}

export interface SchedulerJob {
  id: string
  name: string
  next_run_time: string | null
  trigger: string
  paused: boolean
}

export interface SchedulerJobsResponse {
  jobs: SchedulerJob[]
}

export interface ScheduledTask {
  id: number
  task_name: string
  task_type: string
  status: string
  result: string | null
  error_message: string | null
  duration_seconds: number | null
  started_at: string
  completed_at: string | null
}

export interface ScheduledTasksResponse {
  count: number
  tasks: ScheduledTask[]
}

// Health Check
export const getHealth = () => api.get<HealthResponse>('/health')

// Releases
export const getReleases = () => api.get<ReleasesResponse>('/releases')
export const updateReleases = () => api.post('/releases/update')

// Downloads
export const createStateDownload = (data: { state: string; polygons: string[] }) =>
  api.post('/downloads/state', data)

export const getDownloads = (params?: { status?: string; limit?: number; offset?: number }) =>
  api.get<DownloadsResponse>('/downloads', { params })

export const getDownload = (id: number) => api.get<DownloadJob>(`/downloads/${id}`)

export const getDownloadStats = () => api.get<DownloadStats>('/downloads/stats')

// CAR Downloads
export const searchCAR = (carNumber: string) =>
  api.get<PropertyData>(`/search/car/${carNumber}`)

export const downloadByCAR = (data: { car_number: string; force?: boolean }) =>
  api.post('/downloads/car', data)

export const getDownloadByCAR = (carNumber: string) =>
  api.get<DownloadJob>(`/downloads/car/${carNumber}`)

// Scheduler
export const getSchedulerJobs = () => api.get<SchedulerJobsResponse>('/scheduler/jobs')

export const runSchedulerJob = (jobName: string) =>
  api.post(`/scheduler/jobs/${jobName}/run`)

export const pauseSchedulerJob = (jobName: string) =>
  api.post(`/scheduler/jobs/${jobName}/pause`)

export const resumeSchedulerJob = (jobName: string) =>
  api.post(`/scheduler/jobs/${jobName}/resume`)

export const rescheduleJob = (
  jobName: string,
  scheduleType: 'daily' | 'weekly' | 'interval',
  options: {
    hour?: number
    minute?: number
    day_of_week?: string
    interval_hours?: number
    interval_minutes?: number
  }
) => api.post(`/scheduler/jobs/${jobName}/reschedule`, {
  schedule_type: scheduleType,
  ...options
})

export const getScheduledTasks = (params?: { limit?: number }) =>
  api.get<ScheduledTasksResponse>('/scheduler/tasks', { params })

// Alias for logs component
export const getTasks = async (limit?: number) => {
  const response = await getScheduledTasks({ limit })
  return response.data
}

// Settings
export const getSettings = () =>
  api.get<{ settings: Record<string, any> }>('/settings')

export const getSetting = (key: string) =>
  api.get<{ key: string; value: any; description?: string; updated_at?: string }>(`/settings/${key}`)

export const updateSetting = (key: string, value: any, description?: string) =>
  api.put(`/settings/${key}`, { value, description })

export default api
