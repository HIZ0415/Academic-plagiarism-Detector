<template>
  <div class="d-flex flex-wrap ga-2 align-center">
    <span class="text-caption text-medium-emphasis me-1 d-none d-sm-inline">检测与资源</span>
    <v-btn
      :variant="isTasks ? 'flat' : 'outlined'"
      color="primary"
      class="text-none"
      size="small"
      @click="go('/tasks')"
    >
      检测任务
    </v-btn>
    <v-btn
      :variant="isFiles ? 'flat' : 'outlined'"
      color="primary"
      class="text-none"
      size="small"
      @click="go('/files')"
    >
      资源与文件
    </v-btn>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const isTasks = computed(() => route.path === '/tasks' || route.path.startsWith('/tasks/'))
const isFiles = computed(() => route.path === '/files' || route.path.startsWith('/files/'))

function go(path: string) {
  if (route.path !== path) router.push(path)
}
</script>
