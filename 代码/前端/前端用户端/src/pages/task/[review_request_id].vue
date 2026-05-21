<template>
  <v-container class="py-8 text-center">
    <v-progress-circular indeterminate color="primary" />
    <p class="text-body-2 text-medium-emphasis mt-4">正在打开人工审核结果…</p>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

onMounted(() => {
  const id = (route.params as { review_request_id: string }).review_request_id
  router.replace({
    path: `/image-review/${id}`,
    query: { ...route.query },
  })
})
</script>
