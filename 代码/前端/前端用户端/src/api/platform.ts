import http from './request'

export default {
  getCommunityFeedback(params?: { page?: number; page_size?: number }) {
    return http.get('/community-feedback/', { params })
  },

  getComprehensiveReport(taskId: string | number) {
    return http.get(`/tasks/${taskId}/comprehensive-report/`)
  },

  downloadComprehensiveReport(taskId: string | number) {
    return http.get(`/tasks/${taskId}/comprehensive-report/download/`, { responseType: 'blob' })
  },

  getBatchFusion(data: { batch_session_id?: string; task_ids?: number[] }) {
    if (data.task_ids?.length) {
      return http.post('/batch-fusion/', data)
    }
    return http.get('/batch-fusion/', { params: data })
  },

  getDetectionModels() {
    return http.get('/detection-models/')
  },

  updateDetectionPreferences(data: {
    mode: 'fast' | 'precise'
    text_model_version?: string
    image_model_version?: string
    review_model_version?: string
  }) {
    return http.put('/detection-preferences/', data)
  },

  submitFeedback(data: { manual_review_id: number; is_like?: boolean; comment?: string }) {
    return http.post('/feedback/', data)
  },

  listFeedback(manualReviewId: number) {
    return http.get(`/feedback/${manualReviewId}/`)
  },

  submitReport(data: {
    target_type: string
    target_id: number
    report_type?: string
    reason: string
  }) {
    return http.post('/reports/submit/', data)
  },

  cancelManualReview(reviewRequestId: number) {
    return http.post(`/manual-review-requests/${reviewRequestId}/cancel/`)
  },
}
