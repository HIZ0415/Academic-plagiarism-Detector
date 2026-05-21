<template>
  <v-container class="py-8 text-center">
    <v-progress-circular indeterminate color="primary" />
    <p class="text-body-2 text-medium-emphasis mt-4">正在进入审核详情…</p>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

onMounted(() => {
  const id = (route.params as { manual_review_id: string }).manual_review_id
  router.replace({
    path: `/manual-review/${id}`,
    query: { ...route.query },
  })
})
</script>
