import http from './request'
import { mockAigcFeaturesEnabled } from '@/utils/mockMode'

export default {
  uploadFile(data: FormData, options?: { timeout?: number }) {
    if (mockAigcFeaturesEnabled()) {
      const id = Math.floor(Date.now() / 1000) % 900000 + 100000
      return Promise.resolve({
        data: { id, file_id: id, message: 'Mock：已模拟上传' },
        headers: {},
      } as any)
    }
    return http.post('/upload/', data, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: options?.timeout ?? 15000,
    })
  },

  getExtractedImages(data: any, options?: { timeout?: number }) {
    if (mockAigcFeaturesEnabled()) {
      const base = Number(data.file_id) || 1
      const images = [1, 2, 3].map((i) => ({
        image_id: base * 100 + i,
        image_url: `https://picsum.photos/seed/apdup${base}${i}/200/200`,
        page_number: i,
        extracted_from_pdf: true,
      }))
      return Promise.resolve({
        data: {
          images,
          total: images.length,
        },
        headers: {},
      } as any)
    }
    return http.get(
      `/upload/${data.file_id}/extract_images/?page=${data.page_number}&page_size=${data.page_size}`,
      { timeout: options?.timeout },
    )
  },

  addTag(data: any) {
    if (mockAigcFeaturesEnabled()) {
      return Promise.resolve({ data: { ok: true }, headers: {} } as any)
    }
    console.log(data)
    return http.post(`/upload/${data.fileId}/addTag/`, { tag: data.tag })
  },
}
