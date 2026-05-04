import http from './request'

/** 需求 FR-PLJC-0001 / API 文档 §16.2：在线文本或 .txt 文件，二者择一提交 */
export function submitReviewDetection(params: {
  task_name: string
  text?: string
  file?: File
}) {
  const fd = new FormData()
  fd.append('task_name', params.task_name.trim())
  if (params.file) {
    fd.append('file', params.file)
  } else if (params.text != null) {
    fd.append('text', params.text)
  }
  return http.post('/review/submit/', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
