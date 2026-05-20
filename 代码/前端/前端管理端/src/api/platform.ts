import http from './request'

export default {
  getDetectionLogs(params: {
    log_scope: 'paper' | 'review' | 'image'
    page?: number
    page_size?: number
    status?: string
    organization?: string
  }) {
    return http.get('/admin/detection-logs/', { params })
  },

  getDetectionModels() {
    return http.get('/admin/detection-models/')
  },

  saveDetectionModels(catalog: Record<string, unknown>) {
    return http.put('/admin/detection-models/', { catalog })
  },

  listReports(params?: { page?: number; page_size?: number; status?: string }) {
    return http.get('/reports/admin/', { params })
  },

  handleReport(reportId: number, data: { action: 'resolved' | 'dismissed'; resolution: string }) {
    return http.post(`/reports/admin/${reportId}/handle/`, data)
  },
}
