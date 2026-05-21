<template>
  <v-container>
    <v-row class="mb-4">
      <v-col cols="12">
        <v-card variant="tonal">
          <v-card-title class="text-h5">欢迎使用学术内容诚信检测平台</v-card-title>
          <v-card-text>
            平台支持图像、论文 PDF（全篇 AIGC 与参考文献规范等）、Review 文本（在线或 TXT）及人工审核协作。
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <template v-if="effectiveRole === 'reviewer'">
      <v-row>
        <v-col cols="12" md="6">
          <v-card class="h-100">
            <v-card-title class="text-h6">专家 · 人工审核任务池</v-card-title>
            <v-card-text class="text-body-2">
              本卡片进入的是<strong>人工审核</strong>任务池（路由 <code>/review</code>），与发布者侧的<strong>Review 文本自动检测</strong>（统一入口 <code>/upload</code>）不是同一功能。任务类型可含图像、论文、Review 等材料单元。
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
      <v-col cols="12" md="7">
        <v-card class="h-100">
          <v-card-title class="text-h6">学术检测</v-card-title>
          <v-card-text class="text-body-2">
            <code>/upload</code> 单页包含：<strong>批量提交</strong>（图像 / 论文 PDF / Review 等同批）、<strong>论文工作台</strong>（AIGC 与资源规范性）、<strong>Review 结果</strong>。历史记录中的专项报告会跳转到对应标签。
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" to="/upload" prepend-icon="mdi-flask-outline">进入学术检测</v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
      <v-col cols="12" md="5">
        <v-card class="h-100">
          <v-card-title class="text-h6">检测历史与审核协作</v-card-title>
          <v-card-text class="text-body-2">
            查看各子任务状态与结果摘要；可按批次 ID 筛选同一批送检记录。若对自动结果有疑义，请在<strong>检测历史详情</strong>中发起人工审核申请（与专家在 <code>/review</code> 执行的审核不同）。
          </v-card-text>
          <v-card-actions>
            <v-btn variant="outlined" to="/history" prepend-icon="mdi-history">检测历史</v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts" setup>
import { useEffectiveRole } from '@/composables/useEffectiveRole'

const { effectiveRole } = useEffectiveRole()
</script>
