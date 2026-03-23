<template>
  <!-- 上传页面内容 -->
  <div v-show="!showProgress">
    <v-row>
      <v-col cols="12" lg="11">
        <v-row>
          <v-col cols="12" md="4">
            <v-card class="h-100" :class="{ 'border border-primary': selectedVersion === 1 }"
              @click="selectedVersion = 1">
              <v-card-title class="text-h6">基础版</v-card-title>
              <v-card-subtitle>0元/张</v-card-subtitle>
              <v-card-text>
                <div class="text-body-2 mb-4">适用于个人图片检测</div>
                <v-list density="compact">
                  <v-list-item>
                    <template v-slot:prepend>
                      <div class="text-primary">AI模型</div>
                    </template>
                    <template v-slot:append>
                      <div class="text-primary">基础版</div>
                    </template>
                  </v-list-item>
                  <v-list-item>
                    <template v-slot:prepend>
                      <div>支持格式</div>
                    </template>
                    <template v-slot:append>
                      <div class="text-warning">JPG/PNG</div>
                    </template>
                  </v-list-item>
                  <v-list-item>
                    <template v-slot:prepend>
                      <div>免费额度</div>
                    </template>
                    <template v-slot:append>
                      <div class="text-warning">每天5张</div>
                    </template>
                  </v-list-item>
                  <v-list-item>
                    <template v-slot:prepend>
                      <div>检测精度</div>
                    </template>
                    <template v-slot:append>
                      <v-icon color="warning">mdi-star</v-icon>
                    </template>
                  </v-list-item>
                </v-list>
              </v-card-text>
            </v-card>
          </v-col>

          <v-col cols="12" md="4">
            <v-card class="h-100" :class="{ 'border border-primary': selectedVersion === 2 }"
              @click="selectedVersion = 2">
              <v-card-title class="text-h6">专业版</v-card-title>
              <v-card-subtitle>1元/张</v-card-subtitle>
              <v-card-text>
                <div class="text-body-2 mb-4">适用于批量图片检测</div>
                <v-list density="compact">
                  <v-list-item>
                    <template v-slot:prepend>
                      <div class="text-primary">AI模型</div>
                    </template>
                    <template v-slot:append>
                      <div class="text-primary">专业版</div>
                    </template>
                  </v-list-item>
                  <v-list-item>
                    <template v-slot:prepend>
                      <div>支持格式</div>
                    </template>
                    <template v-slot:append>
                      <div class="text-warning">全格式</div>
                    </template>
                  </v-list-item>
                  <v-list-item>
                    <template v-slot:prepend>
                      <div>极速检测</div>
                    </template>
                    <template v-slot:append>
                      <v-icon color="success">mdi-check</v-icon>
                    </template>
                  </v-list-item>
                  <v-list-item>
                    <template v-slot:prepend>
                      <div>检测精度</div>
                    </template>
                    <template v-slot:append>
                      <div class="d-flex">
                        <v-icon color="warning">mdi-star</v-icon>
                        <v-icon color="warning">mdi-star</v-icon>
                      </div>
                    </template>
                  </v-list-item>
                </v-list>
              </v-card-text>
            </v-card>
          </v-col>

          <v-col cols="12" md="4">
            <v-card class="h-100" :class="{ 'border border-primary': selectedVersion === 3 }"
              @click="selectedVersion = 3">
              <v-card-title class="text-h6">至尊版</v-card-title>
              <v-card-subtitle>定制价格</v-card-subtitle>
              <v-card-text>
                <div class="text-body-2 mb-4">适用于工业级图片检测</div>
                <v-list density="compact">
                  <v-list-item>
                    <template v-slot:prepend>
                      <div class="text-primary">AI模型</div>
                    </template>
                    <template v-slot:append>
                      <div class="text-primary">尊贵定制</div>
                    </template>
                  </v-list-item>
                  <v-list-item>
                    <template v-slot:prepend>
                      <div>支持格式</div>
                    </template>
                    <template v-slot:append>
                      <div class="text-warning">全格式</div>
                    </template>
                  </v-list-item>
                  <v-list-item>
                    <template v-slot:prepend>
                      <div>检测极速</div>
                    </template>
                    <template v-slot:append>
                      <v-icon color="success">mdi-check</v-icon>
                      <v-icon color="success">mdi-check</v-icon>
                    </template>
                  </v-list-item>
                  <v-list-item>
                    <template v-slot:prepend>
                      <div>检测精度</div>
                    </template>
                    <template v-slot:append>
                      <div class="d-flex">
                        <v-icon color="warning">mdi-star</v-icon>
                        <v-icon color="warning">mdi-star</v-icon>
                        <v-icon color="warning">mdi-star</v-icon>
                      </div>
                    </template>
                  </v-list-item>
                </v-list>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-row class="mt-6">
          <v-col cols="12">
            <v-card>
              <v-card-text class="text-center">
                <div v-if="!selectedFiles.length" class="upload-area pa-8" @dragover.prevent @drop.prevent="handleDrop"
                  @click="triggerFileInput">
                  <v-icon size="64" color="grey">mdi-cloud-upload</v-icon>
                  <div class="text-h6 mt-4">点击或拖拽图片/文件到此处上传</div>
                  <div class="text-caption text-grey">支持格式：JPG、PNG、PDF、ZIP等常见文件格式，单个文件不超过100MB</div>
                  <input type="file" ref="fileInput" style="display: none" @change="handleFileSelect"
                    accept=".jpg,.jpeg,.png,.pdf,.zip">
                </div>
                <div v-else class="file-preview pa-4">
                  <v-row>
                    <v-col cols="12" md="6" class="mx-auto">
                      <v-card>
                        <v-card-text class="d-flex align-center">
                          <v-icon size="48" color="primary" class="mr-4">mdi-file</v-icon>
                          <div>
                            <div class="text-h6">{{ selectedFiles[0].name }}</div>
                            <div class="text-caption text-grey">
                              {{ formatFileSize(selectedFiles[0].size) }}
                            </div>
                          </div>
                          <v-spacer></v-spacer>
                          <v-btn icon="mdi-close" variant="text" @click="selectedFiles = []"></v-btn>
                        </v-card-text>
                      </v-card>
                    </v-col>
                  </v-row>
                </div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-row class="mt-4">
          <v-col cols="12" class="d-flex justify-end">
            <v-btn color="primary" size="large" :loading="loading" @click="handleSubmit">
              {{ loading ? '处理中...' : '查看图片' }}
              <template v-slot:loader>
                <v-progress-circular indeterminate color="white" size="24"></v-progress-circular>
              </template>
              <v-icon v-if="!loading" end>mdi-arrow-right</v-icon>
            </v-btn>
          </v-col>
        </v-row>
      </v-col>

      <!-- <v-col cols="12" lg="3">
        <v-card>
          <v-card-title class="d-flex align-center">
            实时检测动态
            <v-spacer></v-spacer>
            <v-btn icon="mdi-chevron-left" variant="text" density="compact"></v-btn>
            <v-btn icon="mdi-chevron-right" variant="text" density="compact"></v-btn>
          </v-card-title>
          <v-card-text>
            <v-timeline density="compact" align="start">
              <v-timeline-item v-for="(item, index) in timelineItems" :key="index" dot-color="primary" size="small">
                <div class="d-flex align-center">
                  <v-avatar size="32" class="mr-3">
                    <v-img :src="item.avatar" cover></v-img>
                  </v-avatar>
                  <div>
                    <div class="d-flex align-center">
                      <span class="text-body-2">{{ item.name }}</span>
                      <v-chip size="x-small" :color="item.tagColor" class="ml-2" label>{{ item.tag }}</v-chip>
                    </div>
                    <div class="text-caption text-grey">
                      {{ item.count }}张图片 平均造假率: {{ item.rate }}
                    </div>
                  </div>
                </div>
              </v-timeline-item>
            </v-timeline>
          </v-card-text>
        </v-card>
      </v-col> -->
    </v-row>
  </div>

  <!-- 进度页面内容 -->
  <div v-show="showProgress" class="upload-progress">
    <!-- 返回按钮 -->
    <div class="d-flex align-center mb-6">
      <v-btn icon="mdi-arrow-left" variant="text" @click="returnToUpload" class="mr-2 return-btn">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <span class="text-h6 font-weight-medium">返回上传</span>
    </div>

    <v-card>
      <v-card-text>
        <ImageSelectionStep v-if="fileId" :fileId="fileId" @update="updateSelectedImages"
          @tagChanged="handleSelectedTag" @add-name="handleName" />
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="primary" variant="elevated" @click="handleNext" :disabled="!canProceed"
          append-icon="mdi-arrow-right">
          提交检测
        </v-btn>
      </v-card-actions>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import uploadApi from '@/api/upload'
import { useSnackbarStore } from '@/stores/snackbar'
import ImageSelectionStep from '@/components/steps/ImageSelectionStep.vue'
import publisher from '@/api/publisher'
import axios from 'axios'
import { modes } from 'vuetify/components/VColorPicker/util'

const router = useRouter()
const selectedVersion = ref<1 | 2 | 3 | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const selectedFiles = ref<File[]>([])
const fileId = ref()
const loading = ref<boolean>(false)
const snackbar = useSnackbarStore()

// 进度页面相关状态
const showProgress = ref(false)
const extractedImages = ref<Image[]>([])
const selectedImages = ref<Image[]>([])
const currentTag = ref<string>('')
const currentTaskName = ref('')

interface Image {
  image_id: number
  image_url: string
  page_number?: number
  extracted_from_pdf: boolean
  selected: boolean
}

const handleDrop = (event: DragEvent) => {
  event.preventDefault()
  const files = event.dataTransfer?.files
  if (files && files.length > 0) {
    const file = files[0]
    if (isValidFile(file)) {
      selectedFiles.value = [file]
    } else {
      snackbar.showMessage('不支持的文件格式，请上传 JPG、PNG 、PDF或 ZIP 文件', 'error')
    }
  }
}

const handleFileSelect = (event: Event) => {
  const files = (event.target as HTMLInputElement).files
  if (files && files.length > 0) {
    const file = files[0]
    if (isValidFile(file)) {
      selectedFiles.value = [file]
    } else {
      snackbar.showMessage('不支持的文件格式，请上传 JPG、PNG 、PDF或 ZIP 文件', 'error')
    }
  }
}

const handleName = async (newName: string) => {
  console.log(newName)
  currentTaskName.value = newName
}

const handleSelectedTag = async (newTag: string) => {
  console.log(newTag)
  currentTag.value = newTag
}

const isValidFile = (file: File): boolean => {
  const validTypes = ['image/jpeg', 'image/png', 'application/pdf', 'application/zip', 'application/x-zip-compressed']
  const maxSize = 10 * 1024 * 1024 // 10MB
  return validTypes.includes(file.type) && file.size <= maxSize
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const handleSubmit = async () => {
  if (!selectedVersion.value) {
    snackbar.showMessage('请选择检测版本', 'error')
    return
  }

  if (!selectedFiles.value.length) {
    snackbar.showMessage('请选择要上传的文件', 'error')
    return
  }

  loading.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedFiles.value[0])
    const { data } = await uploadApi.uploadFile(formData)
    fileId.value = data.file_id
    snackbar.showMessage('文件上传成功，正在处理中...', 'success')

    // 获取提取的图片
    // const { data: imagesData } = await uploadApi.getExtractedImages(data.file_id)
    // extractedImages.value = imagesData.images.map((img: any) => ({
    //   image_id: img.image_id,
    //   image_url: import.meta.env.VITE_API_URL + img.image_url,
    //   page_number: img.page_number,
    //   extracted_from_pdf: img.extracted_from_pdf,
    //   selected: false
    // }))

    // 显示进度页面
    showProgress.value = true
  } catch (error: any) {
    let message = '提交图片失败'
    if (axios.isAxiosError(error)) {
      const status = error?.code
      if (status === 'ERR_NETWORK') {
        message = '用户无权限'
      }
    }
    snackbar.showMessage(message, 'error')
  } finally {
    loading.value = false
  }
}

const triggerFileInput = () => {
  fileInput.value?.click()
}

// 进度页面相关方法
const canProceed = computed(() => {
  return selectedImages.value.length > 0 && (!currentTaskName.value || currentTaskName.value.length <= 10)
})

const updateSelectedImages = (images: typeof extractedImages.value) => {
  selectedImages.value = images
}

const handleTag = async (tag: string) => {
  console.log("parent: " + tag)
  try {
    await uploadApi.addTag({ fileId: fileId.value, tag: currentTag.value })
    console.log('标签已保存')
  } catch (error) {
    console.error('保存失败:', error)
    snackbar.showMessage("标签无效", "error")
  }
}

const handleNext = async () => {
  handleTag(currentTag.value)
  if (canProceed.value) {
    try {
      const task_id = (await publisher.submitDetection({ image_ids: selectedImages.value.map(img => img.image_id), task_name: currentTaskName.value, mode: selectedVersion.value })).data.task_id
      router.push(`/history`)
    } catch (error: any) {
      const message = error?.response?.data?.message || '图片上传失败'
      snackbar.showMessage(message, 'error')
    }
  }
}

// 添加返回上传页面的方法
const returnToUpload = () => {
  showProgress.value = false
  // 清空文件
  selectedFiles.value = []
  // 重置其他状态
  selectedVersion.value = null
  fileId.value = ''
  extractedImages.value = []
  selectedImages.value = []
}
</script>

<style scoped>
.upload-area {
  border: 2px dashed #ccc;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.upload-area:hover {
  border-color: var(--v-primary-base);
  background-color: rgba(var(--v-primary-base), 0.05);
}

.border {
  border-width: 2px !important;
  border-style: solid !important;
}

.border-primary {
  border-color: rgb(var(--v-theme-primary)) !important;
}

.v-timeline-item {
  margin-bottom: 16px;
}

.v-timeline-item:last-child {
  margin-bottom: 0;
}

.file-preview {
  border: 2px solid rgb(var(--v-theme-primary));
  border-radius: 8px;
  background-color: rgba(var(--v-theme-primary), 0.05);
}

.v-btn--loading {
  opacity: 1;
}

.upload-progress {
  position: relative;
  min-height: 100vh;
  max-height: 300vh;
  background-color: rgb(var(--v-theme-surface));
  overflow: hidden;
}

.v-stepper {
  box-shadow: none;
}
</style>