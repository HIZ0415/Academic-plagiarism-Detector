<template>
  <div class="image-detection-page">
    <v-container>
      <v-row justify="center">
        <v-col cols="12" md="8">
          <v-card variant="outlined" class="pa-6">
            <!-- 标题区域 -->
            <div class="text-h5 font-weight-bold mb-2">图像检测</div>
            <div class="text-body-2 text-medium-emphasis mb-6">
              上传图像文件进行学术诚信或内容合规性检测。支持 JPG, PNG 格式。
            </div>

            <!-- 上传区域 -->
            <v-file-input
              v-model="files"
              label="选择图片文件"
              placeholder="点击或拖拽上传"
              prepend-icon="mdi-image-outline"
              accept="image/jpeg,image/png"
              :disabled="running"
              show-size
              counter
              clearable
              variant="outlined"
              density="comfortable"
            />

            <!-- 操作按钮 -->
            <div class="d-flex gap-3 mt-4">
              <v-btn
                color="primary"
                size="large"
                prepend-icon="mdi-play-circle-outline"
                :loading="running"
                :disabled="!files.length"
                @click="startImageDetection"
              >
                开始检测
              </v-btn>
              
              <v-btn
                variant="outlined"
                size="large"
                prepend-icon="mdi-refresh"
                :disabled="running"
                @click="resetForm"
              >
                重置
              </v-btn>
            </div>

            <!-- 错误提示 -->
            <v-alert
              v-if="errorMessage"
              type="error"
              variant="tonal"
              class="mt-4"
              closable
              @click:close="errorMessage = ''"
            >
              {{ errorMessage }}
            </v-alert>
          </v-card>

          <!-- 可选：显示预览图 -->
          <v-card v-if="previewUrl" variant="flat" class="mt-6 pa-4">
            <div class="text-subtitle-1 mb-2">图片预览</div>
            <v-img
              :src="previewUrl"
              max-height="300"
              contain
              class="rounded border"
            />
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useSnackbarStore } from '@/stores/snackbar'

// 如果后续有真实接口，请取消注释并引入
// import imageApi from '@/api/image'

const router = useRouter()
const snackbar = useSnackbarStore()

const files = ref<File[]>([])
const running = ref(false)
const errorMessage = ref('')
const previewUrl = ref<string | null>(null)

// 监听文件变化，生成预览图
watch(files, (newFiles) => {
  if (newFiles && newFiles.length > 0) {
    const file = newFiles[0]
    // 释放旧的 URL 对象以防止内存泄漏
    if (previewUrl.value) {
      URL.revokeObjectURL(previewUrl.value)
    }
    previewUrl.value = URL.createObjectURL(file)
    errorMessage.value = ''
  } else {
    if (previewUrl.value) {
      URL.revokeObjectURL(previewUrl.value)
    }
    previewUrl.value = null
  }
})

// 重置表单
function resetForm() {
  files.value = []
  errorMessage.value = ''
  running.value = false
}

// 开始检测逻辑
async function startImageDetection() {
  if (!files.value || files.value.length === 0) {
    errorMessage.value = '请先选择一张图片'
    return
  }

  const file = files.value[0]
  
  // 前端二次校验格式
  if (!file.type.startsWith('image/')) {
    errorMessage.value = '文件格式不正确，仅支持图片'
    return
  }

  running.value = true
  errorMessage.value = ''

  try {
    // ---------------------------------------------------------
    // TODO: 接入真实后端接口
    // ---------------------------------------------------------
    // 假设您有一个 imageApi，调用方式可能如下：
    // const formData = new FormData()
    // formData.append('file', file)
    // const res = await imageApi.detect(formData)
    // const taskId = res.data.task_id
    
    // --- 模拟异步请求开始 ---
    await new Promise((resolve) => setTimeout(resolve, 1500))
    const mockTaskId = `img_${Date.now()}`
    // --- 模拟异步请求结束 ---

    snackbar.showMessage('图像检测任务已提交', 'success')

    // 跳转到历史记录页或详情页
    // 这里假设历史记录页可以通过 query 参数定位到最新任务
    router.push({
      path: '/history',
      query: {
        detail_id: mockTaskId,
        task_type: 'image_detection', // 确保与后端定义的 type 一致
        source: 'upload'
      }
    })

  } catch (error: any) {
    console.error('Image detection failed:', error)
    errorMessage.value = error.message || '检测提交失败，请稍后重试'
    snackbar.showMessage('检测提交失败', 'error')
  } finally {
    running.value = false
  }
}
</script>

<style scoped>
.gap-3 {
  gap: 12px;
}
.border {
  border: 1px solid rgba(0, 0, 0, 0.12);
}
</style>