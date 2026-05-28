<template>
  <div class="min-h-screen bg-gray-50">
    <header class="sticky top-0 z-10 h-14 bg-gray-950 flex items-center gap-4 px-5 shadow">
      <span class="text-white font-bold text-base">AgentHub 能力配置</span>
      <router-link to="/dashboard" class="ml-auto text-slate-300 hover:text-white text-sm">返回控制台</router-link>
    </header>

    <div class="max-w-3xl mx-auto px-4 py-6">
      <div v-if="loading" class="flex items-center justify-center py-20 text-gray-500 text-sm">
        正在加载配置...
      </div>

      <div v-else-if="loadError" class="rounded-lg border border-red-200 bg-red-50 p-5 text-sm text-red-700">
        {{ loadError }}
        <div class="mt-3">
          <router-link to="/" class="text-red-600 underline">去市场订阅</router-link>
          &nbsp;·&nbsp;
          <router-link to="/dashboard" class="text-red-600 underline">返回控制台</router-link>
        </div>
      </div>

      <template v-else>
        <!-- 配置状态条 -->
        <div
          class="mb-4 flex items-center gap-2 rounded-lg px-4 py-3 text-sm"
          :class="configData.is_configured ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'"
        >
          <span class="h-2 w-2 rounded-full bg-current shrink-0"></span>
          <span>{{ configData.is_configured ? '已配置，客户端下次心跳会自动同步。' : '尚未配置，请填写以下信息并保存。' }}</span>
        </div>

        <!-- 客户端状态 -->
        <div class="mb-4 rounded-lg border border-gray-200 bg-white p-4">
          <h3 class="text-sm font-semibold text-gray-900 mb-3">统一客户端状态</h3>
          <div
            class="flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm"
            :class="matchedDevices.length ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'"
          >
            <span class="h-2 w-2 rounded-full bg-current shrink-0"></span>
            <span v-if="matchedDevices.length">
              当前能力已有 {{ matchedDevices.length }} 台在线客户端可执行任务。
            </span>
            <span v-else>
              未检测到在线客户端。请先下载并启动统一客户端，输入订阅 API Key。
            </span>
          </div>
          <div v-if="matchedDevices.length" class="mt-3 space-y-2">
            <div
              v-for="device in matchedDevices"
              :key="device.device_id"
              class="rounded-lg bg-gray-50 border border-gray-100 px-3 py-2.5"
            >
              <p class="font-mono text-xs font-semibold text-gray-900 break-all">{{ device.device_id }}</p>
              <p class="mt-1 text-xs text-gray-500">
                版本 {{ device.client_version || '-' }} · 心跳 {{ heartbeatText(device) }}
              </p>
              <div class="mt-2 flex flex-wrap gap-1.5">
                <span
                  v-for="plugin in device.plugin_capabilities || []"
                  :key="plugin.cap_id"
                  class="rounded-full bg-white border border-gray-200 px-2 py-0.5 text-xs text-gray-600"
                >
                  {{ plugin.name || plugin.cap_id }} · {{ (plugin.actions || []).length }} 个动作
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- API Key -->
        <div class="mb-4 rounded-lg border border-gray-200 bg-white p-4">
          <h3 class="text-sm font-semibold text-gray-900 mb-1">客户端 API Key</h3>
          <p class="text-xs text-gray-500 mb-3">
            安装 Windows 客户端后，在本地工作台粘贴这个 Key 绑定当前订阅能力。
          </p>
          <div class="flex items-center gap-3 rounded-lg bg-gray-50 border border-gray-200 px-3 py-2.5">
            <span class="font-mono text-sm text-gray-800 break-all flex-1 min-w-0 select-all">
              {{ keyRevealed ? configData.api_key : maskedKey }}
            </span>
            <div class="flex shrink-0 gap-2">
              <button
                type="button"
                class="h-8 rounded-lg border border-gray-300 bg-white px-3 text-xs font-semibold text-gray-700 hover:bg-gray-50"
                @click="keyRevealed = !keyRevealed"
              >
                {{ keyRevealed ? '隐藏' : '查看' }}
              </button>
              <button
                type="button"
                class="h-8 rounded-lg border border-gray-300 bg-white px-3 text-xs font-semibold text-gray-700 hover:bg-gray-50"
                @click="copyKey"
              >
                复制
              </button>
            </div>
          </div>
        </div>

        <!-- 能力描述 -->
        <div v-if="configData.description" class="mb-4 rounded-lg border border-gray-200 bg-white p-4">
          <p class="text-sm text-gray-600 leading-relaxed">{{ configData.description }}</p>
        </div>

        <!-- 配置表单（分组） -->
        <template v-if="hasFields && groups.length">
          <div
            v-for="group in groups"
            :key="group.title"
            class="mb-4 rounded-lg border border-gray-200 bg-white p-4"
          >
            <h3 class="text-sm font-semibold text-gray-900 mb-4">{{ group.title }}</h3>
            <div class="space-y-4">
              <template v-for="key in group.fields" :key="key">
                <div v-if="schemaProps[key]" class="space-y-1">
                  <label class="block text-xs font-semibold text-gray-700">
                    {{ schemaProps[key].title || key }}<span v-if="required.includes(key)" class="text-red-500 ml-0.5">*</span>
                  </label>
                  <!-- select -->
                  <select
                    v-if="schemaProps[key].type === 'select'"
                    v-model="formValues[key]"
                    class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                  >
                    <option
                      v-for="opt in getOptions(schemaProps[key])"
                      :key="opt.value"
                      :value="opt.value"
                    >{{ opt.label }}{{ opt.status ? `（${statusLabel(opt.status)}）` : '' }}</option>
                  </select>
                  <!-- multiselect -->
                  <div
                    v-else-if="schemaProps[key].type === 'multiselect'"
                    class="grid grid-cols-2 gap-2 sm:grid-cols-3"
                  >
                    <label
                      v-for="opt in getOptions(schemaProps[key])"
                      :key="opt.value"
                      class="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs cursor-pointer hover:border-gray-300"
                    >
                      <input
                        type="checkbox"
                        :value="opt.value"
                        v-model="formValues[key]"
                        class="h-4 w-4 rounded border-gray-300 text-blue-600"
                      />
                      <span>{{ opt.label }}{{ opt.status ? `（${statusLabel(opt.status)}）` : '' }}</span>
                    </label>
                  </div>
                  <!-- password -->
                  <input
                    v-else-if="schemaProps[key].type === 'password'"
                    type="password"
                    v-model="formValues[key]"
                    :placeholder="schemaProps[key].placeholder || ''"
                    class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                  />
                  <!-- textarea -->
                  <textarea
                    v-else-if="schemaProps[key].type === 'textarea'"
                    v-model="formValues[key]"
                    :placeholder="schemaProps[key].placeholder || ''"
                    rows="3"
                    class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 resize-y"
                  ></textarea>
                  <!-- number -->
                  <input
                    v-else-if="schemaProps[key].type === 'number'"
                    type="number"
                    v-model.number="formValues[key]"
                    :placeholder="schemaProps[key].placeholder || ''"
                    :min="schemaProps[key].minimum"
                    :max="schemaProps[key].maximum"
                    class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                  />
                  <!-- text (default) -->
                  <input
                    v-else
                    type="text"
                    v-model="formValues[key]"
                    :placeholder="schemaProps[key].placeholder || ''"
                    class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                  />
                  <p v-if="schemaProps[key].description" class="text-xs text-gray-500 leading-relaxed">
                    {{ schemaProps[key].description }}
                  </p>
                  <p v-if="getSourceDesc(schemaProps[key])" class="text-xs text-gray-500 leading-relaxed">
                    {{ getSourceDesc(schemaProps[key]) }}
                  </p>
                </div>
              </template>
            </div>
          </div>
        </template>

        <!-- 配置表单（无分组） -->
        <div v-else-if="hasFields" class="mb-4 rounded-lg border border-gray-200 bg-white p-4">
          <h3 class="text-sm font-semibold text-gray-900 mb-4">配置项</h3>
          <div class="space-y-4">
            <div v-for="(field, key) in schemaProps" :key="key" class="space-y-1">
              <label class="block text-xs font-semibold text-gray-700">
                {{ field.title || key }}<span v-if="required.includes(key)" class="text-red-500 ml-0.5">*</span>
              </label>
              <select
                v-if="field.type === 'select'"
                v-model="formValues[key]"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
              >
                <option
                  v-for="opt in getOptions(field)"
                  :key="opt.value"
                  :value="opt.value"
                >{{ opt.label }}{{ opt.status ? `（${statusLabel(opt.status)}）` : '' }}</option>
              </select>
              <div
                v-else-if="field.type === 'multiselect'"
                class="grid grid-cols-2 gap-2 sm:grid-cols-3"
              >
                <label
                  v-for="opt in getOptions(field)"
                  :key="opt.value"
                  class="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs cursor-pointer hover:border-gray-300"
                >
                  <input
                    type="checkbox"
                    :value="opt.value"
                    v-model="formValues[key]"
                    class="h-4 w-4 rounded border-gray-300 text-blue-600"
                  />
                  <span>{{ opt.label }}{{ opt.status ? `（${statusLabel(opt.status)}）` : '' }}</span>
                </label>
              </div>
              <input
                v-else-if="field.type === 'password'"
                type="password"
                v-model="formValues[key]"
                :placeholder="field.placeholder || ''"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
              />
              <textarea
                v-else-if="field.type === 'textarea'"
                v-model="formValues[key]"
                :placeholder="field.placeholder || ''"
                rows="3"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100 resize-y"
              ></textarea>
              <input
                v-else-if="field.type === 'number'"
                type="number"
                v-model.number="formValues[key]"
                :placeholder="field.placeholder || ''"
                :min="field.minimum"
                :max="field.maximum"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
              />
              <input
                v-else
                type="text"
                v-model="formValues[key]"
                :placeholder="field.placeholder || ''"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
              />
              <p v-if="field.description" class="text-xs text-gray-500 leading-relaxed">{{ field.description }}</p>
            </div>
          </div>
        </div>

        <div v-else class="mb-4 rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-500">
          该能力暂不需要额外配置。
        </div>

        <!-- 操作区 -->
        <div class="rounded-lg border border-gray-200 bg-white p-4">
          <div class="flex flex-wrap gap-3">
            <button
              type="button"
              :disabled="saving"
              class="h-10 rounded-lg bg-gray-950 px-5 text-sm font-semibold text-white hover:bg-gray-800 disabled:opacity-50"
              @click="saveConfig"
            >
              {{ saving ? '保存中...' : '保存配置' }}
            </button>
            <button
              type="button"
              :disabled="testing"
              class="h-10 rounded-lg border border-amber-400 bg-amber-50 px-5 text-sm font-semibold text-amber-800 hover:bg-amber-100 disabled:opacity-50"
              @click="testConfig"
            >
              {{ testing ? '检测中...' : '检测配置' }}
            </button>
            <router-link
              :to="`/cap-chat/${capId}`"
              class="inline-flex h-10 items-center rounded-lg border border-gray-300 bg-white px-5 text-sm font-semibold text-gray-700 hover:bg-gray-50"
            >
              打开对话
            </router-link>
            <a
              href="/downloads/AgentHubClientSetup-1.0.17.exe"
              class="inline-flex h-10 items-center rounded-lg border border-gray-300 bg-white px-5 text-sm font-semibold text-gray-700 hover:bg-gray-50"
            >
              下载客户端
            </a>
          </div>

          <!-- 检测结果 -->
          <div v-if="testResults" class="mt-4 space-y-2">
            <div class="rounded-lg px-4 py-3 text-sm" :class="statusClass(testResults.status)">
              <p class="font-semibold">{{ testResults.message || '检测完成' }}</p>
              <p class="mt-0.5 text-xs opacity-80">整体状态：{{ statusText(testResults.status) }}</p>
            </div>
            <div
              v-for="(item, i) in testResults.results || []"
              :key="i"
              class="rounded-lg px-4 py-3 text-sm"
              :class="statusClass(item.status)"
            >
              <p class="font-semibold">{{ item.name }}</p>
              <p class="mt-0.5 text-xs opacity-80">{{ item.message }}</p>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { capConfigAPI, dashboardAPI } from '../api'

const route = useRoute()
const capId = computed(() => route.params.capId)

const loading = ref(true)
const loadError = ref('')
const configData = ref({})
const adapterOptions = ref({})
const clientStatus = ref({ online: false, devices: [] })
const formValues = reactive({})
const keyRevealed = ref(false)
const saving = ref(false)
const testing = ref(false)
const testResults = ref(null)

const schemaProps = computed(() => configData.value.template?.properties || {})
const required = computed(() => configData.value.template?.required || [])
const groups = computed(() => configData.value.ui_schema?.groups || [])
const hasFields = computed(() => Object.keys(schemaProps.value).length > 0)

const maskedKey = computed(() => {
  const k = configData.value.api_key
  if (!k) return '未生成'
  if (k.length <= 14) return k
  return `${k.slice(0, 6)}****...${k.slice(-8)}`
})

const matchedDevices = computed(() => {
  const devices = clientStatus.value.devices || []
  return devices.filter(d =>
    (d.plugin_capabilities || []).some(p => p.cap_id === capId.value)
  )
})

function getOptions(field) {
  const source = field.options_key ? adapterOptions.value[field.options_key] : null
  if (source?.options) return source.options
  return (field.enum || []).map((v, i) => ({
    value: v,
    label: field.enum_labels?.[i] || v,
    status: '',
  }))
}

function getSourceDesc(field) {
  if (!field.options_key) return ''
  return adapterOptions.value[field.options_key]?.description || ''
}

function statusLabel(s) {
  return { trained: '已训练', generic: '通用', planned: '待适配', none: '不接入' }[s] || s
}

function heartbeatText(device) {
  const age = device?.last_heartbeat_age_seconds
  if (age == null) return '暂无心跳'
  if (age < 60) return `${age} 秒前`
  return `${Math.floor(age / 60)} 分钟前`
}

async function copyKey() {
  const key = configData.value.api_key
  if (!key) return
  try {
    await navigator.clipboard.writeText(key)
    alert('API Key 已复制')
  } catch {
    prompt('请手动复制：', key)
  }
}

function statusClass(status) {
  return {
    ok: 'bg-emerald-50 border border-emerald-200 text-emerald-800',
    warn: 'bg-amber-50 border border-amber-200 text-amber-800',
    error: 'bg-red-50 border border-red-200 text-red-800',
  }[status] || 'bg-gray-50 border border-gray-200 text-gray-700'
}

function statusText(s) {
  return { ok: '通过', warn: '有提醒', error: '有错误' }[s] || s
}

function initFormValues(values) {
  for (const [key, field] of Object.entries(schemaProps.value)) {
    const saved = values[key]
    if (field.type === 'multiselect') {
      formValues[key] = Array.isArray(saved) ? saved
        : (typeof saved === 'string' && saved) ? saved.split(',').filter(Boolean)
        : (Array.isArray(field.default) ? field.default : [])
    } else {
      formValues[key] = saved ?? field.default ?? ''
    }
  }
}

async function saveConfig() {
  saving.value = true
  testResults.value = null
  try {
    await capConfigAPI.save(capId.value, { ...formValues })
    configData.value = { ...configData.value, is_configured: true }
    alert('配置已保存。')
  } catch (e) {
    alert(e.response?.data?.detail || '保存失败，请重试。')
  } finally {
    saving.value = false
  }
}

async function testConfig() {
  testing.value = true
  testResults.value = { status: 'warn', message: '正在检测中...', results: [] }
  try {
    const { data } = await capConfigAPI.test(capId.value, { ...formValues })
    testResults.value = data
  } catch (e) {
    testResults.value = {
      status: 'error',
      message: e.response?.data?.detail || '检测接口不可用',
      results: [],
    }
  } finally {
    testing.value = false
  }
}

onMounted(async () => {
  try {
    const [cfgRes, adpRes, csRes] = await Promise.allSettled([
      capConfigAPI.myConfig(capId.value),
      capConfigAPI.adapterOptions(capId.value),
      dashboardAPI.clientStatus(),
    ])

    if (cfgRes.status === 'rejected') {
      const status = cfgRes.reason?.response?.status
      loadError.value = (status === 403 || status === 404)
        ? '未订阅该能力或能力不存在，请先在市场订阅。'
        : (cfgRes.reason?.response?.data?.detail || '加载配置失败，请刷新重试。')
      return
    }

    configData.value = cfgRes.value.data

    if (adpRes.status === 'fulfilled') {
      adapterOptions.value = adpRes.value.data?.categories || {}
    }

    if (csRes.status === 'fulfilled') {
      const d = csRes.value.data
      clientStatus.value = d?.data || d || { online: false, devices: [] }
    }

    initFormValues(configData.value.values || {})
  } finally {
    loading.value = false
  }
})
</script>
