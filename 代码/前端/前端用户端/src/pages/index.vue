<template>
  <v-container>
    <v-row class="mb-4">
      <v-col cols="12">
        <v-card variant="tonal">
          <v-card-title class="text-h5">欢迎使用学术内容诚信检测平台</v-card-title>
          <v-card-text>
            平台已从单一图像鉴别升级为多模态检测体系，统一支持图像、论文、Review 和学术资源检测，并与人工审核流程联动。
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <template v-if="userStore.role === 'reviewer'">
      <v-row>
        <v-col cols="12" md="6">
          <v-card class="h-100">
            <v-card-title class="text-h6">专家 · 人工审核任务池</v-card-title>
            <v-card-text class="text-body-2">
              查看由发布者发起、管理端审批通过后分配给您的图像类人工审核任务；参考 AI 检测报告完成鉴定结论与理由（FR-YHSH-0001 / 0002）。
            </v-card-text>
            <v-card-actions>
              <v-btn color="primary" to="/review" prepend-icon="mdi-clipboard-check-multiple">进入人工审核</v-btn>
            </v-card-actions>
          </v-card>
        </v-col>
        <v-col cols="12" md="6">
          <v-card class="h-100">
            <v-card-title class="text-h6">通知与个人设置</v-card-title>
            <v-card-text class="text-body-2">
              任务进度与互动通知可在右上角通知中心查看；个人资料与账号设置在「个人主页」。
            </v-card-text>
            <v-card-actions>
              <v-btn variant="outlined" to="/profile" prepend-icon="mdi-account">个人主页</v-btn>
            </v-card-actions>
          </v-card>
        </v-col>
      </v-row>
    </template>

    <v-row v-else>
      <v-col cols="12" md="6">
        <v-card class="h-100">
          <v-card-title class="text-h6">统一上传与任务创建</v-card-title>
          <v-card-text class="text-body-2">
            从统一上传页面进入，按任务类型创建检测任务，覆盖图像检测、论文 AIGC、学术资源与 Review 相关任务。
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" to="/upload" prepend-icon="mdi-upload">进入学术检测</v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card class="h-100">
          <v-card-title class="text-h6">检测历史与审核协作</v-card-title>
          <v-card-text class="text-body-2">
            统一查看任务状态与结果摘要，并支持发起人工审核申请，与审稿人、管理员协作完成复核闭环。
          </v-card-text>
          <v-card-actions class="ga-2">
            <v-btn variant="outlined" to="/history" prepend-icon="mdi-history">检测历史</v-btn>
            <v-btn variant="outlined" to="/annual" prepend-icon="mdi-gavel">人工审核</v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts" setup>
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
</script>
