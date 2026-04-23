import { da } from 'vuetify/locale'
import http from './request'

const USE_MOCK_AIGC = import.meta.env.VITE_USE_MOCK_AIGC === 'true'

const ok = <T>(data: T) => Promise.resolve({ data, headers: {} } as any)

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
  //发布审核任务
  dispatchAnnual(data: any) {
    return http.post('/create_review_task_with_admin_check/', data)
  },

  //data是taskId
  //返回某个task的所有人工审核任务的完成情况，只返回百分比
  getAllAnnual(data: any) {
    return http.get(`/get_task_completion_status/${data}`)
  },

  //返回某个task的所有images和所有人工审核的结果
  getAnnualDetail(data: any) {
    return http.get(`/get_task_detail/${data}/`)
  },

  //返回特定审核员对特定任务的审核结果
  getReviewerDetail(data: any) {
    return http.get(`/get_task_reviewer_detail/${data.taskId}/${data.reviewer_id}`)
  },

  getAllReviewers() {
    if (USE_MOCK_AIGC) {
      return ok([
        { id: 101, username: 'mock_reviewer_1', avatar: '/media/avatars/default.png' },
        { id: 102, username: 'mock_reviewer_2', avatar: '/media/avatars/default.png' },
      ])
    }
    return http.get('/get_all_reviewers/')
  },

  getReviewers(data: any) {
    if (USE_MOCK_AIGC) {
      return ok({
        publisher_id: Number(data.publisher_id),
        reviewers: [
          { id: 101, username: 'mock_reviewer_1', avatar: '/media/avatars/default.png' },
          { id: 102, username: 'mock_reviewer_2', avatar: '/media/avatars/default.png' },
        ]
      })
    }
    return http.get(`publishers/${data.publisher_id}/reviewers/`)
  },

  //获取某个出版社所有检测的任务
  getAllDetectionTask(data: any) {
    if (USE_MOCK_AIGC) {
      return ok({
        tasks: [
          {
            task_id: '1',
            task_name: 'Mock Detection Task',
            upload_time: '2026-04-20 17:11:38',
            completion_time: '2026-04-20 17:15:10',
            status: 'completed',
          }
        ],
        current_page: Number(data?.page || 1),
        total_pages: 1,
        total_tasks: 1,
      })
    }
    return http.get('/user-tasks/', { params: data })
  },

  //提交AI检测任务
  submitDetection(data: any) {
    return http.post('/detection/submit/', data)
  },

  //获取某个任务的所有图片的AI检测结果
  getTaskResults(data: any) {
    return http.get(`/tasks/${data}/results/`)
  },

  getFakeImage(data: any) {
    if (USE_MOCK_AIGC) {
      return ok({ task_id: data.task_id, total_results: mockImageResults.fake.length, results: mockImageResults.fake })
    }
    return http.get(`/tasks/${data.task_id}/fake_results/?include_image=${data.include_image}`)
  },

  getNormalImage(data: any) {
    if (USE_MOCK_AIGC) {
      return ok({ task_id: data.task_id, total_results: mockImageResults.normal.length, results: mockImageResults.normal })
    }
    return http.get(`/tasks/${data.task_id}/normal_results/?include_image=${data.include_image}`,)
  },

  getSingleImageResult(data: any) {
    if (USE_MOCK_AIGC) {
      return ok({
        result_id: Number(data),
        overall: {
          is_fake: Number(data) % 2 === 0,
          confidence_score: 0.82
        },
        llm: '该图片在边缘细节和局部纹理连续性上存在异常，建议结合子方法进一步复核。',
        llm_image: '/media/llm_results/mock_llm_overlay.png',
        ela_image: '/media/ela_results/mock_ela_overlay.png',
        exif: {
          photoshop_edited: true,
          time_modified: false
        },
        timestamps: '2026-04-20 17:15:10',
        sub_methods: [
          { method: 'splicing', probability: 0.83, mask_image: '/media/masks/mock_splicing.png', mask_matrix: null },
          { method: 'blurring', probability: 0.24, mask_image: '/media/masks/mock_blurring.png', mask_matrix: null },
          { method: 'bruteforce', probability: 0.61, mask_image: '/media/masks/mock_bruteforce.png', mask_matrix: null },
          { method: 'contrast', probability: 0.41, mask_image: '/media/masks/mock_contrast.png', mask_matrix: null },
          { method: 'inpainting', probability: 0.73, mask_image: '/media/masks/mock_inpainting.png', mask_matrix: null }
        ]
      })
    }
    return http.get(`/results/${data}/`)
  },

  downloadReport(data: any) {
    return http.get(`/tasks/${data}/report/`, {
      responseType: 'blob'
    })
  },

  downloadReviewReport(data: any) {
    return http.get(`/manual-review/${data.review_request_id}/report/`, {
      responseType: 'blob'
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
    return http.get('/task-summary/')
  },

  ifHasPermission(params: {
    task_id: string
  }) {
    if (USE_MOCK_AIGC) {
      return ok({ access: true })
    }
    return http.get(`/publisher-dectectiontask-access/`, { params })
  },

  //publisher端返回人工审核表头
  getRequestDetail(data: any) {
    return http.get(`/get_request_detail/${data.review_request_id}/`)
  },

  //publisher获取单个图片的所有人工审核结果
  getImageReviewAll(data: any) {
    return http.get(`/get_img_review_all/?review_request_id=${data.review_request_id}&img_id=${data.img_id}`)
  },

  //publisher获得单张图片的单个人的详细人工审核结果
  getImageReviewDetail(data: any) {
    return http.get(`/get_image_review/?review_request_id=${data.review_request_id}&img_id=${data.img_id}&reviewer_id=${data.reviewer_id}`)
  },

  //publisher根据imgid获取detectionid
  getDetectionID(data: any) {
    return http.get(`/tasks_image/${data.img_id}/getdr/`)
  },

  deleteDetectionTask(data: any) {
    return http.delete(`/detection-task-delete/${data.task_id}/`)
  }

}