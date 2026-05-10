<template>
  <div class="review-page pb-12">
    <v-row class="mb-4" align="center">
      <v-col cols="12" md="8">
        <h1 class="text-h4 font-weight-bold mb-2">人工审核任务池</h1>
          路由 <code>/review</code>：<strong>审稿人人工复核</strong>（任务池、鉴定）。任务材料可含图像 / 论文 / Review 等，以 <code>task_kind</code> 区分；与发布者侧 Review 文本<strong>自动检测</strong>（统一入口 <code>/upload</code>）不是同一功能。
>>>>>>> Stashed changes
        </p>
        <p class="text-body-2 text-medium-emphasis mb-0">
          本页供<strong>专家（审稿人）</strong>使用：在管理端通过申请后，在此查看并处理人工复核任务。材料类型（图像 / 论文 / Review 等）由后端 <code>task_kind</code> 区分。与发布者在 <code>/upload</code> 发起的 Review 文本<strong>自动检测</strong>不是同一入口。
        </p>
=======
          路由 <code>/review</code>：<strong>审稿人人工复核</strong>（任务池、鉴定）。任务材料可含图像 / 论文 / Review 等，以 <code>task_kind</code> 区分；与发布者侧 Review 文本<strong>自动检测</strong>（统一入口 <code>/upload</code>）不是同一功能。
>>>>>>> Stashed changes
        </p>
      </v-col>
    </v-row>

    <v-alert type="info" variant="tonal" density="compact" class="mb-4 review-intro-alert text-body-2">
      <div v-if="isPreviewMode" class="d-flex flex-column flex-sm-row flex-wrap align-sm-center ga-3">
        <span><strong>预览：</strong>未调接口时列表可能为空；可打开占位详情。</span>
        <v-btn
          color="primary"
          variant="flat"
          size="small"
          class="text-none"
          prepend-icon="mdi-open-in-new"
          @click="router.push('/task/detail/0')"
        >
          审核详情（图像）
        </v-btn>
        <v-btn size="small" variant="tonal" class="text-none" @click="router.push('/task/detail/0?preview_kind=paper')">
          论文工作台
        </v-btn>
        <v-btn size="small" variant="tonal" class="text-none" @click="router.push('/task/detail/0?preview_kind=review')">
          Review 工作台
        </v-btn>
      </div>
      <div v-else>
        <strong>流程：</strong>发布者「人工审核申请」→ 管理端 <code>admin_gate_status</code> → 分配至本页 → 进入详情提交结论。
      </div>
    </v-alert>

    <v-row class="mb-4" align="center">
      <v-col cols="12" sm="8" md="5">
        <v-text-field
          v-model="searchQuery"
          label="搜索发布者用户名"
          append-inner-icon="mdi-magnify"
          clearable
          density="compact"
          hide-details
          class="search-input"
          placeholder="支持前缀匹配"
          @keyup.enter="handleSearch"
          @click:append-inner="handleSearch"
          @click:clear="handleSearch"
        />
      </v-col>
      <v-col cols="12" sm="4" md="7" class="d-flex justify-end flex-wrap ga-2">
        <v-btn color="primary" class="text-none" prepend-icon="mdi-filter-variant" @click="showFilterDialog = true">
          筛选
        </v-btn>
      </v-col>
    </v-row>