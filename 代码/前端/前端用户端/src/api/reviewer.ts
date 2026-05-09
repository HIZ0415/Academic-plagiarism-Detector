import http from './request'
import * as workflowMock from '@workflow-mock'
import { mockAigcFeaturesEnabled } from '@/utils/mockMode'
import publisher from '@/api/publisher'

function reviewerSideDataMock(): boolean {
  return workflowMock.workflowMockEnabled() || mockAigcFeaturesEnabled()
}

export default {
  submitReview(manual_review_id: number, data: any) {
    if (workflowMock.workflowMockEnabled()) {
      workflowMock.mockSubmitExpert(manual_review_id)
      return Promise.resolve({ data: { ok: true, manual_review_id } })
    }
    return http.post(`/post_review/${manual_review_id}/`, data)
  },
  getReviewerTasks(params: any) {
    if (workflowMock.workflowMockEnabled()) {
      return Promise.resolve({ data: workflowMock.mockReviewerTaskList(params) })
    }
    return http.get('/get_reviewer_tasks/', { params })
  },
  getReviewRequest(params: any) {
    return http.get('/get_publisher_review_tasks/', { params })
  },

  /** 审稿人查看本人 ManualReview 详情（含 imgs、AI 摘要、协作流程字段） */
  getReviewTaskDetail(manualReviewId: number | string) {
    if (workflowMock.workflowMockEnabled()) {
      try {
        const data = workflowMock.mockGetReviewDetail(Number(manualReviewId))
        return Promise.resolve({ data })
      } catch {
        return Promise.reject(new Error('NOT_FOUND'))
      }
    }
    return http.get(`/get_review_detail/${manualReviewId}/`)
  },

  getMaskImage(data: any) {
    if (reviewerSideDataMock()) {
      return publisher.getSingleImageResult(String(data.img_id ?? 9001))
    }
    return http.get(`/results_image/${data.img_id}/`)
  },

  getTaskCount() {
    if (reviewerSideDataMock()) {
      return Promise.resolve({
        data: {
          total_received_tasks: 5,
          total_completed_tasks: 3,
        },
      })
    }
    return http.get('/reviewer/tasks/')
  },

  getRecentActivities() {
    if (reviewerSideDataMock()) {
      return Promise.resolve({
        data: [
          {
            task_name: 'Mock 人工复核任务',
            completion_time: '2026-05-09 11:00:00',
            status: 'completed',
          },
        ],
      })
    }
    return http.get('/reviewer/activity_logs/')
  },

  getDetectionResult(data: any) {
    if (reviewerSideDataMock()) {
      return mockBlobReport(`image_${data.img_id}_report.pdf`)
    }
    return http.get(`tasks_image/${data.img_id}/report/`, { responseType: 'blob' })
  },
}

function mockBlobReport(name: string) {
  const blob = new Blob([`Mock 报告 ${name}`], { type: 'application/pdf' })
  return Promise.resolve({ data: blob, headers: {} } as any)
}