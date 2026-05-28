<template>
  <nav class="bg-white border-b border-gray-200 sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-14">
        <router-link to="/" class="flex items-center gap-2 text-xl font-bold text-primary-600">
          <svg class="w-8 h-8" viewBox="0 0 32 32" fill="none">
            <rect width="32" height="32" rx="8" fill="#3B82F6" />
            <text x="16" y="22" text-anchor="middle" fill="white" font-size="18" font-weight="bold" font-family="Arial">A</text>
          </svg>
          AgentHub
        </router-link>

        <div class="flex items-center gap-1">
          <router-link
            :to="developerEntryTo"
            class="nav-link"
            :class="{ active: $route.name === 'developer' }"
          >
            开发者入驻
          </router-link>

          <router-link to="/" class="nav-link" :class="{ active: $route.name === 'market' }">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z" />
            </svg>
            市场
          </router-link>

          <template v-if="isLoggedIn">
            <router-link
              v-if="isCustomer || isDeveloper || isAdmin"
              to="/dashboard"
              class="nav-link"
              :class="{ active: $route.name === 'dashboard' }"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
              </svg>
              控制台
            </router-link>

            <router-link
              v-if="isCustomer || isAdmin"
              to="/chat"
              class="nav-link"
              :class="{ active: $route.name === 'chat' }"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              对话
            </router-link>

            <router-link v-if="isAdmin" to="/vision" class="nav-link" :class="{ active: $route.name === 'vision' }">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              AI视觉
            </router-link>

            <router-link v-if="isAdmin" to="/admin" class="nav-link" :class="{ active: $route.name === 'admin' }">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              管理
            </router-link>
          </template>

          <div class="w-px h-6 bg-gray-200 mx-2"></div>

          <template v-if="isLoggedIn">
            <div class="relative" ref="menuRef">
              <button @click="showMenu = !showMenu" class="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-gray-100 text-sm text-gray-700">
                <div class="w-7 h-7 rounded-full bg-primary-100 text-primary-600 flex items-center justify-center text-xs font-bold">
                  {{ username.charAt(0).toUpperCase() }}
                </div>
                {{ username }}
                <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              <div v-if="showMenu" class="absolute right-0 mt-1 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
                <div class="px-4 py-2 text-xs text-gray-500 border-b">
                  {{ roleLabel }}
                </div>
                <button @click="logout" class="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50">
                  退出登录
                </button>
              </div>
            </div>
          </template>
          <template v-else>
            <router-link to="/login" class="px-4 py-1.5 text-sm text-gray-600 hover:text-gray-900">登录</router-link>
            <router-link to="/register" class="px-4 py-1.5 text-sm bg-primary-500 text-white rounded-lg hover:bg-primary-600">注册</router-link>
          </template>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../stores/auth'

const router = useRouter()
const { isLoggedIn, role, username, clearAuth } = useAuth()
const showMenu = ref(false)
const menuRef = ref(null)

const isCustomer = computed(() => role.value === 'customer')
const isDeveloper = computed(() => role.value === 'developer')
const isAdmin = computed(() => role.value === 'admin')

const developerEntryTo = computed(() => {
  if (isDeveloper.value || isAdmin.value) return '/developer'
  return { path: '/register', query: { role: 'developer' } }
})

const roleLabel = computed(() => ({
  customer: '客户',
  developer: '开发者',
  admin: '管理员',
})[role.value] || role.value)

function logout() {
  clearAuth()
  showMenu.value = false
  router.push('/')
}

function handleClickOutside(e) {
  if (menuRef.value && !menuRef.value.contains(e.target)) {
    showMenu.value = false
  }
}

onMounted(() => document.addEventListener('click', handleClickOutside))
onUnmounted(() => document.removeEventListener('click', handleClickOutside))
</script>

<style scoped>
.nav-link {
  @apply flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition-colors;
}
.nav-link.active {
  @apply text-primary-600 bg-primary-50;
}
</style>
