<template>
  <v-container class="py-8 text-center">
    <v-progress-circular indeterminate color="primary" />
    <p class="text-body-2 text-medium-emphasis mt-4">正在跳转到系统日志…</p>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

onMounted(() => {
  router.replace({
    path: '/logs',
    query: { ...route.query, tab: 'detection', scope: 'paper' },
  })
})
</script>
