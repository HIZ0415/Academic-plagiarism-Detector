<template>
  <v-container class="py-4">
    <h1 class="text-h4 font-weight-bold mb-2">社区反馈</h1>
    <p class="text-body-2 text-medium-emphasis mb-4">
      汇总系统通知、人工审核进度、举报处理结果等个人消息；与顶栏通知中心数据同源，并按类型分区展示。
    </p>

    <v-tabs v-model="tab" color="primary" class="mb-4">
      <v-tab value="all">全部</v-tab>
      <v-tab value="detection">检测反馈</v-tab>
      <v-tab value="review">审核互动</v-tab>
      <v-tab value="report">举报处理</v-tab>
      <v-tab value="admin">管理员通知</v-tab>
    </v-tabs>

    <v-card variant="outlined">
      <v-list v-if="filteredItems.length" lines="three">
        <v-list-item
          v-for="item in filteredItems"
          :key="item.id"
          :class="{ 'bg-blue-lighten-5': item.status !== 'read' }"
          @click="openItem(item)"
        >
          <template #prepend>
            <v-chip size="small" :color="categoryColor(item.category)">{{ categoryLabel(item.category) }}</v-chip>
          </template>
          <v-list-item-title class="font-weight-medium">{{ item.title }}</v-list-item-title>
          <v-list-item-subtitle class="text-wrap">{{ stripMarkdown(item.content) }}</v-list-item-subtitle>
          <template #append>
            <span class="text-caption text-medium-emphasis">{{ item.time }}</span>
          </template>
        </v-list-item>
      </v-list>
      <v-card-text v-else>
        <v-alert type="info" variant="tonal">
          {{ emptyMessage }}
        </v-alert>
      </v-card-text>
    </v-card>

    <div v-if="totalPages > 1" class="d-flex justify-center mt-4">
      <v-pagination v-model="page" :length="totalPages" @update:model-value="load" />
    </div>
  </v-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import platform from '@/api/platform'
import { useSnackbarStore } from '@/stores/snackbar'

type FeedItem = {
  id: string
  source: string
  category: string
  title: string
  content: string
  status: string
  url: string
  time: string
}

const router = useRouter()
const snackbar = useSnackbarStore()
const tab = ref('all')
const items = ref<FeedItem[]>([])
const page = ref(1)
const totalPages = ref(1)
const loading = ref(false)

const filteredItems = computed(() => {
  if (tab.value === 'all') return items.value
  if (tab.value === 'detection') return items.value.filter((i) => i.category === 'detection')
  if (tab.value === 'review') return items.value.filter((i) => i.category === 'review')
  if (tab.value === 'report') return items.value.filter((i) => i.category === 'report')
  return items.value.filter((i) => i.category === 'admin')
})

const emptyMessage = computed(() => {
  if (tab.value === 'detection') {
    return '暂无检测完成通知。提交检测并任务完成后，结果会出现在此；也可在侧栏「检测历史」查看全部记录。'
  }
  if (tab.value === 'review') return '暂无人工审核相关消息。'
  if (tab.value === 'report') return '暂无举报处理消息。'
  if (tab.value === 'admin') return '暂无管理员通知。'
  return '暂无消息'
})

function categoryLabel(c: string) {
  const m: Record<string, string> = {
    detection: '检测',
    review: '审核',
    report: '举报',
    admin: '管理员',
    system: '系统',
  }
  return m[c] || c
}

function categoryColor(c: string) {
  const m: Record<string, string> = {
    detection: 'blue',
    review: 'purple',
    report: 'orange',
    admin: 'red',
  }
  return m[c] || 'grey'
}

function stripMarkdown(s: string) {
  return (s || '').replace(/[#*`]/g, '').slice(0, 200)
}

async function load() {
  loading.value = true
  try {
    const res = await platform.getCommunityFeedback({ page: page.value, page_size: 20 })
    items.value = res.data.items || []
    totalPages.value = res.data.total_pages || 1
  } catch {
    snackbar.showMessage('加载社区反馈失败', 'error')
  } finally {
    loading.value = false
  }
}

function openItem(item: FeedItem) {
  if (item.url && item.url.startsWith('/')) {
    router.push(item.url)
  }
}

watch(tab, () => {})

onMounted(load)
</script>
