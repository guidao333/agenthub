<template>
  <div class="h-[calc(100vh-56px)] flex">
    <!-- Sidebar -->
    <div class="w-72 bg-dark-700 text-white flex flex-col shrink-0">
      <div class="p-4 border-b border-gray-700">
        <router-link to="/" class="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition mb-3">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
          返回市场
        </router-link>
        <h2 class="text-lg font-semibold">对话</h2>
      </div>

      <!-- Session list -->
      <div class="flex-1 overflow-y-auto p-3 space-y-1">
        <div v-for="s in sessions" :key="s.session_id"
          @click="switchSession(s.session_id)"
          class="px-3 py-2.5 rounded-lg cursor-pointer transition text-sm flex items-center justify-between group"
          :class="currentSessionId === s.session_id ? 'bg-primary-600 text-white' : 'text-gray-300 hover:bg-white/5'">
          <span class="truncate">{{ s.capability_name || s.capability_id || '对话' }}</span>
          <button @click.stop="deleteSession(s.session_id)" class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-400 transition">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
          </button>
        </div>
        <div v-if="!sessions.length" class="text-gray-500 text-sm text-center py-8">
          暂无对话
        </div>
      </div>

      <div class="p-3 border-t border-gray-700">
        <router-link to="/dashboard" class="block text-center py-2 text-sm text-gray-400 hover:text-white transition">
          ← 控制台
        </router-link>
      </div>
    </div>

    <!-- Chat Area -->
    <div class="flex-1 flex flex-col bg-gray-50">
      <!-- Header -->
      <div class="px-6 py-3 bg-white border-b border-gray-200 flex items-center justify-between">
        <div>
          <h3 class="font-semibold text-gray-900">{{ currentCapName || '对话' }}</h3>
          <p class="text-xs text-gray-500">会话 ID: {{ currentSessionId || '-' }}</p>
        </div>
      </div>

      <!-- Messages -->
      <div ref="messagesRef" class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        <div v-if="!currentSessionId" class="flex items-center justify-center h-full text-gray-400">
          <div class="text-center">
            <svg class="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/></svg>
            <p>选择左侧对话或从订阅开始新对话</p>
          </div>
        </div>
        <template v-else>
          <ChatMessage v-for="(msg, idx) in messages" :key="idx" :msg="msg" :streaming="streaming && idx === messages.length - 1 && msg.role === 'assistant'" />
          <div v-if="messages.length === 0" class="text-center text-gray-400 py-10">
            发送消息开始对话
          </div>
        </template>
      </div>

      <!-- Input -->
      <div v-if="currentSessionId" class="px-6 py-4 bg-white border-t border-gray-200">
        <form @submit.prevent="sendMessage" class="flex gap-3">
          <input v-model="inputMsg" :disabled="streaming"
            class="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none disabled:bg-gray-50"
            placeholder="输入消息..." />
          <button type="submit" :disabled="streaming || !inputMsg.trim()"
            class="px-5 py-2.5 bg-primary-500 text-white rounded-xl font-medium hover:bg-primary-600 disabled:opacity-50 transition flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>
            发送
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { chatAPI, dashboardAPI } from '../api'
import ChatMessage from '../components/ChatMessage.vue'

const route = useRoute()
const router = useRouter()

const sessions = ref([])
const currentSessionId = ref(route.params.sessionId || '')
const currentCapName = ref('')
const messages = ref([])
const inputMsg = ref('')
const streaming = ref(false)
const messagesRef = ref(null)

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  })
}

async function loadSessions() {
  try {
    const { data } = await dashboardAPI.subscriptions()
    sessions.value = (data.items || data || []).map(s => ({
      session_id: s.capability_id,
      capability_id: s.capability_id,
      capability_name: s.capability_name || s.name,
    }))
  } catch {
    sessions.value = []
  }
}

async function loadHistory() {
  if (!currentSessionId.value) return
  messages.value = []
  try {
    const { data } = await chatAPI.history(currentSessionId.value)
    messages.value = (data.items || data || []).map(m => ({
      role: m.role,
      content: m.content,
    }))
    scrollToBottom()
  } catch {}
}

async function switchSession(id) {
  currentSessionId.value = id
  router.replace({ name: 'chat', params: { sessionId: id } })
  await loadHistory()
}

async function deleteSession(id) {
  if (!confirm('确定删除此对话？')) return
  try {
    await chatAPI.deleteSession(id)
    sessions.value = sessions.value.filter(s => s.session_id !== id)
    if (currentSessionId.value === id) {
      currentSessionId.value = ''
      messages.value = []
    }
  } catch {}
}

async function sendMessage() {
  const text = inputMsg.value.trim()
  if (!text || streaming.value || !currentSessionId.value) return

  messages.value.push({ role: 'user', content: text })
  inputMsg.value = ''
  streaming.value = true
  scrollToBottom()

  // Add empty assistant message for streaming
  messages.value.push({ role: 'assistant', content: '' })
  const assistantIdx = messages.value.length - 1

  try {
    const response = await chatAPI.sendMessage(currentSessionId.value, text)
    if (!response.ok) throw new Error('请求失败')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') continue
          try {
            const parsed = JSON.parse(data)
            if (parsed.content) {
              messages.value[assistantIdx].content += parsed.content
              scrollToBottom()
            }
          } catch {
            // Not JSON, treat as plain text
            messages.value[assistantIdx].content += data
            scrollToBottom()
          }
        }
      }
    }
  } catch (e) {
    messages.value[assistantIdx].content = '请求失败，请重试。' + (e.message || '')
  } finally {
    streaming.value = false
    scrollToBottom()
  }
}

watch(() => route.params.sessionId, (id) => {
  if (id && id !== currentSessionId.value) {
    currentSessionId.value = id
    loadHistory()
  }
})

onMounted(async () => {
  await loadSessions()
  if (currentSessionId.value) {
    await loadHistory()
  }
})
</script>
