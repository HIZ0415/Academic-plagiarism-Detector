<template>
  <v-card flat>
    <v-card-title class="d-flex align-center">
      <div>
        <div class="text-h5 font-weight-bold">检测记录详情</div>
        <div class="text-body-2 text-medium-emphasis">统一任务详情页（任务 ID：{{ taskId }})</div>
      </div>
      <v-spacer />
      <v-chip :color="statusColor(task.status)" variant="tonal">{{ statusLabel(task.status) }}</v-chip>
    </v-card-title>

    <v-card-text>
      <v-row>
        <v-col cols="12" md="8">
          <v-card variant="outlined" class="pa-4 mb-4">
            <div class="text-subtitle-1 font-weight-bold mb-3">A. 状态时间线</div>
            <v-timeline density="compact" side="end" align="start">
              <v-timeline-item dot-color="grey">
                <div class="font-weight-medium">已创建</div>
                <div class="text-caption text-medium-emphasis">{{ task.upload_time || '暂无' }}</div>
              </v-timeline-item>
              <v-timeline-item :dot-color="task.status === 'pending' ? 'info' : 'success'">
                <div class="font-weight-medium">处理中</div>
                <div class="text-caption text-medium-emphasis">进度：{{ task.progress }}%</div>
              </v-timeline-item>
              <v-timeline-item :dot-color="task.status === 'failed' ? 'error' : 'success'">
                <div class="font-weight-medium">{{ task.status === 'failed' ? '执行失败' : '处理完成' }}</div>
                <div class="text-caption text-medium-emphasis">{{ task.completion_time || '进行中' }}</div>
              </v-timeline-item>
            </v-timeline>
            <v-alert v-if="task.error_message" type="error" variant="tonal" class="mt-2">
              {{ task.error_message }}
            </v-alert>
          </v-card>

          <v-card variant="outlined" class="pa-4">
            <div class="text-subtitle-1 font-weight-bold mb-3">B. 结果摘要</div>
            <div class="text-body-2 mb-1">任务类型：{{ typeLabel(task.task_type) }}</div>
            <div class="text-body-2 mb-1">任务状态：{{ statusLabel(task.status) }}</div>
            <div class="text-body-2 mb-1">上传时间：{{ task.upload_time || '暂无' }}</div>
            <div class="text-body-2">完成时间：{{ task.completion_time || '进行中' }}</div>
          </v-card>
        </v-col>

        <v-col cols="12" md="4">
          <v-card variant="outlined" class="pa-4">
            <div class="text-subtitle-1 font-weight-bold mb-3">C. 操作</div>
            <div class="d-flex flex-column ga-3">
              <v-btn color="primary" variant="elevated" @click="goSpecialDetail" :disabled="task.status !== 'completed'">
                进入专项详情
              </v-btn>
              <v-btn color="primary" variant="outlined" @click="goHistory">返回检测历史</v-btn>
              <v-btn color="error" variant="text" @click="deleteTask" :disabled="task.status !== 'completed'">
                删除任务
              </v-btn>
            </div>
          </v-card>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import publisher from '@/api/publisher'
import { useSnackbarStore } from '@/stores/snackbar'
import type { TaskStatus } from '@/types/core'

type UnifiedTaskType = 'paper_aigc' | 'resource_check' | 'image_detection' | 'unknown'

type TaskDetail = {
  task_id: string
  task_type: UnifiedTaskType
  status: TaskStatus
  progress: number
  upload_time: string
  completion_time: string
  error_message?: string
}

const route = useRoute()
const router = useRouter()
const snackbar = useSnackbarStore()

const taskId = computed(() => String(route.params.id || ''))

const task = ref<TaskDetail>({
  task_id: taskId.value,
  task_type: (route.query.task_type as UnifiedTaskType) || 'unknown',
  status: (route.query.status as TaskStatus) || 'pending',
  progress: Number(route.query.progress || (route.query.status === 'completed' ? 100 : 0)),
  upload_time: String(route.query.upload_time || ''),
  completion_time: String(route.query.completion_time || ''),
  error_message: '',
})

const useMockAigc = import.meta.env.VITE_USE_MOCK_AIGC === 'true'

function typeLabel(t: UnifiedTaskType) {
  if (t === 'paper_aigc') return '论文 AIGC'
  if (t === 'resource_check') return '学术资源检测'
  if (t === 'image_detection') return '图像检测'
  return '未知类型'
}

function statusLabel(s: TaskStatus) {
  if (s === 'pending') return '排队中'
  if (s === 'in_progress') return '进行中'
  if (s === 'completed') return '已完成'
  return '失败'
}

function statusColor(s: TaskStatus) {
  if (s === 'pending') return 'warning'
  if (s === 'in_progress') return 'info'
  if (s === 'completed') return 'success'
  return 'error'
}

async function hydrateFromServer() {
  try {
    const params = { page: 1, page_size: 100 }
    const res = await publisher.getAllDetectionTask(params)
    const list = Array.isArray(res.data?.tasks) ? res.data.tasks : []
    const matched = list.find((x: any) => String(x.task_id) === taskId.value)
    if (!matched) return

    task.value.task_id = String(matched.task_id)
    task.value.status = (matched.status || task.value.status) as TaskStatus
    task.value.upload_time = matched.upload_time || task.value.upload_time
    task.value.completion_time = matched.completion_time || task.value.completion_time
    if (task.value.status === 'completed') task.value.progress = 100
    else if (task.value.status === 'in_progress') task.value.progress = Math.max(task.value.progress, 60)
    else if (task.value.status === 'pending') task.value.progress = Math.max(task.value.progress, 20)

    if (task.value.task_type === 'unknown') {
      task.value.task_type = 'image_detection'
    }
  } catch {
    // 保留 query 信息作为回退数据
  }
}

async function deleteTask() {
  try {
    await publisher.deleteDetectionTask({ task_id: taskId.value })
    snackbar.showMessage('任务已删除', 'success')
    router.push('/history')
  } catch {
    snackbar.showMessage('删除检测任务失败', 'error')
  }
}

function goHistory() {
  router.push('/history')
}

function goSpecialDetail() {
  if (task.value.task_type === 'paper_aigc') {
    router.push({ path: '/detect/paper', query: { tab: 'aigc', task_id: taskId.value } })
    return
  }
  if (task.value.task_type === 'resource_check') {
    router.push({ path: '/detect/paper', query: { tab: 'resource', task_id: taskId.value } })
    return
  }
  router.push(`/step/${taskId.value}`)
}

onMounted(async () => {
  if (useMockAigc && task.value.status !== 'completed') {
    task.value.status = 'completed'
    task.value.progress = 100
  } else {
    await hydrateFromServer()
  }
})
</script>
