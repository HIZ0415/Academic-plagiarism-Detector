<template>
  <v-container>
    <v-row class="mb-4">
      <v-col>
        <h1 class="text-h4 font-weight-bold">用户举报审核</h1>
        <p class="text-body-2 text-medium-emphasis mb-0 mt-2">处理用户提交的违规举报（FR-GLWH-0009）。</p>
      </v-col>
    </v-row>

    <v-row class="mb-4">
      <v-col cols="12" sm="4">
        <v-select
          v-model="statusFilter"
          :items="statusItems"
          label="状态"
          clearable
          hide-details
          density="compact"
          variant="outlined"
          @update:model-value="load"
        />
      </v-col>
    </v-row>

    <v-card>
      <v-data-table :headers="headers" :items="reports" :loading="loading" density="comfortable">
        <template #item.status="{ item }">
          <v-chip size="small" :color="item.status === 'pending' ? 'warning' : 'success'">{{ item.status }}</v-chip>
        </template>
        <template #item.actions="{ item }">
          <v-btn
            v-if="item.status === 'pending'"
            size="small"
            color="primary"
            variant="tonal"
            class="text-none"
            @click="openHandle(item)"
          >
            处理
          </v-btn>
        </template>
      </v-data-table>
      <div class="d-flex justify-center pa-4">
        <v-pagination v-model="page" :length="totalPages" @update:model-value="load" />
      </div>
    </v-card>

    <v-dialog v-model="dialog" max-width="520">
      <v-card v-if="current">
        <v-card-title>处理举报 #{{ current.id }}</v-card-title>
        <v-card-text>
          <p class="text-body-2 mb-2"><strong>举报人：</strong>{{ current.reporter }}</p>
          <p class="text-body-2 mb-2"><strong>对象：</strong>{{ current.target_type }} #{{ current.target_id }}</p>
          <p class="text-body-2 mb-4"><strong>理由：</strong>{{ current.reason }}</p>
          <v-textarea v-model="resolution" label="处理说明" rows="3" variant="outlined" />
          <v-radio-group v-model="action" inline>
            <v-radio label="成立" value="resolved" />
            <v-radio label="驳回" value="dismissed" />
          </v-radio-group>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog = false">取消</v-btn>
          <v-btn color="primary" :loading="handling" @click="submitHandle">提交</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import platform from '@/api/platform'
import { useSnackbarStore } from '@/stores/snackbar'

const snackbar = useSnackbarStore()
const reports = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const totalPages = ref(1)
const statusFilter = ref<string | null>(null)
const dialog = ref(false)
const current = ref<any>(null)
const resolution = ref('')
const action = ref<'resolved' | 'dismissed'>('resolved')
const handling = ref(false)

const statusItems = [
  { title: '待处理', value: 'pending' },
  { title: '已处理', value: 'resolved' },
  { title: '已驳回', value: 'dismissed' },
]

const headers = [
  { title: 'ID', key: 'id' },
  { title: '举报人', key: 'reporter' },
  { title: '对象', key: 'target_type' },
  { title: '目标 ID', key: 'target_id' },
  { title: '状态', key: 'status' },
  { title: '时间', key: 'created_at' },
  { title: '操作', key: 'actions', sortable: false },
]

async function load() {
  loading.value = true
  try {
    const res = await platform.listReports({
      page: page.value,
      page_size: 10,
      status: statusFilter.value || undefined,
    })
    reports.value = res.data.reports || []
    totalPages.value = res.data.total_pages || 1
  } catch {
    snackbar.showMessage('加载举报列表失败', 'error')
  } finally {
    loading.value = false
  }
}

function openHandle(item: any) {
  current.value = item
  resolution.value = ''
  action.value = 'resolved'
  dialog.value = true
}

async function submitHandle() {
  if (!current.value) return
  handling.value = true
  try {
    await platform.handleReport(current.value.id, { action: action.value, resolution: resolution.value })
    snackbar.showMessage('已处理', 'success')
    dialog.value = false
    load()
  } catch {
    snackbar.showMessage('处理失败', 'error')
  } finally {
    handling.value = false
  }
}

onMounted(load)
</script>
