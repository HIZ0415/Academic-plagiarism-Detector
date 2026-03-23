<template>
  <v-card flat border="0">
    <v-card-text class="pa-0 mt-4">
      <DetectionReviewStep :task_id="taskId"/>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
//注意鉴权！！！
import { computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { RouteParams } from 'vue-router'
import DetectionReviewStep from '@/components/steps/DetectionReviewStep.vue'
import { useSnackbarStore } from '@/stores/snackbar';
import publisher from '@/api/publisher'
const snackbar = useSnackbarStore();

const router = useRouter()
const route = useRoute()

// 获取任务ID
const taskId = computed(() => (route.params as RouteParams & { id: string }).id)

// 组件挂载时获取任务数据
onMounted(async () => {
  const response = (await publisher.ifHasPermission({task_id: taskId.value})).data.access
  if(response !== true){
    router.push('/404')
  }
})
</script>

<style scoped>
.v-card {
  box-shadow: none;
}
</style>
