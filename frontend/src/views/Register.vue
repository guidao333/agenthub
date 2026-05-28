<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <router-link to="/" class="inline-flex items-center gap-2 text-2xl font-bold text-primary-600 mb-2">
          <svg class="w-10 h-10" viewBox="0 0 32 32">
            <rect width="32" height="32" rx="8" fill="#3B82F6" />
            <text x="16" y="22" text-anchor="middle" fill="white" font-size="18" font-weight="bold" font-family="Arial">A</text>
          </svg>
          AgentHub
        </router-link>
        <p class="text-gray-500">创建账号，进入 AI 能力市场</p>
      </div>

      <div class="bg-white rounded-lg border border-gray-200 shadow-sm p-8">
        <form @submit.prevent="handleRegister" class="space-y-5">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">用户名</label>
            <input
              v-model.trim="form.username"
              type="text"
              required
              class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition"
              placeholder="请输入用户名"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">邮箱</label>
            <input
              v-model.trim="form.email"
              type="email"
              required
              class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition"
              placeholder="请输入邮箱"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">密码</label>
            <input
              v-model="form.password"
              type="password"
              required
              minlength="6"
              class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition"
              placeholder="请输入密码，至少 6 位"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">账号类型</label>
            <div class="grid grid-cols-2 gap-3">
              <button
                type="button"
                @click="form.role = 'customer'"
                class="p-4 rounded-lg border text-center transition"
                :class="form.role === 'customer' ? 'border-primary-500 bg-primary-50 text-primary-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'"
              >
                <span class="block text-sm font-semibold">客户</span>
                <span class="block text-xs mt-1 opacity-75">订阅和使用能力</span>
              </button>
              <button
                type="button"
                @click="form.role = 'developer'"
                class="p-4 rounded-lg border text-center transition"
                :class="form.role === 'developer' ? 'border-primary-500 bg-primary-50 text-primary-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'"
              >
                <span class="block text-sm font-semibold">开发者</span>
                <span class="block text-xs mt-1 opacity-75">创建和发布能力</span>
              </button>
            </div>
          </div>

          <div v-if="error" class="p-3 bg-red-50 text-red-600 text-sm rounded-lg">
            {{ error }}
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full py-2.5 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {{ loading ? '注册中...' : submitText }}
          </button>
        </form>

        <p class="mt-6 text-center text-sm text-gray-500">
          已有账号？
          <router-link to="/login" class="text-primary-600 hover:text-primary-700 font-medium">立即登录</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authAPI } from '../api'
import { useAuth } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const { setAuth } = useAuth()

const form = reactive({ username: '', email: '', password: '', role: 'customer' })
const loading = ref(false)
const error = ref('')

const submitText = computed(() => form.role === 'developer' ? '注册并进入开发者中心' : '注册并进入市场')

onMounted(() => {
  if (route.query.role === 'developer') {
    form.role = 'developer'
  }
})

async function handleRegister() {
  error.value = ''
  loading.value = true
  try {
    await authAPI.register(form)
    const { data: loginData } = await authAPI.login({ username: form.username, password: form.password })
    setAuth(loginData)
    router.push(form.role === 'developer' ? '/developer' : '/')
  } catch (e) {
    error.value = e.response?.data?.detail || '注册失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>
