<template>
  <v-container>
    <v-row class="mb-4">
      <v-col>
        <h1 class="text-h4 font-weight-bold">模型管理与配置</h1>
        <p class="text-body-2 text-medium-emphasis mb-0 mt-2">
          维护用户端展示的模型名称、版本与默认检测模式（FR-GLWH-0013）。
        </p>
      </v-col>
    </v-row>

    <v-card variant="outlined" class="pa-4 mb-4">
      <v-textarea
        v-model="jsonText"
        label="模型目录 JSON"
        rows="16"
        variant="outlined"
        hint="包含 text_model / image_model / review_model / default_mode"
        persistent-hint
      />
      <v-btn color="primary" class="mt-4 text-none" :loading="saving" @click="save">保存配置</v-btn>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import platform from '@/api/platform'
import { useSnackbarStore } from '@/stores/snackbar'

const snackbar = useSnackbarStore()
const jsonText = ref('')
const saving = ref(false)

async function load() {
  try {
    const res = await platform.getDetectionModels()
    jsonText.value = JSON.stringify(res.data.catalog, null, 2)
  } catch {
    snackbar.showMessage('加载失败', 'error')
  }
}

async function save() {
  saving.value = true
  try {
    const catalog = JSON.parse(jsonText.value)
    await platform.saveDetectionModels(catalog)
    snackbar.showMessage('已保存', 'success')
  } catch {
    snackbar.showMessage('JSON 无效或保存失败', 'error')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>
