import http from './request'
import * as workflowMock from '@workflow-mock'

export default {
    getReviewRequests(params: any)  {
        if (workflowMock.workflowMockEnabled()) {
            return Promise.resolve({ data: workflowMock.mockAdminReviewRequestList(params) })
        }
        return http.get('/get_reviewRequest/all/',{ params })
    },
     // 获取审核请求详情
     getReviewRequestDetails(id: number) {
        if (workflowMock.workflowMockEnabled()) {
            try {
                const data = workflowMock.mockAdminReviewRequestDetail(id)
                return Promise.resolve({ data })
            } catch {
                return Promise.reject(new Error('NOT_FOUND'))
            }
        }
        return http.get(`/get_reviewRequest/${id}/`)
    },

    // 处理审核请求（choice: 1 通过 → 分配 manual_review；0 拒绝）
    handleReviewRequest(id: number, data: any) {
        if (workflowMock.workflowMockEnabled()) {
            workflowMock.mockAdminHandle(id, Number(data?.choice), String(data?.reason ?? ''))
            return Promise.resolve({ data: { ok: true } })
        }
        return http.post(`/handle_reviewRequest/${id}/`, data)
    }
}
