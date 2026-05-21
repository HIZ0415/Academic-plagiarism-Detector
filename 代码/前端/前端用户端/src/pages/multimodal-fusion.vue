<template>
  <v-container class="py-8 text-center">
    <v-progress-circular indeterminate color="primary" />
    <p class="text-body-2 text-medium-emphasis mt-4">正在跳转到鉴伪报告…</p>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

onMounted(() => {
  router.replace({
    path: '/comprehensive-report',
    query: { ...route.query },
  })
})
</script>
