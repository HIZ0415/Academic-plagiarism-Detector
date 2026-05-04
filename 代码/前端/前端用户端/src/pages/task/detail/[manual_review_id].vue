<template>
  <div class="task-detail task-detail-page pa-4 pb-12">
    <v-alert v-if="isPreviewMode" type="info" variant="tonal" density="compact" class="mb-4 text-body-2">
      <strong>界面预览：</strong>下方可切换<strong>学术图像 / 论文全文 / Review</strong>三类工作台（与需求 FR-YHSH-0001 审核类型及 FR-YHSH-0002/0005/0006 一致）。表单可填，提交不会调用后端。
      <div class="d-flex flex-wrap align-center ga-2 mt-3">
        <span class="text-caption text-medium-emphasis">预览任务类型：</span>
        <v-btn-toggle
          v-model="previewDemoKind"
          mandatory
          divided
          density="compact"
          variant="outlined"
          color="primary"
          @update:model-value="reloadPreviewDemo"
        >
          <v-btn value="image" size="small" class="text-none">学术图像</v-btn>
          <v-btn value="paper" size="small" class="text-none">论文全文</v-btn>
          <v-btn value="review" size="small" class="text-none">Review</v-btn>
        </v-btn-toggle>
      </div>
    </v-alert>
    <v-alert
      v-if="!isPreviewMode && isTextualTaskKind"
      type="info"
      variant="tonal"
      density="compact"
      class="mb-4 text-body-2"
    >
      本条为 <strong>{{ taskKindTitle }}</strong> 人工审核（FR-YHSH-{{ isReviewTaskKind ? '0006' : '0005' }}）。材料单元来自接口 <code>segments</code> / <code>text_units</code>；若为空则使用占位片段直至后端下发结构化正文。
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
          <span v-if="manualReviewStatus !== 'completed'" class="text-medium-emphasis d-block mt-2">鉴定口径见右侧「评分维度」说明；评论点赞与举报（FR-YHSH-0003 / 0004）待接口接入。</span>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <!-- 主要内容区域：允许整页纵向滚动，避免底部「造假判定」等被裁切 -->
    <div class="main-content rounded-lg">
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
                <div class="text-subtitle-1 mb-4">造假判定（对应 FR-YHSH-0002）</div>
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
            <p class="text-caption text-medium-emphasis mb-3">按单元审读；与需求 FR-YHSH-0002 鉴定结论及 FR-YHSH-{{ isReviewTaskKind ? '0006' : '0005' }} 分项参考一致。</p>
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
            <v-alert v-else type="warning" variant="tonal" density="compact">暂无材料单元，请等待后端返回 <code>segments</code> / <code>text_units</code>。</v-alert>
          </div>

          <div class="dimension-section textual-dimension-section rounded-lg elevation-1">
            <div class="text-h6 font-weight-medium mb-2">鉴定表单</div>
            <div class="text-caption text-medium-emphasis mb-4">
              {{ dimensionHintText }}
              <span class="d-block mt-2">{{ appraisalGuidanceText }}</span>
            </div>

            <div v-if="currentTextualDimensions.length" class="mb-4">
              <div class="text-subtitle-2 mb-2">鉴定结论（FR-YHSH-0002）</div>
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
              <div class="text-subtitle-2 mb-2">与系统倾向关系（FR-YHSH-0005）</div>
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
            完整报告可由发布者在检测任务结果中查看；此处仅摘要供人工审核参考（FR-YHSH-0002）。
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
import { resolveBackendMediaUrl } from '@/utils/backendUrl'
import { useEffectiveRole } from '@/composables/useEffectiveRole'

const router = useRouter()
const snackbar = useSnackbarStore()
const route = useRoute()
const { isPreviewMode } = useEffectiveRole()

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
/** 界面预览下切换 demo 形态 */
const previewDemoKind = ref<'image' | 'paper' | 'review'>('image')

const manual_review_id = computed(() => Number((route.params as RouteParams & { manual_review_id: string }).manual_review_id))

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
  return k === 'image' || k === 'image_detection' || k === ''
})

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
    return '鉴定结论（FR-YHSH-0002 · 论文）：请结合 AI 对全文/段落的异常提示，在「引用风险、生成痕迹、逻辑矛盾」等维度给出评分与理由；细分字段与后端论文检测报告 schema 对齐后固化。'
  }
  if (k.startsWith('review')) {
    return '鉴定结论（FR-YHSH-0002 · Review）：请结合 AI 对评审文本的异常提示，在「立场偏颇、抄袭拼接、不当引用」等维度给出结论与理由；字段与 Review 检测 schema 对齐后固化。'
  }
  return '鉴定结论（FR-YHSH-0002 · 图像）：每张图请选择「造假图片 / 真实图片」对应需求中的「确认造假或疑似倾向 / 未发现异常」表述；细分维度评分与理由用于支撑您的结论。'
})

const dimensionHintText = computed(() => {
  const k = normTaskKind(reviewTaskKind.value)
  if (k.startsWith('paper')) {
    return '论文人工审核（FR-YHSH-0005）：结合原文片段与下列分项 1–5 分及文字理由；段落高亮与事实性子结论以后端下发为准。'
  }
  if (k.startsWith('review')) {
    return 'Review 人工审核（FR-YHSH-0006）：结合评审文本与 AI 参考信息填写分项评分与理由；可疑片段引用见补充说明。'
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
  if (isPreviewMode.value) {
    return
  }
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

function syncPreviewKindFromRoute() {
  const q = route.query.preview_kind
  const s = ((Array.isArray(q) ? q[0] : q) ?? '').toString().toLowerCase()
  if (s === 'paper' || s === 'paper_aigc') previewDemoKind.value = 'paper'
  else if (s === 'review' || s === 'review_detection') previewDemoKind.value = 'review'
  else previewDemoKind.value = 'image'
}

function loadImagePreviewMock() {
  clearTextualWorkspace()
  reviewTaskKind.value = 'image'
  currentImageIndex.value = 0
  images.value = [
    { id: 9001, url: 'https://picsum.photos/seed/aprev1/800/600' },
    { id: 9002, url: 'https://picsum.photos/seed/aprev2/800/600' },
  ]
  reviewRequestMeta.value = {
    id: 1,
    status: 'in_progress',
    admin_gate_status: 'accepted',
    request_time: '2026-01-01 12:00:00',
  }
  aiDetectionSummary.value = {
    is_fake: true,
    confidence_score: 0.62,
    detection_time: '2026-01-01 12:05:00',
  }
  manualReviewStatus.value = 'undo'
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
  overall.value = { confidence_score: 0.62 }
  detection_results.value = [
    { method: '高斯模糊', probability: 0.12 },
    { method: '亮度/对比度', probability: 0.15 },
    { method: '智能修复', probability: 0.09 },
    { method: '暴力覆盖', probability: 0.21 },
    { method: '同图复制', probability: 0.08 },
    { method: '重叠切割', probability: 0.11 },
    { method: '跨图拼接', probability: 0.07 },
  ]
  urn.value = []
}

function loadPaperPreviewMock() {
  images.value = []
  imageJudgements.value = []
  dimensionsPerImage.value = []
  currentImageIndex.value = 0
  reviewTaskKind.value = 'paper_aigc'
  reviewRequestMeta.value = {
    id: 2,
    status: 'in_progress',
    admin_gate_status: 'accepted',
    request_time: '2026-01-02 09:00:00',
  }
  aiDetectionSummary.value = {
    is_fake: true,
    confidence_score: 0.71,
    detection_time: '2026-01-02 09:10:00',
  }
  manualReviewStatus.value = 'undo'
  overall.value = { confidence_score: 0.71 }
  detection_results.value = []
  urn.value = []
  textualAiSummaryList.value = [
    { label: '全文异常倾向', value: '71%' },
    { label: '高敏段落（AI）', value: '5' },
    { label: '引用一致性提示', value: '中' },
    { label: '事实核查子结论', value: '待人工确认' },
  ]
  textualUnits.value = [
    {
      id: 1,
      label: '摘要',
      content:
        '【示例摘要】本研究提出一种面向学术图像完整性检测的多任务学习框架。实验表明，在公开数据集上 F1 提升约 3.2%。由于系统尚未接入后端 segments，本段为占位正文；联调后此处应展示脱敏摘要及 AI 段落级高亮。',
      aiNote: 'AI：生成痕迹偏高',
    },
    {
      id: 2,
      label: '方法 · 实验设置',
      content:
        '【示例方法节】我们在 PyTorch 2.1 上复现基线，批量大小 32，学习率 1e-4。数据增强包含随机裁剪与颜色抖动。若后端返回事实性子结论（如与公开实现不一致），将显示在本卡片上方参考区。',
      aiNote: 'AI：与公开描述部分不一致',
    },
    {
      id: 3,
      label: '讨论与结论',
      content:
        '【示例讨论】局限性包括样本来源单一与人工标注成本。未来工作将扩展至多模态与跨语言场景。审核人请结合 FR-YHSH-0005 选择「同意系统倾向 / 存在重大异议」并填写分项理由。',
      aiNote: 'AI：逻辑链基本自洽',
    },
  ]
  dimensionsPerTextUnit.value = textualUnits.value.map(() => createPaperDimensions())
  textUnitVerdicts.value = textualUnits.value.map(() => null)
  textUnitPaperStances.value = textualUnits.value.map(() => null)
  textUnitMemos.value = textualUnits.value.map(() => '')
}

function loadReviewPreviewMock() {
  images.value = []
  imageJudgements.value = []
  dimensionsPerImage.value = []
  currentImageIndex.value = 0
  reviewTaskKind.value = 'review_detection'
  reviewRequestMeta.value = {
    id: 3,
    status: 'in_progress',
    admin_gate_status: 'accepted',
    request_time: '2026-01-03 14:00:00',
  }
  aiDetectionSummary.value = {
    is_fake: false,
    confidence_score: 0.38,
    detection_time: '2026-01-03 14:05:00',
  }
  manualReviewStatus.value = 'undo'
  overall.value = { confidence_score: 0.38 }
  detection_results.value = []
  urn.value = []
  textualAiSummaryList.value = [
    { label: '模板化倾向', value: '0.42' },
    { label: '文本异常片段', value: '2' },
    { label: '立场风险提示', value: '低' },
    { label: '综合建议（AI）', value: '建议人工复核结论段' },
  ]
  textualUnits.value = [
    {
      id: 1,
      label: '评审意见 · 总体评价',
      content:
        '【示例 Review】论文创新点明确，实验充分。但结论部分对局限性的讨论略显模板化，与同类评审用语高度相似。此处为占位文本；正式环境由后端返回 Review 原文与系统标注可疑片段。',
      aiNote: 'AI：模板化风险',
    },
    {
      id: 2,
      label: '评审意见 · 具体意见',
      content:
        '【示例意见】建议补充与 SOTA 的对比实验，并说明数据伦理合规性。若存在利益冲突声明缺失，请在本单元结论中选择「确认造假 / 疑似造假」等并说明理由（FR-YHSH-0002 / 0006）。',
      aiNote: 'AI：未见明显抄袭拼接',
    },
  ]
  dimensionsPerTextUnit.value = textualUnits.value.map(() => createReviewDimensions())
  textUnitVerdicts.value = textualUnits.value.map(() => null)
  textUnitPaperStances.value = textualUnits.value.map(() => null)
  textUnitMemos.value = textualUnits.value.map(() => '')
}

function loadDetailPreviewMock() {
  if (previewDemoKind.value === 'paper') loadPaperPreviewMock()
  else if (previewDemoKind.value === 'review') loadReviewPreviewMock()
  else loadImagePreviewMock()
}

function reloadPreviewDemo() {
  loadDetailPreviewMock()
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

onMounted(async () => {
  if (isPreviewMode.value) {
    syncPreviewKindFromRoute()
    loadDetailPreviewMock()
    return
  }
  try {
    const response = (await reviewer.getReviewTaskDetail(manual_review_id.value)).data as Record<string, unknown>
    reviewTaskKind.value = String(response.task_kind || 'image')

    reviewRequestMeta.value = (response.review_request as typeof reviewRequestMeta.value) ?? null
    manualReviewStatus.value = (response.manual_review_status as string) || 'undo'

    const k = normTaskKind(reviewTaskKind.value)
    const imageLike = k === 'image' || k === 'image_detection' || k === ''

    if (imageLike) {
      const rawImgs = (response as { imgs?: Image[]; image_urls?: string[]; image_ids?: number[] }).imgs?.length
        ? (response as { imgs: Image[] }).imgs
        : ((response as { image_urls?: string[]; image_ids?: number[] }).image_urls || []).map((url: string, i: number) => ({
            id: (response as { image_ids?: number[] }).image_ids?.[i],
            url,
          }))

      images.value = rawImgs.filter((x: Image) => x && x.id != null && x.url)
      if (!images.value.length) {
        snackbar.showMessage('未获取到任务图片，请确认管理端已审批通过且任务已分配', 'error')
        return
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
      fetchMaskImage()
      fetchDetectionResults()
    } else {
      initTextualTaskFromResponse(response)
      if (!textualUnits.value.length) {
        snackbar.showMessage('未获取到论文/Review 材料单元', 'error')
      }
    }
  } catch {
    snackbar.showMessage('获取任务详情失败', 'error')
  }
})

watch(
  () => route.query.preview_kind,
  () => {
    if (!isPreviewMode.value) return
    syncPreviewKindFromRoute()
    loadDetailPreviewMock()
  }
)

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
  if (isPreviewMode.value) {
    return
  }
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
        message: `材料单元 ${i + 1} 尚未选择鉴定结论（FR-YHSH-0002：确认造假 / 疑似造假 / 未发现异常）`,
      }
    }
    if (isPaperTaskKind.value && !textUnitPaperStances.value[i]) {
      return {
        complete: false,
        message: `材料单元 ${i + 1} 尚未选择结论类型（FR-YHSH-0005：同意系统倾向 / 存在重大异议）`,
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
  if (v === 'confirmed_fake') return true
  if (v === 'no_issue') return false
  if (v === 'suspected') return null
  return null
}

const constructData = () => {
  if (!isImageTaskKind.value) {
    return {
      task_kind: reviewTaskKind.value,
      result: textualUnits.value.map((u, i) => ({
        segment_id: u.id,
        img_id: u.id,
        unit_label: u.label,
        verdict: textUnitVerdicts.value[i],
        paper_stance: textUnitPaperStances.value[i],
        memo: textUnitMemos.value[i],
        score: dimensionsPerTextUnit.value[i].map(dim => dim.value),
        reason: dimensionsPerTextUnit.value[i].map(dim => dim.reason),
        final: verdictToFinal(textUnitVerdicts.value[i]),
        points: dimensionsPerTextUnit.value[i].map(dim => dim.drawingPaths),
      })),
    }
  }
  const data: { task_kind: string; result: ImageItem[] } = {
    task_kind: reviewTaskKind.value,
    result: [],
  }
  for (let i = 0; i < images.value.length; i++) {
    const item: ImageItem = {
      img_id: images.value[i].id,
      score: dimensionsPerImage.value[i].map(dim => dim.value),
      reason: dimensionsPerImage.value[i].map(dim => dim.reason),
      final: imageJudgements.value[i],
      points: dimensionsPerImage.value[i].map(dim => dim.drawingPaths),
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
  if (isPreviewMode.value) {
    snackbar.showMessage('界面预览：校验通过，未调用提交接口', 'success')
    manualReviewStatus.value = 'completed'
    router.push('/review')
    return
  }
  try {
    await reviewer.submitReview(manual_review_id.value, constructData())
    snackbar.showMessage('提交成功，发布者将收到进度更新', 'success')
    manualReviewStatus.value = 'completed'
    router.push('/review')
  } catch {
    snackbar.showMessage('提交失败', 'error')
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