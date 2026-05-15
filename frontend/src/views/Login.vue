<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 via-white to-blue-50 py-12 px-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <router-link to="/" class="inline-flex items-center gap-2 text-2xl font-bold text-primary-600 mb-2">
          <svg class="w-10 h-10" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#3B82F6"/><text x="16" y="22" text-anchor="middle" fill="white" font-size="18" font-weight="bold" font-family="Arial">A</text></svg>
          AgentHub
        </router-link>
        <p class="text-gray-500">AI能力市场 — 登录您的账户</p>
      </div>

      <div class="bg-white rounded-2xl shadow-xl shadow-primary-100/50 p-8">
        <form @submit.prevent="handleLogin" class="space-y-5">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">用户名</label>
            <input v-model="form.username" type="text" required autocomplete="username"
              class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition"
              placeholder="请输入用户名" />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1.5">密码</label>
            <input v-model="form.password" type="password" required autocomplete="current-password"
              class="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition"
              placeholder="请输入密码" />
          </div>

          <div v-if="error" class="p-3 bg-red-50 text-red-600 text-sm rounded-xl">
            {{ error }}
          </div>

          <button type="submit" :disabled="loading"
            class="w-full py-2.5 bg-primary-500 text-white rounded-xl font-medium hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition">
            <span v-if="loading">登录中...</span>
            <span v-else>登 录</span>
          </button>
        </form>

        <p class="mt-6 text-center text-sm text-gray-500">
          还没有账户？
          <router-link to="/register" class="text-primary-600 hover:text-primary-700 font-medium">立即注册</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { authAPI } from '../api'
import { useAuth } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const { setAuth } = useAuth()

const form = reactive({ username: '', password: '' })
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    const { data } = await authAPI.login(form)
    setAuth(data)
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  } catch (e) {
    error.value = e.response?.data?.detail || '登录失败，请检查用户名和密码'
  } finally {
    loading.value = false
  }
}
</script>
