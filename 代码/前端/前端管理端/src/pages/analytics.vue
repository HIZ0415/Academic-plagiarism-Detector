<template>
  <div class="d-none" aria-hidden="true" />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

onMounted(() => {
  router.replace({ path: '/' })
})
</script>
