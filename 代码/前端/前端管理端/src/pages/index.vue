<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title class="text-h5">
            欢迎使用学术检测管理平台
          </v-card-title>
          <v-card-text>
            <p class="mb-4">
              统筹用户、上传资源与<strong>统一检测任务</strong>（图像 / 论文 / Review），并查看操作日志与统计分析。左侧导航可进入各模块。
            </p>
            <v-list>
              <v-list-item to="/analytics">
                <v-list-item-title>
                  <v-icon start>mdi-chart-bar</v-icon>
                  统计分析（含近 30 日任务汇总与各维度趋势）
                </v-list-item-title>
              </v-list-item>
              <v-list-item to="/tasks">
                <v-list-item-title>
                  <v-icon start>mdi-clipboard-list-outline</v-icon>
                  任务列表（类型筛选、详情、自动刷新与通知推送）
                </v-list-item-title>
              </v-list-item>
              <v-list-item to="/files">
                <v-list-item-title>
                  <v-icon start>mdi-folder</v-icon>
                  资源与图像管理
                </v-list-item-title>
              </v-list-item>
              <v-list-item to="/users">
                <v-list-item-title>
                  <v-icon start>mdi-account-group</v-icon>
                  用户管理
                </v-list-item-title>
              </v-list-item>
              <v-list-item to="/logs">
                <v-list-item-title>
                  <v-icon start>mdi-history</v-icon>
                  操作日志
                </v-list-item-title>
              </v-list-item>
              <v-list-item to="/reviews">
                <v-list-item-title> 
                  <v-icon start>mdi-gavel</v-icon>
                  人工审核申请（组织管理员）
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts" setup>
//
</script>
