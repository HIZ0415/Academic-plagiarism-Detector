import http from './request'
import publisherApi from './publisher'
import * as workflowMock from '@workflow-mock'

export type CreateManualReviewBody = {
  detection_task_id: string
  task_type: string
  reason: string
  priority?: 'normal' | 'urgent'
  batch_session_id?: string
}

/** POST /manual-review-requests/ — 发布者发起人工审核申请（见文档 §3） */
export function createManualReviewRequest(body: CreateManualReviewBody, publisherUsername?: string) {
  if (workflowMock.workflowMockEnabled()) {
    return Promise.resolve({
      data: workflowMock.mockCreate({
        detection_task_id: body.detection_task_id,
        task_type: body.task_type,
        reason: body.reason,
        priority: body.priority,
        batch_session_id: body.batch_session_id,
        publisher_username: publisherUsername,
      }),
    })
  }
  return http.post('/manual-review-requests/', {
    detection_task_id: body.detection_task_id.trim(),
    task_type: body.task_type,
    reason: body.reason.trim(),
    priority: body.priority ?? 'normal',
    batch_session_id: body.batch_session_id?.trim() || undefined,
  })
}

/** GET /get_publisher_review_tasks/ 或与后端统一的列表契约 */
export function listPublisherManualReviewApplications(params: {
  page?: number
  page_size?: number
  status?: string
  startTime?: string
  endTime?: string
}) {
  if (workflowMock.workflowMockEnabled()) {
    return Promise.resolve({ data: workflowMock.mockListPublisher(params) })
  }
  return publisherApi.getPublisherReviewTasks(params)
}

/** GET /manual-review-requests/by-detection-task/ */
export function getManualReviewApplicationByDetectionTask(detection_task_id: string) {
  if (workflowMock.workflowMockEnabled()) {
    return Promise.resolve({ data: workflowMock.mockGetByDetectionTask(detection_task_id) })
  }
  return http.get('/manual-review-requests/by-detection-task/', {
    params: { detection_task_id },
  })
}

/** GET /manual-review-requests/{id}/publisher-summary/ */
export function getPublisherManualReviewSummary(review_request_id: number) {
  if (workflowMock.workflowMockEnabled()) {
    return Promise.resolve({ data: workflowMock.mockPublisherResultSummary(review_request_id) })
  }
  return http.get(`/manual-review-requests/${review_request_id}/publisher-summary/`)
}
