<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 via-white to-blue-50 py-12 px-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <router-link to="/" class="inline-flex items-center gap-2 text-2xl font-bold text-primary-600 mb-2">
          <svg class="w-10 h-10" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#3B82F6"/><text x="16" y="22" text-anchor="middle" fill="white" font-size="18" font-weight="bold" font-family="Arial">A</text></svg>
          AgentHub
        </router-link>
        <p class="text-gray-500">AI能力市场 — 创建新账户</p>
      </div>

      <div class="bg-white rounded-2xl shadow-xl shadow-primary-100/50 p-8">
        <form @submit.prevent="handleRegister" class="space-y-5">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">用户名</label>
            <input v-model="form.username" type="text" required
              class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition"
              placeholder="请输入用户名" />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">邮箱</label>
            <input v-model="form.email" type="email" required
              class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition"
              placeholder="请输入邮箱" />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">密码</label>
            <input v-model="form.password" type="password" required
              class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition"
              placeholder="请输入密码（至少6位）" />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">角色</label>
            <div class="grid grid-cols-2 gap-3">
              <button type="button" @click="form.role = 'customer'"
                class="p-3 rounded-xl border-2 text-center transition"
                :class="form.role === 'customer' ? 'border-primary-500 bg-primary-50 text-primary-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'">
                <svg class="w-6 h-6 mx-auto mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>
                <span class="text-sm font-medium">客户</span>
                <p class="text-xs mt-0.5 opacity-75">使用AI能力</p>
              </button>
              <button type="button" @click="form.role = 'developer'"
                class="p-3 rounded-xl border-2 text-center transition"
                :class="form.role === 'developer' ? 'border-primary-500 bg-primary-50 text-primary-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'">
                <svg class="w-6 h-6 mx-auto mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg>
                <span class="text-sm font-medium">开发者</span>
                <p class="text-xs mt-0.5 opacity-75">发布AI能力</p>
              </button>
            </div>
          </div>

          <div v-if="error" class="p-3 bg-red-50 text-red-600 text-sm rounded-xl">
            {{ error }}
          </div>

          <button type="submit" :disabled="loading"
            class="w-full py-2.5 bg-primary-500 text-white rounded-xl font-medium hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition">
            <span v-if="loading">注册中...</span>
            <span v-else>注 册</span>
          </button>
        </form>

        <p class="mt-6 text-center text-sm text-gray-500">
          已有账户？
          <router-link to="/login" class="text-primary-600 hover:text-primary-700 font-medium">立即登录</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { authAPI } from '../api'
import { useAuth } from '../stores/auth'

const router = useRouter()
const { setAuth } = useAuth()

const form = reactive({ username: '', email: '', password: '', role: 'customer' })
const loading = ref(false)
const error = ref('')

async function handleRegister() {
  error.value = ''
  loading.value = true
  try {
    await authAPI.register(form)
    // Auto login after register
    const { data: loginData } = await authAPI.login({ username: form.username, password: form.password })
    setAuth(loginData)
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || '注册失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>
