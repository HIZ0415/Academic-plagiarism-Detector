<template>
  <v-row>
    <v-col cols="6" class="mb-2">
      <v-select v-model="selectedTag" :items="mappedTag" label="为本批图片添加标签" clearable variant="outlined" hide-details />
    </v-col>
    <v-col cols="6" class="mb-2">
      <v-text-field v-model="task_name" label="为该检测任务添加名称" @update:modelValue="handleName"
        variant="outlined" :rules="[v => !v || v.length <= 10 || '任务名称不能超过10个字']" counter="10"></v-text-field>
    </v-col>
  </v-row>


  <v-row>
    <v-col cols="12">
      <div class="d-flex align-center mb-4">
        <span class="text-h6">已提取图片</span>
        <v-spacer></v-spacer>
        <v-btn color="primary" prepend-icon="mdi-check-all" @click="selectAllImages">
          全选
        </v-btn>
      </div>
    </v-col>
  </v-row>

  <v-row class="h-100">
    <!-- 左侧缩略图列表 -->
    <v-col cols="4" class="thumbnail-list pa-0">
      <v-card class="h-100">
        <v-card-text class="pa-0 h-100">
          <v-list lines="two" class="thumbnail-scroll h-100">
            <v-list-item v-for="(image, index) in displayImages" :key="image.image_id"
              :class="{ 'selected-item': image.selected }" @click="selectImage(image)">
              <template v-slot:prepend>
                <v-avatar size="60" class="me-2">
                  <v-img :src="image.image_url" cover class="bg-grey-lighten-2"></v-img>
                </v-avatar>
              </template>
              <v-list-item-title>
                {{ `图片${index + 1}` }}
              </v-list-item-title>
              <v-list-item-subtitle>
                {{ image.extracted_from_pdf ? 'PDF提取' : '上传图片' }}
              </v-list-item-subtitle>
              <template v-slot:append>
                <v-checkbox v-model="image.selected" hide-details density="compact" @click.stop
                  @update:model-value="emitUpdate"></v-checkbox>
              </template>
            </v-list-item>
          </v-list>
        </v-card-text>
      </v-card>
    </v-col>

    <!-- 右侧大图预览 -->
    <v-col cols="8" class="preview-section pa-0">
      <v-card class="h-100">
        <v-card-text class="pa-0 preview-wrapper h-100">
          <div v-if="selectedImage" class="preview-container h-100">
            <v-btn icon="mdi-chevron-left" variant="text" size="x-large" class="preview-nav-btn preview-nav-left"
              :disabled="!canNavigatePrev" @click="navigatePrev"></v-btn>

            <div class="image-container">
              <v-img :src="selectedImage.image_url" class="preview-image" cover></v-img>
            </div>

            <v-btn icon="mdi-chevron-right" variant="text" size="x-large" class="preview-nav-btn preview-nav-right"
              :disabled="!canNavigateNext" @click="navigateNext"></v-btn>

            <div class="preview-info pa-4">
              <div class="text-h6">
                {{ `图片${currentIndex + 1}` }}
              </div>
              <div class="text-body-2">
                {{ selectedImage.extracted_from_pdf ? 'PDF提取' : '上传图片' }}
              </div>
            </div>
          </div>
          <div v-else class="d-flex align-center justify-center h-100">
            <div class="text-h6 text-grey">请选择一张图片查看详情</div>
          </div>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useSnackbarStore } from '@/stores/snackbar';
import upload from '@/api/upload'

const snackbar = useSnackbarStore()
const task_name = ref('')

interface Image {
  image_id: number
  image_url: string
  page_number?: number
  extracted_from_pdf: boolean
  selected: boolean
}

const props = withDefaults(defineProps<{
  images?: Image[]
  fileId?: number
}>(), {
  images: () => [],
  fileId: 0
})

const emit = defineEmits<{
  (e: 'update', selectedImages: Image[]): void
  (e: 'tagChanged', tag: string): void
  (e: 'addName', task_name: string): void
}>()





// 使用响应式变量存储图片
const localImages = ref<Image[]>([])

// 使用计算属性合并props和本地图片
const displayImages = computed(() => {
  return localImages.value.length > 0 ? localImages.value : props.images
})

// 添加滚动加载相关变量
const loading = ref(false)
const page = ref(1)
const hasMore = ref(true)
const pageSize = ref(20)

// 添加滚动加载方法
const loadMoreImages = async () => {
  if (loading.value || !hasMore.value) return

  loading.value = true
  try {
    console.log(page.value)
    console.log(pageSize.value)
    const response = (await upload.getExtractedImages({ file_id: props.fileId, page_number: page.value, page_size: pageSize.value })).data
    const newImages = response.images.map((img: any) => ({
      image_id: img.image_id,
      image_url: import.meta.env.VITE_API_URL + img.image_url,
      page_number: img.page_number,
      extracted_from_pdf: img.extracted_from_pdf,
      selected: false
    }))
    localImages.value.push(...newImages)
    page.value++
    hasMore.value = localImages.value.length < response.total
  } catch (error) {
    snackbar.showMessage('图片加载失败', 'error')
  } finally {
    loading.value = false
  }
}

// 监听滚动事件
const handleScroll = (e: Event) => {
  const target = e.target as HTMLElement
  if (target.scrollHeight - target.scrollTop - target.clientHeight < 50) {
    loadMoreImages()
  }
}

// 组件挂载时添加滚动监听
onMounted(() => {
  const thumbnailList = document.querySelector('.thumbnail-scroll')
  if (thumbnailList) {
    thumbnailList.addEventListener('scroll', handleScroll)
  }
})

// 组件卸载时移除滚动监听
onUnmounted(() => {
  const thumbnailList = document.querySelector('.thumbnail-scroll')
  if (thumbnailList) {
    thumbnailList.removeEventListener('scroll', handleScroll)
  }
})

const selectedImage = ref<Image | null>(null)
const currentIndex = ref(-1)

const selectImage = (image: Image) => {
  console.log(image)
  selectedImage.value = image
  currentIndex.value = displayImages.value.findIndex(img => img.image_id === image.image_id)
}


const canNavigatePrev = computed(() => currentIndex.value > 0)
const canNavigateNext = computed(() => currentIndex.value < displayImages.value.length - 1)

const navigatePrev = () => {
  if (canNavigatePrev.value) {
    currentIndex.value--
    selectedImage.value = displayImages.value[currentIndex.value]
  }
}

const navigateNext = () => {
  if (canNavigateNext.value) {
    currentIndex.value++
    selectedImage.value = displayImages.value[currentIndex.value]
  }
}

const selectAllImages = () => {
  const allSelected = displayImages.value.every(img => img.selected)
  displayImages.value.forEach(img => {
    img.selected = !allSelected
  })
  emitUpdate()
}

const handleName = () => {
  emit('addName', task_name.value)
}

const emitUpdate = () => {
  emit('update', displayImages.value.filter(img => img.selected))
}

// 获取提取的图片
onMounted(async () => {
  if (props.fileId) {
    loadMoreImages()
  }
})

const mappedTag = [
  { title: '医学', value: 'Medicine' },
  { title: '生物', value: 'Biology' },
  { title: '化学', value: 'Chemistry' },
  { title: '图形学', value: 'Graphics' },
  { title: '其他', value: 'Other' }
]
const selectedTag = ref(null)


watch(selectedTag, (newVal) => {
  if (newVal !== null) {
    console.log('标签变为:', newVal)
    emit('tagChanged', newVal)
  } else {
    console.log('标签被清除')
  }
})

const canProceed = computed(() => {
  return displayImages.value.length > 0 && (!task_name.value || task_name.value.length <= 10)
})

</script>

<style scoped>
.thumbnail-list {
  height: calc(100vh - 300px);
  overflow: hidden;
}

.preview-section {
  height: calc(100vh - 300px);
  overflow: hidden;
}

.thumbnail-scroll {
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
}

.v-list {
  padding: 0;
}

.v-list-item {
  min-height: 80px;
  padding: 8px 16px;
}

.selected-item {
  background-color: rgb(var(--v-theme-primary), 0.1);
}

.preview-wrapper {
  position: relative;
  height: 100%;
}

.preview-container {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.image-container {
  flex: 1;
  position: relative;
  overflow: hidden;
  background-color: rgb(var(--v-theme-surface));
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-image {
  max-height: 100%;
  max-width: 100%;
  object-fit: contain;
  width: auto;
  height: auto;
}

.preview-nav-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 1;
  background: rgba(0, 0, 0, 0.3) !important;
  color: white !important;
}

.preview-nav-btn:hover {
  background: rgba(0, 0, 0, 0.5) !important;
}

.preview-nav-left {
  left: 16px;
}

.preview-nav-right {
  right: 16px;
}

.preview-info {
  background: rgba(0, 0, 0, 0.5);
  color: white;
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 16px;
}
</style>