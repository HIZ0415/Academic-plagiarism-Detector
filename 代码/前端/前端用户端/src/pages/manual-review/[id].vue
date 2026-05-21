<template>
  <div class="task-detail task-detail-page pa-4 pb-12">
    <v-alert
      v-if="isTextualTaskKind"
      type="info"
      variant="tonal"
      density="compact"
      class="mb-4 text-body-2"
    >
      本条为 <strong>{{ taskKindTitle }}</strong> 人工审核。请根据下方材料单元逐项给出鉴定意见；材料加载完成后将显示正文摘录。
    </v-alert>
    <!-- 返回按钮 -->
    <div class="d-flex align-center mb-4 flex-wrap ga-2">
      <v-btn icon="mdi-arrow-left" variant="text" @click="router.push('/review')" class="mr-2 return-btn">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <span class="text-h6 font-weight-medium">返回人工审核任务池</span>
      <v-spacer />
      <v-btn color="primary" variant="tonal" prepend-icon="mdi-file-chart" @click="showAiReportDialog = true">
        查看 AI 检测报告摘要
      </v-btn>
    </div>

    <v-expansion-panels
      v-if="reviewRequestMeta"
      v-model="requestMetaPanels"
      class="mb-4 request-meta-panel"
      variant="accordion"
    >
      <v-expansion-panel rounded="lg" elevation="1">
        <v-expansion-panel-title class="text-body-2 py-3">
          申请单 #{{ reviewRequestMeta.id }} · {{ requestFlowLabel(reviewRequestMeta.status) }} · 门闸 {{ adminGateLabel(reviewRequestMeta.admin_gate_status) }}
          <span v-if="manualReviewStatus === 'completed'" class="text-success"> · 您已提交</span>
        </v-expansion-panel-title>
        <v-expansion-panel-text class="text-body-2">
          申请时间 {{ reviewRequestMeta.request_time }}。
          <span v-if="manualReviewStatus !== 'completed'" class="text-medium-emphasis d-block mt-2">鉴定口径见右侧「评分维度」说明；可在下方参与评论、点赞或举报。</span>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <v-progress-linear v-if="pageLoading" indeterminate color="primary" class="mb-4" />

    <v-alert v-else-if="pageError" type="error" variant="tonal" class="mb-4">
      {{ pageError }}
      <template #append>
        <v-btn variant="tonal" size="small" class="text-none" @click="reloadDetail">重试加载</v-btn>
      </template>
    </v-alert>

    <!-- 主要内容区域：允许整页纵向滚动，避免底部「造假判定」等被裁切 -->
    <div v-else class="main-content rounded-lg">
      <!-- 顶部信息区域（与概要设计「协作上下文 + AI 摘要 + 进度」一致，去掉过大左右边距） -->
      <div class="info-section pa-4 pa-md-6">
        <div class="content-wrapper d-flex justify-center">
          <div class="content-container info-strip">
            <div class="info-content d-flex flex-column flex-md-row flex-wrap align-stretch align-md-center justify-space-between pa-4 ga-6">
              <div class="d-flex align-center flex-grow-1 justify-center justify-md-start flex-wrap ga-4">
                <div class="progress-circle elevation-1">
                  <span class="text-h5 font-weight-bold primary--text">{{
                    formatNumber(overall?.confidence_score) }}</span>
                  <span class="text-caption">{{ confidenceRingLabel }}</span>
                </div>
                <v-card class="pa-2 elevation-1 ai-summary-card" flat rounded="lg">
                  <v-card-title class="pa-2 pb-1 text-subtitle-2 font-weight-bold">AI 检测结果摘要</v-card-title>
                  <v-card-text class="pa-2 pt-1">
                    <template v-if="isImageTaskKind">
                      <div v-for="(dimension, index) in detection_results" :key="index"
                        class="d-flex justify-space-between text-body-2 text-grey">
                        <span class="font-weight-medium">{{ convert(index) }}:</span>
                        <span class="text-primary">{{ dimension.probability.toFixed(2) }}</span>
                      </div>
                    </template>
                    <template v-else>
                      <div v-for="(row, index) in textualAiSummaryRows" :key="index"
                        class="d-flex justify-space-between text-body-2 text-grey">
                        <span class="font-weight-medium">{{ row.label }}:</span>
                        <span class="text-primary">{{ row.value }}</span>
                      </div>
                    </template>
                  </v-card-text>
                </v-card>
              </div>

              <div class="task-stats d-flex align-center justify-center justify-md-end flex-grow-0">
                <div class="answer-card elevation-1">
                  <div class="d-flex flex-column flex-sm-row align-sm-center ga-3 mb-3">
                    <div class="text-h6 font-weight-medium">审核进度</div>
                    <v-btn color="primary" :disabled="manualReviewStatus === 'completed'" @click="handleSubmit">
                      {{ manualReviewStatus === 'completed' ? '已提交' : '提交审核' }}
                    </v-btn>
                  </div>
                  <div class="answer-grid">
                    <template v-if="isImageTaskKind">
                      <v-btn v-for="(image, index) in images" :key="index" :color="getAnswerButtonColor(index)"
                        variant="outlined" size="small" class="answer-btn" density="compact"
                        @click="handleImageSelect(index)">
                        {{ index + 1 }}
                      </v-btn>
                    </template>
                    <template v-else>
                      <v-btn v-for="(unit, index) in textualUnits" :key="unit.id" :color="getTextUnitAnswerColor(index)"
                        variant="outlined" size="small" class="answer-btn answer-btn-wide" density="compact"
                        @click="handleTextUnitSelect(index)">
                        {{ index + 1 }}
                      </v-btn>
                    </template>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 分割线 -->
      <v-divider></v-divider>

      <!-- 图像类：逐图 + 七维 + 画布标注 -->
      <div v-if="isImageTaskKind" class="content-wrapper d-flex pa-2 justify-center">
        <div class="content-container d-flex" style="gap: 12px;">
          <div class="image-list rounded-lg elevation-1"
            style="background-color: rgb(var(--v-theme-surface)); padding: 20px;">
            <div class="text-h6 font-weight-medium text-center mb-4" style="white-space: nowrap;">{{ materialSidebarTitle }}</div>
            <div class="image-grid">
              <div v-for="(image, index) in images" :key="index" class="image-grid-item"
                :class="{ 'active': currentImageIndex === index }" @click="handleImageSelect(index)">
                <v-img :src="getImageUrl(image.url)" cover width="100%" height="100%" class="rounded-lg"></v-img>
              </div>
            </div>
          </div>

          <div class="preview-section">
            <div class="preview-box">
              <v-img v-if="currentImage" :src="getImageUrl(currentImage.url)" contain height="100%"
                class="rounded-lg"></v-img>
              <template v-for="(dimension, index) in dimensionsPerImage[currentImageIndex]" :key="index">
                <canvas v-show="currentDrawingDimension === index"
                  :ref="el => { if (el) drawingCanvases[index] = el as HTMLCanvasElement }" class="drawing-canvas"
                  :class="{ 'active': currentDrawingDimension === index }"
                  style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;"></canvas>
              </template>
              <transition name="fade">
                <v-img v-if="activeOverlay && isOverlayVisible" :src="activeOverlay"
                  class="rounded-lg overlay-image"></v-img>
              </transition>
              <div class="preview-controls">
                <v-btn icon="mdi-chevron-left" variant="flat" @click="handlePrevImage"
                  :disabled="currentImageIndex <= 0" class="control-btn" color="black" size="x-large"></v-btn>
                <v-btn icon="mdi-chevron-right" variant="flat" @click="handleNextImage"
                  :disabled="currentImageIndex >= images.length - 1" class="control-btn" color="black"
                  size="x-large"></v-btn>
              </div>
            </div>
          </div>

          <div class="dimension-section rounded-lg elevation-1">
            <div class="text-h6 font-weight-medium mb-4">评分维度（图像）</div>
            <div class="text-caption text-medium-emphasis mb-4">
              {{ dimensionHintText }}
              <span class="d-block mt-2">{{ appraisalGuidanceText }}</span>
            </div>
            <div class="dimension-list">
              <div v-for="(dimension, index) in dimensionsPerImage[currentImageIndex]" :key="index"
                class="dimension-item mb-6">
                <div class="d-flex align-center justify-space-between mb-2">
                  <span class="text-subtitle-1">{{ dimension.name }}</span>
                  <div class="d-flex">
                    <v-btn size="small" color="primary" variant="tonal" @click="openDrawingDialog(index)" class="mr-2">
                      <v-icon size="small" icon="mdi-pencil" class="mr-1"></v-icon>
                      绘制标注
                    </v-btn>
                    <v-btn size="small" :color="urn[index]?.visible ? 'error' : 'grey'" variant="tonal"
                      @click="handleDisplayFake(urn[index])" class="fake-area-btn">
                      <v-icon size="small" :icon="urn[index]?.visible ? 'mdi-eye-off' : 'mdi-eye'"
                        class="mr-1"></v-icon>
                      {{ urn[index]?.visible ? '隐藏造假区域' : '显示造假区域' }}
                    </v-btn>
                  </div>
                </div>
                <div class="degree-buttons mb-2">
                  <v-btn-group variant="outlined" class="d-flex">
                    <v-btn v-for="option in degreeOptions" :key="option.value"
                      :color="dimension.value === option.value ? getDegreeColor(option.value) : 'grey'"
                      :variant="dimension.value === option.value ? 'flat' : 'outlined'" class="flex-grow-1"
                      @click="dimension.value = option.value" size="small">
                      {{ option.value }}
                    </v-btn>
                  </v-btn-group>
                </div>
                <v-text-field v-model="dimension.reason" :label="'请输入' + dimension.name + '的理由'" variant="outlined"
                  density="compact" hide-details class="mt-2"></v-text-field>
              </div>

              <div class="fake-judge-section mt-4 pt-4">
                <div class="text-subtitle-1 mb-4">造假判定</div>
                <div class="d-flex justify-space-between">
                  <v-btn :color="imageJudgements[currentImageIndex] === true ? 'error' : 'grey-lighten-1'"
                    variant="tonal" class="flex-grow-1 mr-2" @click="handleJudgement(true)">
                    造假图片
                  </v-btn>
                  <v-btn :color="imageJudgements[currentImageIndex] === false ? 'success' : 'grey-lighten-1'"
                    variant="tonal" class="flex-grow-1" @click="handleJudgement(false)">
                    真实图片
                  </v-btn>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 论文 / Review：材料单元 + 正文预览 + 结论与分项评分 -->
      <div v-else class="content-wrapper d-flex pa-2 justify-center">
        <div class="content-container textual-workspace d-flex" style="gap: 12px;">
          <div class="text-unit-sidebar rounded-lg elevation-1 pa-3">
            <div class="text-subtitle-1 font-weight-bold mb-2">{{ materialSidebarTitle }}</div>
            <p class="text-caption text-medium-emphasis mb-3">按单元审读；与鉴定结论及分项参考一致。</p>
            <div class="text-unit-list">
              <v-list density="compact" nav>
                <v-list-item
                  v-for="(unit, index) in textualUnits"
                  :key="unit.id"
                  :active="currentTextUnitIndex === index"
                  rounded="lg"
                  @click="handleTextUnitSelect(index)"
                >
                  <v-list-item-title class="text-body-2">{{ index + 1 }}. {{ unit.label }}</v-list-item-title>
                  <v-list-item-subtitle v-if="unit.aiNote" class="text-caption text-wrap">{{ unit.aiNote }}</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </div>
          </div>

          <div class="text-preview-section rounded-lg elevation-1 pa-4">
            <div class="d-flex flex-wrap align-center justify-space-between mb-3 ga-2">
              <div class="text-h6 font-weight-medium">{{ currentTextualUnit?.label || '—' }}</div>
              <div class="d-flex ga-1">
                <v-btn icon size="small" variant="tonal" :disabled="currentTextUnitIndex <= 0" @click="handlePrevTextUnit">
                  <v-icon>mdi-chevron-up</v-icon>
                </v-btn>
                <v-btn icon size="small" variant="tonal" :disabled="currentTextUnitIndex >= textualUnits.length - 1" @click="handleNextTextUnit">
                  <v-icon>mdi-chevron-down</v-icon>
                </v-btn>
              </div>
            </div>
            <v-sheet v-if="currentTextualUnit" class="text-preview-body pa-4 rounded-lg">
              <div class="text-body-1 textual-content">{{ currentTextualUnit.content }}</div>
            </v-sheet>
            <v-alert v-else type="warning" variant="tonal" density="compact">暂无材料单元，请稍后刷新或联系管理员。</v-alert>
          </div>

          <div class="dimension-section textual-dimension-section rounded-lg elevation-1">
            <div class="text-h6 font-weight-medium mb-2">鉴定表单</div>
            <div class="text-caption text-medium-emphasis mb-4">
              {{ dimensionHintText }}
              <span class="d-block mt-2">{{ appraisalGuidanceText }}</span>
            </div>

            <div v-if="currentTextualDimensions.length" class="mb-4">
              <div class="text-subtitle-2 mb-2">鉴定结论</div>
              <v-radio-group
                :model-value="textUnitVerdicts[currentTextUnitIndex] ?? null"
                hide-details
                density="compact"
                class="mt-0"
                @update:model-value="patchTextVerdict"
              >
                <v-radio label="确认造假" value="confirmed_fake" color="error" class="mb-1" />
                <v-radio label="疑似造假" value="suspected" color="warning" class="mb-1" />
                <v-radio label="未发现异常" value="no_issue" color="success" />
              </v-radio-group>
            </div>

            <div v-if="isPaperTaskKind && currentTextualDimensions.length" class="mb-4">
              <div class="text-subtitle-2 mb-2">与系统倾向关系</div>
              <v-select
                :model-value="textUnitPaperStances[currentTextUnitIndex] ?? null"
                :items="paperStanceItems"
                item-title="title"
                item-value="value"
                label="结论类型"
                variant="outlined"
                density="compact"
                hide-details
                clearable
                @update:model-value="patchTextPaperStance"
              />
            </div>

            <div class="dimension-list">
              <div v-for="(dimension, index) in currentTextualDimensions" :key="index" class="dimension-item mb-5">
                <div class="text-subtitle-2 mb-2">{{ dimension.name }}</div>
                <div class="degree-buttons mb-2">
                  <v-btn-group variant="outlined" class="d-flex">
                    <v-btn v-for="option in degreeOptions" :key="option.value"
                      :color="dimension.value === option.value ? getDegreeColor(option.value) : 'grey'"
                      :variant="dimension.value === option.value ? 'flat' : 'outlined'" class="flex-grow-1"
                      @click="dimension.value = option.value" size="small">
                      {{ option.value }}
                    </v-btn>
                  </v-btn-group>
                </div>
                <v-text-field v-model="dimension.reason" :label="'理由 · ' + dimension.name" variant="outlined"
                  density="compact" hide-details />
              </div>
            </div>

            <v-textarea
              :model-value="textUnitMemos[currentTextUnitIndex] ?? ''"
              label="本单元补充说明（选填，可引用系统标注片段）"
              variant="outlined"
              rows="2"
              auto-grow
              max-rows="5"
              hide-details
              class="mt-2"
              @update:model-value="patchTextMemo"
            />

            <div class="fake-judge-section mt-4 pt-4">
              <div class="text-subtitle-2 mb-2">单元导航</div>
              <p class="text-caption text-medium-emphasis mb-0">请对每个材料单元完成结论、分项评分与理由后再提交整单任务。</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <v-card v-if="manual_review_id" variant="outlined" class="pa-4 mt-6 mx-2">
      <div class="d-flex align-center flex-wrap ga-2 mb-3">
        <div class="text-subtitle-1 font-weight-bold">评论与互动</div>
        <v-chip size="small" color="primary" variant="tonal">{{ feedbackLikeCount }} 赞</v-chip>
        <v-spacer />
        <v-btn size="small" variant="tonal" color="error" class="text-none" prepend-icon="mdi-flag" @click="showReportDialog = true">
          举报
        </v-btn>
      </div>
      <v-list v-if="feedbacks.length" density="compact" class="mb-3">
        <v-list-item v-for="fb in feedbacks" :key="fb.feedback_id">
          <v-list-item-title>{{ fb.username }}</v-list-item-title>
          <v-list-item-subtitle>
            <span v-if="fb.is_like">👍 </span>{{ fb.comment || '（仅点赞）' }}
          </v-list-item-subtitle>
        </v-list-item>
      </v-list>
      <v-textarea v-model="feedbackComment" label="发表评论" rows="2" variant="outlined" hide-details class="mb-2" />
      <div class="d-flex ga-2">
        <v-btn color="primary" variant="tonal" class="text-none" @click="submitComment">发表评论</v-btn>
        <v-btn color="secondary" variant="outlined" class="text-none" prepend-icon="mdi-thumb-up" @click="submitLike">点赞</v-btn>
      </div>
    </v-card>

    <v-dialog v-model="showReportDialog" max-width="480">
      <v-card>
        <v-card-title>举报本审核任务</v-card-title>
        <v-card-text>
          <v-textarea v-model="reportReason" label="举报说明" rows="3" variant="outlined" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showReportDialog = false">取消</v-btn>
          <v-btn color="error" @click="submitReport">提交</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 添加提示对话框 -->
    <v-dialog v-model="showAlert" max-width="400">
      <v-card>
        <v-card-text class="pa-4">
          <div class="text-center">{{ alertMessage }}</div>
        </v-card-text>
        <v-card-actions class="justify-center pb-4">
          <v-btn color="primary" variant="text" @click="showAlert = false">
            确定
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 绘制弹窗（仅图像类） -->
    <DrawingDialog
      v-if="isImageTaskKind"
      v-model="showDrawingDialog"
      :image-url="currentImage ? getImageUrl(currentImage.url) : ''"
      :initial-paths="currentDimensionPaths"
      @save="handleDrawingSave"
    />

    <v-dialog v-model="showAiReportDialog" max-width="560">
      <v-card>
        <v-card-title class="text-h6">AI 检测报告摘要</v-card-title>
        <v-card-text v-if="aiDetectionSummary">
          <v-list density="compact">
            <v-list-item title="判定为造假" :subtitle="aiDetectionSummary.is_fake ? '是' : '否'" />
            <v-list-item title="置信度" :subtitle="formatNumber(aiDetectionSummary.confidence_score)" />
            <v-list-item title="检测时间" :subtitle="aiDetectionSummary.detection_time || '—'" />
          </v-list>
          <p class="text-caption text-medium-emphasis mt-2">
            完整报告可由发布者在检测任务结果中查看；此处仅摘要供人工审核参考。
          </p>
        </v-card-text>
        <v-card-text v-else>暂无 AI 摘要数据</v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showAiReportDialog = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import reviewer from '@/api/reviewer'
import type { RouteParams } from 'vue-router'
import { useSnackbarStore } from '@/stores/snackbar'
import DrawingDialog from '@/components/DrawingDialog.vue'
import publisher from '@/api/publisher'
import platform from '@/api/platform'
import { resolveBackendMediaUrl } from '@/utils/backendUrl'
const router = useRouter()
const snackbar = useSnackbarStore()
const route = useRoute()

const feedbacks = ref<Array<{ feedback_id: number; username: string; is_like: boolean; comment: string }>>([])
const feedbackLikeCount = ref(0)
const feedbackComment = ref('')
const showReportDialog = ref(false)
const reportReason = ref('')

async function loadFeedbacks() {
  const id = manual_review_id.value
  if (!id) return
  try {
    const res = await platform.listFeedback(id)
    feedbacks.value = res.data.feedbacks || []
    feedbackLikeCount.value = res.data.like_count ?? 0
  } catch {
    feedbacks.value = []
  }
}

async function submitComment() {
  const text = feedbackComment.value.trim()
  if (!text) {
    snackbar.showMessage('请填写评论', 'warning')
    return
  }
  try {
    await platform.submitFeedback({ manual_review_id: manual_review_id.value, comment: text })
    feedbackComment.value = ''
    await loadFeedbacks()
    snackbar.showMessage('评论已发布', 'success')
  } catch {
    snackbar.showMessage('评论失败', 'error')
  }
}

async function submitLike() {
  try {
    await platform.submitFeedback({ manual_review_id: manual_review_id.value, is_like: true })
    await loadFeedbacks()
    snackbar.showMessage('已点赞', 'success')
  } catch {
    snackbar.showMessage('点赞失败', 'error')
  }
}

async function submitReport() {
  const reason = reportReason.value.trim()
  if (reason.length < 5) {
    snackbar.showMessage('请至少填写 5 字说明', 'warning')
    return
  }
  try {
    await platform.submitReport({
      target_type: 'manual_review',
      target_id: manual_review_id.value,
      reason,
    })
    showReportDialog.value = false
    reportReason.value = ''
    snackbar.showMessage('举报已提交', 'success')
  } catch {
    snackbar.showMessage('举报失败', 'error')
  }
}

interface Image {
  id: number,
  url: string
}

interface TextualUnit {
  id: number
  label: string
  content: string
  aiNote?: string
}

type TextualVerdict = 'confirmed_fake' | 'suspected' | 'no_issue' | null
type PaperStance = 'agree_ai' | 'major_objection' | null

const paperStanceItems = [
  { title: '同意系统倾向', value: 'agree_ai' as const },
  { title: '存在重大异议', value: 'major_objection' as const },
]

interface SubMethod {
  method: string
  probability: number
  mask_image: string
  mask_matrix: any | null
  visible: boolean
}

/** 评分维度（图像七维与论文/Review 分项共用结构） */
interface Dimension {
  name: string
  value: number | null
  reason: string
  showFakeArea: boolean
  drawingPaths: Array<{
    points: Array<{ x: number; y: number }>
    color: string
  }>
}

// 图片相关数据和方法
const currentImageIndex = ref(0)
const images = ref<Image[]>([])

/** 论文 / Review 材料单元（接口 segments / text_units 或占位） */
const textualUnits = ref<TextualUnit[]>([])
const currentTextUnitIndex = ref(0)
const dimensionsPerTextUnit = ref<Dimension[][]>([])
const textUnitVerdicts = ref<TextualVerdict[]>([])
const textUnitPaperStances = ref<PaperStance[]>([])
const textUnitMemos = ref<string[]>([])
/** 非图像类 AI 摘要表（与侧栏卡片对应） */
const textualAiSummaryList = ref<{ label: string; value: string }[]>([])
const manual_review_id = computed(() => Number((route.params as RouteParams & { id: string }).id))

const reviewRequestMeta = ref<{
  id: number
  status: string
  admin_gate_status: string
  request_time: string
} | null>(null)

const aiDetectionSummary = ref<{
  is_fake: boolean
  confidence_score: number
  detection_time?: string
} | null>(null)

const manualReviewStatus = ref<string>('undo')
const showAiReportDialog = ref(false)
/** 申请单上下文默认折叠，减少首屏占用 */
const requestMetaPanels = ref<unknown[]>([])

/** 与列表页 task_kind 枚举对齐；缺省按图像处理 */
const reviewTaskKind = ref('image')

function normTaskKind(k?: string) {
  return (k || 'image').toLowerCase()
}

const isImageTaskKind = computed(() => {
  const k = normTaskKind(reviewTaskKind.value)
  return !k.startsWith('paper') && !k.startsWith('review')
})

const pageLoading = ref(true)
const pageError = ref('')
const pageReady = computed(
  () =>
    !pageLoading.value &&
    !pageError.value &&
    (images.value.length > 0 || textualUnits.value.length > 0),
)

const isPaperTaskKind = computed(() => normTaskKind(reviewTaskKind.value).startsWith('paper'))
const isReviewTaskKind = computed(() => normTaskKind(reviewTaskKind.value).startsWith('review'))
const isTextualTaskKind = computed(() => isPaperTaskKind.value || isReviewTaskKind.value)

const taskKindTitle = computed(() => {
  const k = normTaskKind(reviewTaskKind.value)
  if (k.startsWith('paper')) return '论文全文'
  if (k.startsWith('review')) return '同行评审 Review'
  return '学术图像'
})

const materialSidebarTitle = computed(() => {
  const k = normTaskKind(reviewTaskKind.value)
  if (k.startsWith('paper')) return '论文材料单元'
  if (k.startsWith('review')) return 'Review 材料单元'
  return '图片列表（逐图）'
})

const appraisalGuidanceText = computed(() => {
  const k = normTaskKind(reviewTaskKind.value)
  if (k.startsWith('paper')) {
    return '鉴定结论（论文）：请结合 AI 对全文/段落的异常提示，在「引用风险、生成痕迹、逻辑矛盾」等维度给出评分与理由；细分字段与后端论文检测报告 schema 对齐后固化。'
  }
  if (k.startsWith('review')) {
    return '鉴定结论（Review）：请结合 AI 对评审文本的异常提示，在「立场偏颇、抄袭拼接、不当引用」等维度给出结论与理由；字段与 Review 检测 schema 对齐后固化。'
  }
  return '鉴定结论（图像）：每张图请选择「造假图片 / 真实图片」对应需求中的「确认造假或疑似倾向 / 未发现异常」表述；细分维度评分与理由用于支撑您的结论。'
})

const dimensionHintText = computed(() => {
  const k = normTaskKind(reviewTaskKind.value)
  if (k.startsWith('paper')) {
    return '论文人工审核：结合原文片段与下列分项 1–5 分及文字理由；段落高亮与事实性子结论以后端下发为准。'
  }
  if (k.startsWith('review')) {
    return 'Review 人工审核：结合评审文本与 AI 参考信息填写分项评分与理由；可疑片段引用见补充说明。'
  }
  return '请根据图片特征，对每个造假方式进行可能性评估，分值越大表示相应维度造假可能性越大，必要时可使用绘制标注功能标记具体位置。'
})

function requestFlowLabel(s: string) {
  switch (s) {
    case 'pending':
      return '待处理'
    case 'in_progress':
      return '进行中'
    case 'completed':
      return '已完成'
    default:
      return s
  }
}

function adminGateLabel(s: string) {
  switch (s) {
    case 'pending':
      return '待审批'
    case 'accepted':
      return '已通过'
    case 'refused':
      return '已拒绝'
    default:
      return s
  }
}
const imageJudgements = ref<(boolean | null)[]>([])
const dimensionsPerImage = ref<Dimension[][]>([])
const urn = ref<SubMethod[]>([])
const activeOverlay = ref()
const isOverlayVisible = ref(false)
const overall = ref()
const detection_results = ref<dimension[]>([])

interface dimension {
  method: string,
  probability: number
}

const convert = (index: number) => {
  switch (index) {
    case 0:
      return '高斯模糊'
    case 1:
      return '亮度/对比度调节'
    case 2:
      return '智能修复'
    case 3:
      return '暴力覆盖'
    case 4:
      return '同图复制'
    case 5:
      return '重叠切割'
    case 6:
      return '跨图拼接'
  }
}


const fetchDetectionResults = async () => {
  try {
    const id = await (await publisher.getDetectionID({ img_id: currentImage.value?.id })).data.
      detection_result_id
    const response = (await publisher.getSingleImageResult(id)).data
    detection_results.value = response.sub_methods
  } catch (error) {
    snackbar.showMessage('获取检测结果失败', 'error')
  }
}


const formatNumber = (result: number) => {
  return `${(result * 100).toFixed(2)}%`
}

function clearTextualWorkspace() {
  textualUnits.value = []
  dimensionsPerTextUnit.value = []
  textUnitVerdicts.value = []
  textUnitPaperStances.value = []
  textUnitMemos.value = []
  textualAiSummaryList.value = []
  currentTextUnitIndex.value = 0
}

function createPaperDimensions(): Dimension[] {
  return [
    { name: '引用与参考规范性', value: null, reason: '', showFakeArea: false, drawingPaths: [] },
    { name: 'AIGC / 生成痕迹', value: null, reason: '', showFakeArea: false, drawingPaths: [] },
    { name: '逻辑与结构一致性', value: null, reason: '', showFakeArea: false, drawingPaths: [] },
    { name: '事实与数据可信度', value: null, reason: '', showFakeArea: false, drawingPaths: [] },
  ]
}

function createReviewDimensions(): Dimension[] {
  return [
    { name: '模板化 / 套路化倾向', value: null, reason: '', showFakeArea: false, drawingPaths: [] },
    { name: '立场与利益冲突风险', value: null, reason: '', showFakeArea: false, drawingPaths: [] },
    { name: '文本来源与抄袭嫌疑', value: null, reason: '', showFakeArea: false, drawingPaths: [] },
    { name: '评审有效性与完整性', value: null, reason: '', showFakeArea: false, drawingPaths: [] },
  ]
}

function parseSegmentsFromResponse(resp: Record<string, unknown>): TextualUnit[] {
  const raw = resp.segments ?? resp.text_units
  if (!Array.isArray(raw) || raw.length === 0) return []
  return raw
    .map((seg: unknown, i: number) => {
      const s = seg as Record<string, unknown>
      const content = String(s.content ?? s.body ?? s.text ?? '').trim()
      const label = String(s.label ?? s.title ?? `材料单元 ${i + 1}`)
      if (!content && !s.label && !s.title) return null
      return {
        id: Number(s.id ?? s.unit_id ?? i + 1),
        label,
        content: content || '（该单元暂无正文，请后端补充 content/text 字段）',
        aiNote: s.ai_note != null ? String(s.ai_note) : undefined,
      } as TextualUnit
    })
    .filter((x): x is TextualUnit => x != null)
}

function mockDefaultPaperUnits(): TextualUnit[] {
  return [
    {
      id: 1,
      label: '全文占位单元',
      content:
        '未收到后端 segments/text_units。请后端按《前后端对接-用户端专家模式》返回结构化段落；在此之前可使用本占位单元完成联调前的界面走查。',
      aiNote: '占位',
    },
  ]
}

function mockDefaultReviewUnits(): TextualUnit[] {
  return [
    {
      id: 1,
      label: 'Review 占位单元',
      content:
        '未收到后端 Review 文本单元。请返回 text_units/segments 后替换本段；审核流程仍适用 FR-YHSH-0002 / 0006。',
      aiNote: '占位',
    },
  ]
}

function initTextualTaskFromResponse(response: Record<string, unknown>) {
  clearTextualWorkspace()
  images.value = []
  imageJudgements.value = []
  dimensionsPerImage.value = []
  currentImageIndex.value = 0

  let units = parseSegmentsFromResponse(response)
  const k = normTaskKind(reviewTaskKind.value)
  const isRev = k.startsWith('review')
  if (!units.length) units = isRev ? mockDefaultReviewUnits() : mockDefaultPaperUnits()
  textualUnits.value = units
  dimensionsPerTextUnit.value = units.map(() => (isRev ? createReviewDimensions() : createPaperDimensions()))
  textUnitVerdicts.value = units.map(() => null)
  textUnitPaperStances.value = units.map(() => null)
  textUnitMemos.value = units.map(() => '')

  const ai = (response.ai_detection_result ?? {}) as Record<string, unknown>
  const conf = typeof ai.confidence_score === 'number' ? ai.confidence_score : 0.65
  overall.value = { confidence_score: conf }
  aiDetectionSummary.value = (response.ai_detection_result as typeof aiDetectionSummary.value) ?? {
    is_fake: conf > 0.5,
    confidence_score: conf,
    detection_time: undefined,
  }

  if (isRev) {
    textualAiSummaryList.value = [
      { label: '模板化倾向', value: String(ai.template_score ?? '—') },
      { label: '文本异常片段', value: String(ai.anomaly_segments ?? ai.anomaly_count ?? '—') },
      { label: '立场风险提示', value: String(ai.bias_risk ?? '—') },
      { label: '综合建议（AI）', value: String(ai.suggestion ?? '—') },
    ]
  } else {
    textualAiSummaryList.value = [
      { label: '全文异常倾向', value: formatNumber(conf) },
      { label: '高敏段落数', value: String(ai.high_risk_segments ?? ai.high_risk_paragraphs ?? '—') },
      { label: 'AIGC 占比（若有）', value: String(ai.ai_ratio ?? '—') },
      { label: '事实性子结论', value: String(ai.fact_check_hint ?? '—') },
    ]
  }
}

function applySubMethodsFromDetail(response: Record<string, unknown>) {
  const subs = response.sub_methods
  if (!Array.isArray(subs) || !subs.length) return
  detection_results.value = subs.map((s: Record<string, unknown>) => ({
    method: String(s.method ?? ''),
    probability: Number(s.probability ?? 0),
  }))
  urn.value = subs.map((s: Record<string, unknown>) => ({
    method: String(s.method ?? ''),
    probability: Number(s.probability ?? 0),
    mask_image: String(s.mask_image ?? ''),
    mask_matrix: s.mask_matrix ?? null,
    visible: false,
  }))
  const overallPayload = response.overall as { confidence_score?: number } | undefined
  if (overallPayload?.confidence_score != null) {
    overall.value = { confidence_score: overallPayload.confidence_score }
  }
}

function hydrateSavedImageReviews(reviewersResults: unknown) {
  if (!Array.isArray(reviewersResults)) return
  for (const rr of reviewersResults as Array<{
    image_id: number
    scores?: (number | null)[]
    reasons?: (string | null)[]
    result?: boolean | null
  }>) {
    const idx = images.value.findIndex((img) => img.id === rr.image_id)
    if (idx < 0) continue
    if (rr.result !== undefined && rr.result !== null) {
      imageJudgements.value[idx] = rr.result
    }
    const dims = dimensionsPerImage.value[idx]
    if (!dims) continue
    const scores = rr.scores || []
    const reasons = rr.reasons || []
    for (let j = 0; j < 7; j++) {
      if (scores[j] != null) dims[j].value = scores[j]
      if (reasons[j]) dims[j].reason = String(reasons[j])
    }
  }
}

function initImageWorkspaceFromDetail(response: Record<string, unknown>) {
  const rawImgs = (response as { imgs?: Image[] }).imgs?.length
    ? (response as { imgs: Image[] }).imgs
    : ((response as { image_urls?: string[]; image_ids?: number[] }).image_urls || []).map(
        (url: string, i: number) => ({
          id: (response as { image_ids?: number[] }).image_ids?.[i] as number,
          url,
        }),
      )

  images.value = rawImgs.filter((x: Image) => x && x.id != null && x.url)
  if (!images.value.length) {
    pageError.value = '未获取到可审核的图片。请确认管理端已通过申请，且检测任务下有关联图像。'
    return false
  }

  aiDetectionSummary.value = (response.ai_detection_result as typeof aiDetectionSummary.value) ?? null
  imageJudgements.value = new Array(images.value.length).fill(null)
  dimensionsPerImage.value = images.value.map(() => [
    { name: '高斯模糊', value: null, reason: '', showFakeArea: false, drawingPaths: [] },
    { name: '亮度/对比度调节', value: null, reason: '', showFakeArea: false, drawingPaths: [] },
    { name: '智能修复', value: null, reason: '', showFakeArea: false, drawingPaths: [] },
    { name: '暴力覆盖', value: null, reason: '', showFakeArea: false, drawingPaths: [] },
    { name: '同图复制', value: null, reason: '', showFakeArea: false, drawingPaths: [] },
    { name: '重叠切割', value: null, reason: '', showFakeArea: false, drawingPaths: [] },
    { name: '跨图拼接', value: null, reason: '', showFakeArea: false, drawingPaths: [] },
  ])
  applySubMethodsFromDetail(response)
  hydrateSavedImageReviews(response.reviewers_results)
  currentImageIndex.value = 0
  if (!detection_results.value.length) {
    fetchDetectionResults().catch(() => {})
  }
  if (!urn.value.length) {
    fetchMaskImage().catch(() => {})
  }
  return true
}

async function loadReviewDetail() {
  pageLoading.value = true
  pageError.value = ''
  images.value = []
  clearTextualWorkspace()

  if (!manual_review_id.value || Number.isNaN(manual_review_id.value)) {
    pageError.value = '无效的任务编号'
    pageLoading.value = false
    return
  }

  try {
    const response = (await reviewer.getReviewTaskDetail(manual_review_id.value)).data as Record<
      string,
      unknown
    >
    reviewTaskKind.value = String(response.task_kind || response.task_type || 'image')
    reviewRequestMeta.value = (response.review_request as typeof reviewRequestMeta.value) ?? null
    manualReviewStatus.value = (response.manual_review_status as string) || 'undo'

    if (isImageTaskKind.value) {
      const ok = initImageWorkspaceFromDetail(response)
      if (!ok) {
        snackbar.showMessage(pageError.value, 'error')
      }
    } else {
      initTextualTaskFromResponse(response)
      if (!textualUnits.value.length) {
        pageError.value = '未获取到论文/Review 材料单元，请稍后重试或联系管理员。'
        snackbar.showMessage(pageError.value, 'error')
      }
    }
  } catch (e: unknown) {
    console.error(e)
    pageError.value = '获取任务详情失败，请确认已用专家账号登录后重试。'
    snackbar.showMessage(pageError.value, 'error')
  } finally {
    pageLoading.value = false
    void loadFeedbacks()
  }
}

function reloadDetail() {
  loadReviewDetail()
}

onMounted(() => {
  loadReviewDetail()
  void loadFeedbacks()
})

const currentImage = computed(() => {
  if (
    Array.isArray(images.value) &&
    typeof currentImageIndex.value === 'number' &&
    currentImageIndex.value >= 0 &&
    currentImageIndex.value < images.value.length
  ) {
    return images.value[currentImageIndex.value];
  }
  return null;
})

const confidenceRingLabel = computed(() => (isImageTaskKind.value ? '为假' : '综合风险'))

const currentTextualUnit = computed(() => textualUnits.value[currentTextUnitIndex.value] ?? null)

const currentTextualDimensions = computed(() => dimensionsPerTextUnit.value[currentTextUnitIndex.value] ?? [])

const textualAiSummaryRows = computed(() => textualAiSummaryList.value)

const getImageUrl = (url: string) => resolveBackendMediaUrl(url)

function patchTextVerdict(v: string | null) {
  const next = textUnitVerdicts.value.slice()
  next[currentTextUnitIndex.value] = (v as TextualVerdict) ?? null
  textUnitVerdicts.value = next
}

function patchTextPaperStance(v: string | null) {
  const next = textUnitPaperStances.value.slice()
  next[currentTextUnitIndex.value] = (v as PaperStance) ?? null
  textUnitPaperStances.value = next
}

function patchTextMemo(v: string) {
  const next = textUnitMemos.value.slice()
  next[currentTextUnitIndex.value] = v
  textUnitMemos.value = next
}

function handleTextUnitSelect(index: number) {
  currentTextUnitIndex.value = index
}

function getTextUnitAnswerColor(index: number) {
  if (index === currentTextUnitIndex.value) return 'primary'
  const v = textUnitVerdicts.value[index]
  if (!v) return 'grey'
  if (v === 'confirmed_fake') return 'error'
  if (v === 'suspected') return 'warning'
  return 'success'
}

function handlePrevTextUnit() {
  if (currentTextUnitIndex.value > 0) currentTextUnitIndex.value--
}

function handleNextTextUnit() {
  if (currentTextUnitIndex.value < textualUnits.value.length - 1) currentTextUnitIndex.value++
}

const fetchMaskImage = async () => {
  try {
    const res = (await reviewer.getMaskImage({ img_id: currentImage.value?.id })).data
    urn.value = res.sub_methods.map((item: Omit<SubMethod, 'visible'>) => ({
      ...item,
      visible: false
    }))
    overall.value = res.overall
  } catch (error) {
    snackbar.showMessage('获取mask失败', 'error')
  }
}

const handleDisplayFake = (dimension: SubMethod) => {
  if (dimension.visible) {
    dimension.visible = false
    isOverlayVisible.value = false
    activeOverlay.value = null
    return
  }

  // 关闭其他所有覆盖层
  urn.value.forEach(d => {
    if (d !== dimension) {
      d.visible = false
    }
  })

  // 显示当前覆盖层
  dimension.visible = true
  isOverlayVisible.value = true
  activeOverlay.value = resolveBackendMediaUrl(dimension.mask_image)
}

const handleImageSelect = (index: number) => {
  currentImageIndex.value = index
  currentDrawingDimension.value = -1 // 重置绘制状态
  fetchMaskImage()
  fetchDetectionResults()
}

const handlePrevImage = () => {
  if (currentImageIndex.value > 0) {
    currentImageIndex.value--
  }
}

const handleNextImage = () => {
  if (currentImageIndex.value < images.value.length - 1) {
    currentImageIndex.value++
  }
}

const drawingCanvases = ref<HTMLCanvasElement[]>([])
const imageRect = ref<DOMRect | null>(null)
const currentDrawingDimension = ref<number>(-1)

// 计算当前维度的笔迹列表
const currentDimensionPaths = computed(() => {
  if (currentDrawingDimension.value === -1) return []
  const currentImage = dimensionsPerImage.value[currentImageIndex.value]
  if (!currentImage) return []
  const currentDim = currentImage[currentDrawingDimension.value]
  return currentDim?.drawingPaths || []
})

// 打开绘制对话框
const openDrawingDialog = (index: number) => {
  currentDrawingDimension.value = index
  showDrawingDialog.value = true
}

// 处理绘制保存
const handleDrawingSave = (paths: Array<{ points: Array<{ x: number; y: number }>; color: string }>) => {
  if (currentDrawingDimension.value === -1) return

  const currentImage = dimensionsPerImage.value[currentImageIndex.value]
  if (!currentImage) return

  // 只更新当前维度的绘制路径
  currentImage[currentDrawingDimension.value].drawingPaths = [...paths]
}

// 监听图片加载完成
watch(() => currentImage.value?.url, () => {
  const imgElement = document.querySelector('.preview-box .v-img img') as HTMLImageElement
  if (imgElement) {
    if (imgElement.complete) {
      imageRect.value = imgElement.getBoundingClientRect()
    } else {
      imgElement.onload = () => {
        imageRect.value = imgElement.getBoundingClientRect()
      }
    }
  }
})

// 监听窗口大小变化
onMounted(() => {
  window.addEventListener('resize', () => {
    const imgElement = document.querySelector('.preview-box .v-img img') as HTMLImageElement
    if (imgElement) {
      imageRect.value = imgElement.getBoundingClientRect()
    }
  })
})

onUnmounted(() => {
  window.removeEventListener('resize', () => { })
})

const degreeOptions = [
  { value: 1, label: '轻微' },
  { value: 2, label: '一般' },
  { value: 3, label: '中等' },
  { value: 4, label: '明显' },
  { value: 5, label: '严重' }
]

const getDegreeColor = (value: number) => {
  switch (value) {
    case 1:
      return 'success'
    case 2:
      return 'info'
    case 3:
      return 'yellow'
    case 4:
      return 'warning'
    case 5:
      return 'error'
    default:
      return 'grey'
  }
}

// 处理造假判定
const handleJudgement = (isFake: boolean) => {
  imageJudgements.value[currentImageIndex.value] = isFake
}

// 获取答题卡按钮颜色
const getAnswerButtonColor = (index: number) => {
  if (index === currentImageIndex.value) return 'primary'
  const judgement = imageJudgements.value[index]
  if (judgement === null) return 'grey'
  return judgement ? 'error' : 'success'
}

const showAlert = ref(false)
const alertMessage = ref('')

function checkTextualAnswerCompletion() {
  for (let i = 0; i < textualUnits.value.length; i++) {
    if (textUnitVerdicts.value[i] == null) {
      return {
        complete: false,
        message: `材料单元 ${i + 1} 尚未选择鉴定结论（确认造假 / 疑似造假 / 未发现异常）`,
      }
    }
    if (isPaperTaskKind.value && !textUnitPaperStances.value[i]) {
      return {
        complete: false,
        message: `材料单元 ${i + 1} 尚未选择结论类型（同意系统倾向 / 存在重大异议）`,
      }
    }
    const dims = dimensionsPerTextUnit.value[i]
    if (!dims?.length) continue
    if (dims.some(dim => dim.value === null)) {
      return { complete: false, message: `材料单元 ${i + 1} 的分项评分尚未完成` }
    }
    if (dims.some(dim => !String(dim.reason || '').trim())) {
      return { complete: false, message: `材料单元 ${i + 1} 的分项理由尚未填写完整` }
    }
  }
  return { complete: true, message: '' }
}

const checkAnswerCompletion = () => {
  if (!isImageTaskKind.value) {
    return checkTextualAnswerCompletion()
  }
  for (let i = 0; i < images.value.length; i++) {
    if (imageJudgements.value[i] === null) {
      return {
        complete: false,
        message: `第 ${i + 1} 张图片尚未进行造假判定`,
      }
    }
  }

  for (let i = 0; i < dimensionsPerImage.value.length; i++) {
    const dims = dimensionsPerImage.value[i]

    const hasUnratedDimension = dims.some(dim => dim.value === null)
    if (hasUnratedDimension) {
      return {
        complete: false,
        message: `第 ${i + 1} 张图片的评分维度尚未评分完整`,
      }
    }

    const hasEmptyReason = dims.some(dim => !dim.reason)
    if (hasEmptyReason) {
      return {
        complete: false,
        message: `第 ${i + 1} 张图片的评分维度理由尚未填写完整`,
      }
    }
  }

  return {
    complete: true,
    message: '所有图片已完成评分',
  }
}

interface ImageItem {
  img_id: number
  score: Array<number | null>  // 维度得分数组，可能是数值或者null
  reason: Array<string | null>  // 维度理由数组，可能是字符串或者null
  final: boolean | null  // 造假判定结果
  points: Array<Array<{}>>
}

function verdictToFinal(v: TextualVerdict): boolean | null {
  if (v === 'confirmed_fake' || v === 'suspected') return true
  if (v === 'no_issue') return false
  return null
}

function normalizeDimensionScores(dims: Dimension[]): number[] {
  const padded = dims.map((dim) => (dim.value == null ? 0 : Number(dim.value)))
  while (padded.length < 7) padded.push(0)
  return padded.slice(0, 7)
}

function normalizeDimensionReasons(dims: Dimension[]): string[] {
  const padded = dims.map((dim) => String(dim.reason ?? '').trim())
  while (padded.length < 7) padded.push('')
  return padded.slice(0, 7)
}

function normalizeDimensionPoints(dims: Dimension[]): unknown[][] {
  const padded = dims.map((dim) => dim.drawingPaths ?? [])
  while (padded.length < 7) padded.push([])
  return padded.slice(0, 7)
}

const constructData = () => {
  if (!isImageTaskKind.value) {
    return {
      task_kind: reviewTaskKind.value,
      result: textualUnits.value.map((u, i) => {
        const dims = dimensionsPerTextUnit.value[i] ?? []
        const fallbackImgId = images.value[0]?.id
        return {
          segment_id: u.id,
          img_id: fallbackImgId ?? u.id,
          unit_label: u.label,
          verdict: textUnitVerdicts.value[i],
          paper_stance: textUnitPaperStances.value[i],
          memo: textUnitMemos.value[i],
          score: normalizeDimensionScores(dims),
          reason: normalizeDimensionReasons(dims),
          final: verdictToFinal(textUnitVerdicts.value[i]),
          points: normalizeDimensionPoints(dims),
        }
      }),
    }
  }
  const data: { task_kind: string; result: ImageItem[] } = {
    task_kind: reviewTaskKind.value,
    result: [],
  }
  for (let i = 0; i < images.value.length; i++) {
    const dims = dimensionsPerImage.value[i] ?? []
    const item: ImageItem = {
      img_id: images.value[i].id,
      score: normalizeDimensionScores(dims),
      reason: normalizeDimensionReasons(dims),
      final: imageJudgements.value[i],
      points: normalizeDimensionPoints(dims),
    }
    data.result.push(item)
  }
  return data
}

const handleSubmit = async () => {
  if (manualReviewStatus.value === 'completed') {
    snackbar.showMessage('该任务已提交，无需重复提交', 'info')
    return
  }
  const result = checkAnswerCompletion()
  if (!result.complete) {
    snackbar.showMessage(result.message, 'error')
    return
  }
  try {
    await reviewer.submitReview(manual_review_id.value, constructData())
    snackbar.showMessage('提交成功，发布者将收到进度更新', 'success')
    manualReviewStatus.value = 'completed'
    router.push('/review')
  } catch (e: unknown) {
    const ax = e as { response?: { data?: { error?: string; message?: string; detail?: string } } }
    const d = ax.response?.data
    const msg =
      (typeof d?.error === 'string' && d.error) ||
      (typeof d?.message === 'string' && d.message) ||
      (typeof d?.detail === 'string' && d.detail) ||
      '提交失败，请检查表单是否填写完整'
    snackbar.showMessage(msg, 'error')
  }
}

const showDrawingDialog = ref(false)

// 监听图片切换
watch(() => currentImageIndex.value, () => {
  currentDrawingDimension.value = -1 // 重置绘制状态
})

// 监听维度切换
watch(() => currentDrawingDimension.value, (newVal, oldVal) => {
  // 确保所有画布都被隐藏
  drawingCanvases.value.forEach((canvas, index) => {
    if (canvas) {
      canvas.style.display = 'none'
    }
  })

  // 只显示当前维度的画布
  if (newVal !== -1) {
    const newCanvas = drawingCanvases.value[newVal]
    if (newCanvas) {
      newCanvas.style.display = 'block'
    }
  }
})
</script>

<style scoped>
/* 整页可滚动：禁止再锁 100vh + overflow:hidden，否则底部「造假判定」等区域无法完整查看 */
.task-detail-page {
  max-width: min(1400px, 100%);
  margin-left: auto;
  margin-right: auto;
}

.task-detail {
  position: relative;
  min-height: auto;
  background-color: rgb(var(--v-theme-surface));
  overflow-x: hidden;
  overflow-y: visible;
}

.main-content {
  height: auto;
  min-height: 0;
  overflow: visible;
  background-color: rgb(var(--v-theme-surface));
}

.info-strip .content-container {
  max-width: min(1100px, 100%);
}

.ai-summary-card {
  width: 100%;
  max-width: 280px;
}

.info-section {
  background-color: rgb(var(--v-theme-surface));
  padding: 16px 0;
}

.info-content {
  width: 100%;
  background-color: rgb(var(--v-theme-surface));
  min-height: 160px;
  padding: 12px 16px !important;
  justify-content: center;
  gap: 24px;
}

.progress-circle {
  width: clamp(100px, 8vw, 130px);
  height: clamp(100px, 8vw, 130px);
  border-radius: 50%;
  border: 5px solid rgb(var(--v-theme-primary));
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: rgb(var(--v-theme-surface));
}

.progress-circle .text-h5 {
  font-size: clamp(1.8rem, 2vw, 2.5rem) !important;
  line-height: 1.2;
}

.progress-circle .text-caption {
  font-size: 1rem !important;
  margin-top: 4px;
}

.task-list {
  width: clamp(360px, 30vw, 420px);
  padding: 0 12px;
}

.task-item {
  width: 100%;
  margin-bottom: 12px;
}

.task-item .v-progress-linear {
  width: clamp(260px, 25vw, 340px) !important;
  height: 10px !important;
}

.task-item .text-h6 {
  white-space: nowrap;
}

.content-wrapper {
  width: 100%;
  display: flex;
  justify-content: center;
}

.content-container {
  width: 100%;
  max-width: min(1200px, 95vw);
  display: flex;
  justify-content: center;
}

.task-stats {
  min-width: 0;
  justify-content: center;
}

.answer-card {
  padding: 16px;
  border-radius: 8px;
  background-color: rgb(var(--v-theme-surface));
  min-width: min(100%, 320px);
}

.answer-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}

.overlay-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  mix-blend-mode: multiply;
  opacity: 0.7;
  object-fit: contain;
}


.answer-btn {
  width: 36px !important;
  min-width: 0 !important;
  height: 36px !important;
  padding: 0 !important;
}

@media (max-width: 1280px) {
  .task-stats {
    min-width: clamp(280px, 25vw, 320px);
  }

  .answer-card {
    padding: 12px;
  }

  .answer-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* 三栏区域：flex 子项须 min-height:0，否则 min-height:auto 会撑破 max-height，导致右侧无法内部滚动、底部裁切 */
.image-list {
  width: clamp(100px, 8vw, 120px);
  max-height: min(78dvh, 800px);
  min-height: 0;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.image-grid {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
  margin-top: -8px;
}

.image-grid-item {
  width: 80px;
  height: 80px;
  cursor: pointer;
  border-radius: 4px;
  overflow: hidden;
  transition: border-color 0.2s ease;
  border: 2px solid transparent;
  flex-shrink: 0;
}

.image-grid-item:hover {
  border-color: rgba(var(--v-theme-primary), 0.5);
}

.image-grid-item.active {
  border-color: rgb(var(--v-theme-primary));
}

.preview-section {
  flex: 1;
  min-width: 0;
  min-height: 0;
  max-width: min(800px, 60vw);
  margin: 0 12px;
}

.preview-box {
  position: relative;
  min-height: 0;
  max-height: min(78dvh, 800px);
  height: clamp(280px, 78dvh, 800px);
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: transparent;
  overflow: hidden;
}

.preview-box .v-img {
  max-width: 800px;
  max-height: 100%;
  object-fit: contain;
}

.preview-controls {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 100%;
  display: flex;
  justify-content: space-between;
  padding: 0 16px;
}

.control-btn {
  opacity: 0.7;
  transition: opacity 0.2s ease !important;
}

.control-btn:hover {
  opacity: 1;
  transform: none;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(var(--v-theme-primary), 0.2);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(var(--v-theme-primary), 0.4);
}

/* 论文 / Review 多材料单元工作台 */
.textual-workspace {
  width: 100%;
  max-width: min(1200px, 95vw);
  align-items: stretch;
}

.text-unit-sidebar {
  width: clamp(200px, 22vw, 280px);
  flex-shrink: 0;
  min-height: 0;
  background-color: rgb(var(--v-theme-surface));
}

.text-unit-list {
  max-height: min(70dvh, 720px);
  overflow-y: auto;
}

.text-preview-section {
  flex: 1;
  min-width: 0;
  min-height: 0;
  background-color: rgb(var(--v-theme-surface));
}

.text-preview-body {
  max-height: min(78dvh, 800px);
  overflow-y: auto;
}

.textual-content {
  white-space: pre-wrap;
  line-height: 1.65;
  word-break: break-word;
}

.textual-dimension-section {
  width: min(380px, 94vw);
}

.answer-btn-wide {
  min-width: 44px;
}

@media (max-width: 960px) {
  .content-container {
    flex-wrap: wrap;
    justify-content: flex-start;
  }

  .textual-workspace {
    flex-wrap: wrap;
  }

  .text-unit-sidebar {
    width: 100%;
    max-width: 100%;
  }

  .text-preview-section {
    order: -1;
    width: 100%;
    max-width: 100%;
  }

  .textual-dimension-section {
    width: 100%;
    max-width: 100%;
    max-height: min(72dvh, 720px);
  }

  .preview-section {
    max-width: 100%;
    order: -1;
  }

  .image-list {
    height: auto;
    min-height: 0;
    max-height: min(40dvh, 360px);
    width: 100%;
    max-width: 100%;
  }

  .dimension-section {
    width: 100%;
    max-width: 100%;
    max-height: min(72dvh, 720px);
  }

  .answer-card {
    padding: 12px;
  }

  .answer-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.dimension-section {
  width: min(360px, 92vw);
  padding: 20px;
  padding-bottom: 28px;
  background-color: rgb(var(--v-theme-surface));
  max-height: min(78dvh, 800px);
  min-height: 0;
  overflow-y: auto;
  flex-shrink: 0;
  overscroll-behavior: contain;
}

.dimension-list {
  padding-right: 12px;
}

.dimension-item {
  border-bottom: 1px solid rgba(var(--v-theme-primary), 0.1);
  padding-bottom: 16px;
}

.dimension-item:last-child {
  border-bottom: none;
}

@media (max-width: 1280px) {
  .dimension-section {
    width: 260px;
  }
}

.fake-judge-section {
  border-top: 1px solid rgba(var(--v-theme-primary), 0.1);
}

.degree-buttons {
  width: 100%;
}

.degree-buttons .v-btn {
  text-transform: none;
  letter-spacing: 0;
  font-size: 0.875rem;
}

.fake-area-btn {
  font-size: 0.75rem;
  text-transform: none;
  letter-spacing: 0;
  min-width: 120px;
  /* 确保按钮有固定的最小宽度 */
}

.drawing-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
  display: none;
}

.drawing-canvas.active {
  pointer-events: auto;
  cursor: crosshair;
  display: block;
}

.color-preview {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1px solid rgba(0, 0, 0, 0.1);
}
</style>