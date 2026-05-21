<template>
  <v-container class="py-8 text-center">
    <v-progress-circular indeterminate color="primary" />
    <p class="text-body-2 text-medium-emphasis mt-4">正在打开检测详情…</p>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

onMounted(() => {
  const id = (route.params as { id: string }).id
  router.replace({
    path: '/history',
    query: { ...route.query, detail_id: id },
  })
})
</script>
