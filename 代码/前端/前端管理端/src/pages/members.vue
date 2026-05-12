<template>
  <v-container>
    <v-row class="mb-4">
      <v-col>
        <h1 class="text-h4 font-weight-bold">用户与组织</h1>
        <p class="text-body-2 text-medium-emphasis mb-0 mt-2">
          账号检索与维护、平台多组织治理或本组织档案，按身份切换下方标签即可。
        </p>
      </v-col>
    </v-row>

    <v-tabs v-model="tab" color="primary" class="mb-4" density="comfortable">
      <v-tab value="users">用户账号</v-tab>
      <v-tab v-if="adminType === 'software_admin'" value="organizations">平台组织</v-tab>
      <v-tab v-if="adminType === 'organization_admin'" value="profile">本组织档案</v-tab>
    </v-tabs>

    <v-window v-model="tab">
      <v-window-item value="users">
        <UsersPage embed />
      </v-window-item>
      <v-window-item v-if="adminType === 'software_admin'" value="organizations">
        <OrganizationsPage embed />
      </v-window-item>
      <v-window-item v-if="adminType === 'organization_admin'" value="profile">
        <OrgProfilePage embed />
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import userApi from '@/api/user'
import UsersPage from './users.vue'
import OrganizationsPage from './organizations.vue'
import OrgProfilePage from './organization_profile.vue'

const route = useRoute()
const router = useRouter()
const adminType = ref('')
const tab = ref('users')

function validTab(t: string): boolean {
  if (t === 'users') return true
  if (t === 'organizations' && adminType.value === 'software_admin') return true
  if (t === 'profile' && adminType.value === 'organization_admin') return true
  return false
}

onMounted(async () => {
  try {
    const res = await userApi.getUserInfo()
    adminType.value = res.data.admin_type ?? ''
  } catch {
    adminType.value = ''
  }
  const q = typeof route.query.tab === 'string' ? route.query.tab : ''
  if (q && validTab(q)) {
    tab.value = q
  } else {
    tab.value = 'users'
  }
})

watch(tab, (v) => {
  if (route.query.tab === v) return
  router.replace({ path: '/members', query: { ...route.query, tab: v } })
})
</script>
