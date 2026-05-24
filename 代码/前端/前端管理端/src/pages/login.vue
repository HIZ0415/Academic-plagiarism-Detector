<template>
    <div class="login-page">
      <!-- 左侧功能介绍区域 -->
      <div class="feature-section">
        <div class="feature-content">
          <h1 class="text-h4 font-weight-bold mb-12">学术内容诚信 · 管理端</h1>
          <div class="feature-grid">
            <div class="feature-item">
              <div class="feature-icon">
                <v-icon size="32" color="primary">mdi-magnify</v-icon>
              </div>
              <div class="feature-text">
                <div class="text-subtitle-1 font-weight-medium">AI 图像检测</div>
                <div class="text-body-2 text-grey">基于深度学习与图像分析技术，识别重复、篡改、拼接等学术图像异常。</div>
              </div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">
                <v-icon size="32" color="primary">mdi-compare</v-icon>
              </div>
              <div class="feature-text">
                <div class="text-subtitle-1 font-weight-medium">自动化筛查</div>
                <div class="text-body-2 text-grey">AI预检测可在数秒内完成初筛，大幅降低人工审核成本，提升出版社工作效率</div>
              </div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">
                <v-icon size="32" color="primary">mdi-account-group</v-icon>
              </div>
              <div class="feature-text">
                <div class="text-subtitle-1 font-weight-medium">双重验证机制</div>
                <div class="text-body-2 text-grey">AI初检+人工复核双保险，确保结果客观可信，降低误判风险。</div>
              </div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">
                <v-icon size="32" color="primary">mdi-pencil</v-icon>
              </div>
              <div class="feature-text">
                <div class="text-subtitle-1 font-weight-medium">多角色协同平台</div>
                <div class="text-body-2 text-grey">支持出版社、审稿人多端登录，任务进度实时追踪，反馈结果集中归档。</div>
              </div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">
                <v-icon size="32" color="primary">mdi-school</v-icon>
              </div>
              <div class="feature-text">
                <div class="text-subtitle-1 font-weight-medium">可追溯审计</div>
                <div class="text-body-2 text-grey">所有操作留痕，满足出版机构对流程透明性与合规性的严格要求</div>
              </div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">
                <v-icon size="32" color="primary">mdi-chart-bar</v-icon>
              </div>
              <div class="feature-text">
                <div class="text-subtitle-1 font-weight-medium">多维统计分析</div>
                <div class="text-body-2 text-grey">自动生成结构化检测报告，附带篡改区域标记与证据链，助力学术争议裁定。</div>
              </div>
            </div>
          </div>
        </div>
      </div>
  
      <!-- 右侧登录 / 注册 -->
      <div class="login-section">
        <div class="login-container">
          <div class="d-flex mb-6 rounded-lg overflow-hidden border">
            <v-btn
              class="flex-grow-1 rounded-0"
              :variant="mode === 'login' ? 'flat' : 'text'"
              :color="mode === 'login' ? 'primary' : undefined"
              @click="mode = 'login'"
            >
              登录
            </v-btn>
            <v-btn
              class="flex-grow-1 rounded-0"
              :variant="mode === 'register' ? 'flat' : 'text'"
              :color="mode === 'register' ? 'primary' : undefined"
              @click="mode = 'register'"
            >
              注册
            </v-btn>
          </div>

          <p v-if="mode === 'register'" class="text-caption text-medium-emphasis mb-4">
            使用组织发放的<strong>邀请码</strong>注册；账号角色（发布者/审稿人）由邀请码决定。
            进入本<strong>管理后台</strong>需使用<strong>管理员</strong>账号登录（由超级管理员创建或数据库配置）。
          </p>

          <v-form ref="form" @submit.prevent="handleSubmit">
            <template v-if="mode === 'login'">
              <v-alert type="info" variant="tonal" density="compact" class="mb-4 text-caption">
                本地联调：<strong>组织内人工审核审批</strong>请用
                <code>org_admin@example.com</code> / <code>OrgAdmin123!</code><br>
                跨组织治理用 <code>admin@mail.com</code> / <code>Admin123!</code>。
              </v-alert>
              <v-text-field
                v-model="email"
                label="请输入邮箱"
                variant="outlined"
                density="comfortable"
                class="mb-4"
                prepend-inner-icon="mdi-email"
                :rules="loginRules.email"
              ></v-text-field>

              <v-text-field
                v-model="password"
                label="输入密码"
                variant="outlined"
                density="comfortable"
                class="mb-4"
                type="password"
                prepend-inner-icon="mdi-lock"
                :rules="loginRules.password"
              ></v-text-field>
            </template>

            <template v-else>
              <v-text-field
                v-model="registerForm.username"
                label="用户名"
                variant="outlined"
                density="comfortable"
                class="mb-4"
                prepend-inner-icon="mdi-account"
                :rules="registerRules.username"
              ></v-text-field>
              <v-text-field
                v-model="registerForm.email"
                label="邮箱"
                variant="outlined"
                density="comfortable"
                class="mb-4"
                prepend-inner-icon="mdi-email"
                :rules="registerRules.email"
              ></v-text-field>
              <v-text-field
                v-model="registerForm.password"
                label="密码"
                variant="outlined"
                density="comfortable"
                class="mb-4"
                type="password"
                prepend-inner-icon="mdi-lock"
                :rules="registerRules.password"
              ></v-text-field>
              <v-text-field
                v-model="registerForm.confirmPassword"
                label="确认密码"
                variant="outlined"
                density="comfortable"
                class="mb-4"
                type="password"
                prepend-inner-icon="mdi-lock-check"
                :rules="registerRules.confirmPassword"
              ></v-text-field>
              <v-text-field
                v-model="registerForm.invitation_code"
                label="邀请码"
                variant="outlined"
                density="comfortable"
                class="mb-4"
                prepend-inner-icon="mdi-ticket-confirmation"
                hint="与发放方提供的邀请码一致"
                persistent-hint
                :rules="registerRules.invitation_code"
              ></v-text-field>
            </template>

            <!-- 验证码区域 -->
            <div class="captcha-section mb-6">
              <v-text-field
                v-model="captchaInput"
                label="请输入验证码"
                variant="outlined"
                density="comfortable"
                :error-messages="captchaError"
                class="captcha-input"
                prepend-inner-icon="mdi-shield-check"
              >
                <template v-slot:append>
                  <DynamicCaptcha
                    ref="captchaRef"
                    @update:code="code => captchaCode = code"
                  />
                </template>
              </v-text-field>
            </div>

            <v-checkbox
              v-model="agreement"
              label="我已阅读《隐私政策》和《使用协议》"
              hide-details
              class="mb-6"
            ></v-checkbox>

            <v-btn
              block
              color="primary"
              size="large"
              type="submit"
              :loading="registering"
              :disabled="!isFormValid"
            >
              {{ mode === 'login' ? '登录' : '注册' }}
            </v-btn>
          </v-form>
        </div>
      </div>
    </div>
  </template>
  
  <script setup lang="ts">
  import { ref, computed } from 'vue'
  import { useRouter } from 'vue-router'
  import DynamicCaptcha from '@/components/DynamicCaptcha.vue'
  import { useSnackbarStore } from '@/stores/snackbar';
  const snackbar = useSnackbarStore();
  import user from '@/api/user'
  import { useUserStore } from '@/stores/user';
  const userStore = useUserStore();
  
  const router = useRouter()
  const mode = ref<'login' | 'register'>('login')
  const captchaRef = ref()
  const email = ref('')
  const password = ref('')
  const agreement = ref(false)
  const form = ref(null)
  const registering = ref(false)

  const registerForm = ref({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    invitation_code: '',
  })
  
  // 验证码相关
  const captchaInput = ref('')
  const captchaCode = ref('')
  const captchaError = ref('')
  
  // 表单验证规则
  const loginRules = {
    email: [
      (v: string) => !!v || '邮箱不能为空',
      // (v: string) => /.+@.+\..+/.test(v) || '请输入有效的邮箱地址'
    ],
    password: [
      (v: string) => !!v || '密码不能为空',
      // (v: string) => v.length >= 6 || '密码至少6个字符'
    ]
  }

  const registerRules = {
    username: [
      (v: string) => !!v || '用户名不能为空',
      (v: string) => v.length >= 2 || '用户名至少 2 个字符',
    ],
    email: [
      (v: string) => !!v || '邮箱不能为空',
      (v: string) => /.+@.+\..+/.test(v) || '请输入有效的邮箱地址',
    ],
    password: [
      (v: string) => !!v || '密码不能为空',
      (v: string) => v.length >= 6 || '密码至少 6 个字符',
    ],
    confirmPassword: [
      (v: string) => !!v || '请再次输入密码',
      (v: string) => v === registerForm.value.password || '两次输入的密码不一致',
    ],
    invitation_code: [
      (v: string) => !!v || '邀请码不能为空',
      (v: string) => (v && v.length >= 6) || '邀请码长度不符合要求',
    ],
  }
  
  const validateCaptcha = () => {
    if (!captchaInput.value) {
      captchaError.value = '请输入验证码'
      return false
    }
    if (captchaInput.value.toLowerCase() !== captchaCode.value.toLowerCase()) {
      captchaError.value = '验证码错误'
      captchaInput.value = ''
      captchaRef.value?.refreshCaptcha()
      return false
    }
    captchaError.value = ''
    return true
  }
  
  const isFormValid = computed(() => {
    if (!agreement.value) return false
    if (!captchaInput.value) return false

    if (mode.value === 'login') {
      return !!(email.value && password.value)
    }

    const r = registerForm.value
    return !!(
      r.username &&
      r.email &&
      r.password &&
      r.confirmPassword === r.password &&
      r.invitation_code &&
      r.invitation_code.length >= 6 &&
      /.+@.+\..+/.test(r.email) &&
      r.password.length >= 6
    )
  })
  
  const handleSubmit = async () => {
    if (!validateCaptcha()) {
      return
    }

    if (mode.value === 'register') {
      registering.value = true
      try {
        await user.register({
          username: registerForm.value.username,
          email: registerForm.value.email,
          password: registerForm.value.password,
          role: 'publisher',
          invitation_code: registerForm.value.invitation_code,
        })
        snackbar.showMessage('注册成功，请使用管理员账号登录管理后台，或使用用户端登录（发布者/审稿人）', 'success')
        mode.value = 'login'
        email.value = registerForm.value.email
        password.value = ''
        registerForm.value = {
          username: '',
          email: '',
          password: '',
          confirmPassword: '',
          invitation_code: '',
        }
        captchaInput.value = ''
        captchaRef.value?.refreshCaptcha?.()
      } catch (error: unknown) {
        const err = error as { response?: { status?: number; data?: Record<string, unknown> } }
        let errorMessage = '注册失败，请稍后重试'
        if (err.response?.status === 400 && err.response.data) {
          const d = err.response.data
          const parts: string[] = []
          if (d.username) parts.push('用户名不可用')
          if (d.email) parts.push('邮箱已被使用或格式错误')
          if (d.invitation_code) parts.push('邀请码无效或已过期')
          if (d.non_field_errors) parts.push(String(d.non_field_errors))
          if (parts.length) errorMessage = parts.join('；')
        }
        snackbar.showMessage(errorMessage, 'error')
      } finally {
        registering.value = false
      }
      return
    }

    await user.login({
      email: email.value,
      password: password.value,
    }).then(async (res: { data: { access: string; refresh: string } }) => {
      localStorage.setItem("1-token", res.data.access)
      localStorage.setItem("1-refresh", res.data.refresh)
      localStorage.setItem("1-isLoggedIn", "true")

      await userStore.fetchUserInfo()

      snackbar.showMessage('登录成功', 'success')
      router.push('/')
    }).catch((error: unknown) => {
      console.log(error)
      const res = (error as { response?: { status?: number; data?: Record<string, unknown> } }).response
      let errorMessage = '网络错误，请稍后重试'
      if (res?.data) {
        const raw = res.data.non_field_errors
        const first = Array.isArray(raw) && raw.length ? String(raw[0]) : ''
        if (first.includes('Invalid credentials')) {
          errorMessage = '邮箱或密码错误'
        } else if (first.includes('not an admin') || first.includes('Invalid role')) {
          errorMessage =
            '该账号不是管理员：后端要求 user.role 为 admin。若邮箱无误，请在库里将该用户的 role 设为 admin，或使用一键启动脚本创建的本地管理员账号登录。'
        } else if (first) {
          errorMessage = first
        } else {
          errorMessage = '登录失败，请检查账号是否为管理员或联系后端同学查看接口返回'
        }
      } else if (res?.status === 401) {
        errorMessage = '邮箱或密码错误'
      } else if (res) {
        errorMessage = '登录失败，请检查网络或账号权限'
      }
      snackbar.showMessage(errorMessage, 'error')
    })
  }
  </script>
  
  <style scoped>
  .login-page {
    display: flex;
    min-height: 100vh;
    background-color: var(--v-theme-background);
    padding-top: 40px;
  }
  
  .feature-section {
    flex: 1;
    padding: 24px 48px;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    background-color: var(--v-theme-surface);
  }
  
  .feature-content {
    max-width: 800px;
    margin-top: -20px;
  }
  
  .feature-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 32px;
  }
  
  .feature-item {
    display: flex;
    align-items: flex-start;
    gap: 16px;
  }
  
  .feature-icon {
    padding: 12px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 12px;
  }
  
  .feature-text {
    flex: 1;
  }
  
  .login-section {
    width: 480px;
    background-color: var(--v-theme-surface);
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding: 32px 48px;
    margin-top: -20px;
  }
  
  .login-container {
    width: 100%;
    max-width: 400px;
    background-color: var(--v-theme-surface);
  }
  
  .v-btn {
    text-transform: none !important;
    background-color: var(--v-theme-primary);
    color: var(--v-theme-on-primary);
  }
  
  .v-btn.v-btn--size-large {
    height: 44px;
    font-size: 16px;
    font-weight: 500;
    box-shadow: 0 2px 4px rgba(64, 158, 255, 0.2);
    transition: all 0.3s ease;
  }
  
  .v-btn.v-btn--size-large:hover {
    background-color: var(--v-theme-primary-light);
    box-shadow: 0 4px 8px rgba(64, 158, 255, 0.3);
    transform: translateY(-1px);
  }
  
  .v-btn.v-btn--size-large:active {
    background-color: var(--v-theme-primary-dark);
    transform: translateY(0);
  }
  
  .captcha-section {
    width: 100%;
  }
  
  .captcha-input {
    width: 100%;
  }
  
  :deep(.v-field__append-inner) {
    padding-top: 6px;
  }
  
  @media (max-width: 1024px) {
    .login-page {
      flex-direction: column;
      padding-top: 20px;
    }
  
    .feature-section {
      padding: 24px;
    }
  
    .feature-content {
      margin-top: 0;
    }
  
    .login-section {
      width: 100%;
      margin-top: 0;
      padding: 24px;
    }
  
    .feature-grid {
      grid-template-columns: 1fr;
    }
  }
  </style> 
