import http from './request'
import publisherApi from './publisher'

export type CreateManualReviewBody = {
  detection_task_id: string
  task_type: string
  reason: string
  priority?: 'normal' | 'urgent'
  batch_session_id?: string
}

/** POST /manual-review-requests/ — 发布者发起人工审核申请 */
export function createManualReviewRequest(body: CreateManualReviewBody) {
  return http.post('/manual-review-requests/', {
    detection_task_id: body.detection_task_id.trim(),
    task_type: body.task_type,
    reason: body.reason.trim(),
    priority: body.priority ?? 'normal',
    batch_session_id: body.batch_session_id?.trim() || undefined,
  })
}

export function listPublisherManualReviewApplications(params: {
  page?: number
  page_size?: number
  status?: string
  startTime?: string
  endTime?: string
}) {
  return publisherApi.getPublisherReviewTasks(params)
}

export function getManualReviewApplicationByDetectionTask(detection_task_id: string) {
  return http.get('/manual-review-requests/by-detection-task/', {
    params: { detection_task_id },
  })
}

export function getPublisherManualReviewSummary(review_request_id: number) {
  return http.get(`/manual-review-requests/${review_request_id}/publisher-summary/`)
}
