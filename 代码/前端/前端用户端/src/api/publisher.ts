import http from './request'
import { mockAigcFeaturesEnabled } from '@/utils/mockMode'

const useMock = mockAigcFeaturesEnabled

const ok = <T>(data: T) => Promise.resolve({ data, headers: {} } as any)

const mockBlob = (name: string) => {
  const blob = new Blob([`Mock PDF 占位（${name}）`], { type: 'application/pdf' })
  return Promise.resolve({
    data: blob,
    headers: { 'content-disposition': `attachment; filename="${name}"` },
  } as any)
}

const mockImageResults = {
  fake: [
    { result_id: '9001', image_id: '3001', image_url: '/media/extracted_images/mock_fake_1.png' },
    { result_id: '9002', image_id: '3002', image_url: '/media/extracted_images/mock_fake_2.png' },
  ],
  normal: [
    { result_id: '9003', image_id: '3003', image_url: '/media/extracted_images/mock_real_1.png' },
    { result_id: '9004', image_id: '3004', image_url: '/media/extracted_images/mock_real_2.png' },
  ],
}

export default {
  dispatchAnnual(data: any) {
    if (useMock()) {
      return ok({ message: 'Mock：已提交人工复查申请', review_request_id: 88000 + Math.floor(Math.random() * 100) })
    }
    return http.post('/create_review_task_with_admin_check/', data)
  },

  getAllAnnual(data: any) {
    if (useMock()) {
      return ok({ completion_ratio: 0.5, completion: '50%' })
    }
    return http.get(`/get_task_completion_status/${data}`)
  },

  getAnnualDetail(data: any) {
    if (useMock()) {
      return ok({
        task_id: data,
        images: [],
        manual_reviews: [],
      })
    }
    return http.get(`/get_task_detail/${data}/`)
  },

  getReviewerDetail(data: any) {
    if (useMock()) {
      return ok({ reviewer_id: data.reviewer_id, results: [] })
    }
    return http.get(`/get_task_reviewer_detail/${data.taskId}/${data.reviewer_id}`)
  },

  getAllReviewers() {
    if (useMock()) {
      return ok([
        { id: 101, username: 'mock_reviewer_1', avatar: '/media/avatars/default.png' },
        { id: 102, username: 'mock_reviewer_2', avatar: '/media/avatars/default.png' },
      ])
    }
    return http.get('/get_all_reviewers/')
  },

  getReviewers(data: any) {
    if (useMock()) {
      return ok({
        publisher_id: Number(data.publisher_id),
        reviewers: [
          { id: 101, username: 'mock_reviewer_1', avatar: '/media/avatars/default.png' },
          { id: 102, username: 'mock_reviewer_2', avatar: '/media/avatars/default.png' },
        ],
      })
    }
    return http.get(`publishers/${data.publisher_id}/reviewers/`)
  },

  getAllDetectionTask(data: any) {
    if (useMock()) {
      return ok({
        tasks: [
          {
            task_id: '1',
            task_name: 'Mock Detection Task',
            upload_time: '2026-04-20 17:11:38',
            completion_time: '2026-04-20 17:15:10',
            status: 'completed',
            task_type: 'image_detection',
          },
        ],
        current_page: Number(data?.page || 1),
        total_pages: 1,
        total_tasks: 1,
      })
    }
    return http.get('/user-tasks/', { params: data })
  },

  submitDetection(data: any) {
    if (useMock()) {
      return ok({
        task_id: `mock-img-${Date.now()}`,
        message: 'Mock：检测任务已入队',
        ...data,
      })
    }
    return http.post('/detection/submit/', data)
  },

  getTaskResults(data: any) {
    if (useMock()) {
      const all = [...mockImageResults.fake, ...mockImageResults.normal]
      return ok({ task_id: data, results: all, total_results: all.length })
    }
    return http.get(`/tasks/${data}/results/`)
  },

  getFakeImage(data: any) {
    if (useMock()) {
      return ok({
        task_id: data.task_id,
        total_results: mockImageResults.fake.length,
        results: mockImageResults.fake,
      })
    }
    return http.get(`/tasks/${data.task_id}/fake_results/?include_image=${data.include_image}`)
  },

  getNormalImage(data: any) {
    if (useMock()) {
      return ok({
        task_id: data.task_id,
        total_results: mockImageResults.normal.length,
        results: mockImageResults.normal,
      })
    }
    return http.get(`/tasks/${data.task_id}/normal_results/?include_image=${data.include_image}`)
  },

  getSingleImageResult(data: any) {
    if (useMock()) {
      return ok({
        result_id: Number(data),
        overall: {
          is_fake: Number(data) % 2 === 0,
          confidence_score: 0.82,
        },
        llm: '该图片在边缘细节和局部纹理连续性上存在异常，建议结合子方法进一步复核。',
        llm_image: '/media/llm_results/mock_llm_overlay.png',
        ela_image: '/media/ela_results/mock_ela_overlay.png',
        exif: {
          photoshop_edited: true,
          time_modified: false,
        },
        timestamps: '2026-04-20 17:15:10',
        sub_methods: [
          { method: 'splicing', probability: 0.83, mask_image: '/media/masks/mock_splicing.png', mask_matrix: null },
          { method: 'blurring', probability: 0.24, mask_image: '/media/masks/mock_blurring.png', mask_matrix: null },
          { method: 'bruteforce', probability: 0.61, mask_image: '/media/masks/mock_bruteforce.png', mask_matrix: null },
          { method: 'contrast', probability: 0.41, mask_image: '/media/masks/mock_contrast.png', mask_matrix: null },
          { method: 'inpainting', probability: 0.73, mask_image: '/media/masks/mock_inpainting.png', mask_matrix: null },
        ],
      })
    }
    return http.get(`/results/${data}/`)
  },

  downloadReport(data: any) {
    if (useMock()) {
      return mockBlob(`task_${data}_report.pdf`)
    }
    return http.get(`/tasks/${data}/report/`, {
      responseType: 'blob',
    })
  },

  downloadReviewReport(data: any) {
    if (useMock()) {
      return mockBlob(`manual_review_${data.review_request_id}_report.pdf`)
    }
    return http.get(`/manual-review/${data.review_request_id}/report/`, {
      responseType: 'blob',
    })
  },

  getPublisherReviewTasks(params: {
    page?: number
    page_size?: number
    status?: string
    startTime?: string
    endTime?: string
  }) {
    return http.get('/get_publisher_review_tasks/', { params })
  },

  getTaskSummary() {
    if (useMock()) {
      return ok({
        total_task_count: 12,
        completed_task_count: 8,
        recent_tasks: [
          {
            task_id: 1001,
            task_name: 'sample.png',
            task_type: 'image_detection',
            upload_time: '2026-05-09 09:30:00',
            completion_time: '2026-05-09 10:00:00',
            status: 'completed',
          },
          {
            task_id: 1002,
            task_name: 'thesis.pdf',
            task_type: 'paper_aigc',
            upload_time: '2026-05-08 15:00:00',
            completion_time: '2026-05-08 16:30:00',
            status: 'completed',
          },
        ],
      })
    }
    return http.get('/task-summary/')
  },

  ifHasPermission(params: { task_id: string }) {
    if (useMock()) {
      return ok({ access: true })
    }
    return http.get(`/publisher-dectectiontask-access/`, { params })
  },

  getRequestDetail(data: any) {
    if (useMock()) {
      return ok({
        review_request_id: data.review_request_id,
        status: 'pending',
        reason: 'Mock 申请原因',
        detection_task_id: 'mock-task-1',
      })
    }
    return http.get(`/get_request_detail/${data.review_request_id}/`)
  },

  getImageReviewAll(data: any) {
    if (useMock()) {
      return ok({
        reviewers_results: [
          {
            reviewer_id: 101,
            username: 'mock_reviewer_1',
            avatar: '/media/avatars/default.png',
            status: 'completed',
            summary: 'Mock 汇总',
          },
        ],
      })
    }
    return http.get(`/get_img_review_all/?review_request_id=${data.review_request_id}&img_id=${data.img_id}`)
  },

  getImageReviewDetail(data: any) {
    if (useMock()) {
      return ok({
        reviewer_id: data.reviewer_id,
        comment: 'Mock：单审稿人详细结论占位。',
        dimensions: [],
      })
    }
    return http.get(
      `/get_image_review/?review_request_id=${data.review_request_id}&img_id=${data.img_id}&reviewer_id=${data.reviewer_id}`,
    )
  },

  getDetectionID(data: any) {
    if (useMock()) {
      const imgId = Number(data.img_id) || 3001
      return ok({ detection_result_id: 8000 + (imgId % 1000) })
    }
    return http.get(`/tasks_image/${data.img_id}/getdr/`)
  },

  deleteDetectionTask(data: any) {
    if (useMock()) {
      return ok({ message: 'Mock：已删除任务', task_id: data.task_id })
    }
    return http.delete(`/detection-task-delete/${data.task_id}/`)
  },
}
