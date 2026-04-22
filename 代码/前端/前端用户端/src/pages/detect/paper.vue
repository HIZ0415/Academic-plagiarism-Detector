<template>
  <div class="aigc-detection-container">
    <!-- A. 上传与格式说明区 -->
    <div class="upload-section">
      <h3>上传论文文件</h3>
      <input
        type="file"
        accept=".pdf,.docx,.txt"
        @change="handleFileChange"
        :disabled="isSubmitting"
      />
      <p>支持格式：PDF / DOCX / TXT</p>
      <p>建议大小：小于 50MB</p>
      <p v-if="orgQuota">当前可用额度：{{ orgQuota }} 次</p>
      <button @click="uploadFile" :disabled="!selectedFile || isSubmitting">
        {{ isSubmitting ? '上传中...' : '上传' }}
      </button>
    </div>

    <!-- B. 任务元数据与操作区 -->
    <div class="task-config-section">
      <label>任务名称：</label>
      <input
        v-model="taskName"
        placeholder="请输入任务名称"
        :disabled="isSubmitting"
      />

      <label>
        <input
          type="checkbox"
          v-model="enableFactCheck"
          :disabled="isSubmitting"
        />
        启用事实性验证
      </label>

      <label>分析粒度：</label>
      <select v-model="analysisGranularity" :disabled="isSubmitting">
        <option value="paragraph">段落级</option>
        <option value="sentence">句子级</option>
      </select>

      <button @click="submitDetection" :disabled="!taskName || isSubmitting">
        {{ isSubmitting ? '提交中...' : '提交检测' }}
      </button>
    </div>

    <!-- C. 提交与状态区 -->
    <div class="submit-status-section">
      <div v-if="taskId && !result" class="progress-bar">
        <div class="progress" :style="{ width: progress + '%' }"></div>
        <span>{{ statusText }}</span>
      </div>

      <div v-if="result" class="result-link">
        <a href="#" @click.prevent="viewDetail">查看详细报告</a>
      </div>

      <div v-if="error" class="error-message">
        {{ error }}
      </div>
    </div>

    <!-- D. 预留结果摘要区 -->
    <div v-if="result" class="result-summary-section">
      <h3>检测结果摘要</h3>
      <p><strong>全文风险值：</strong>{{ result.riskScore }}%</p>
      <p><strong>AI 写作能力：</strong>{{ result.aiAbility }}</p>
      <a href="#" @click.prevent="viewDetail">跳转详情</a>
    </div>
  </div>
</template>