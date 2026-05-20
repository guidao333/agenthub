<template>
  <div class="vision-panel">
    <h1 class="panel-title">👁️ AI视觉管理</h1>

    <!-- Tab 导航 -->
    <div class="tabs">
      <button v-for="tab in tabs" :key="tab.key"
        :class="['tab-btn', { active: activeTab === tab.key }]"
        @click="activeTab = tab.key">
        {{ tab.icon }} {{ tab.label }}
      </button>
    </div>

    <!-- ============== TAB1: 设备 ============== -->
    <div v-if="activeTab === 'devices'" class="tab-content">
      <div class="section-header">
        <h2>📡 已注册设备</h2>
        <button class="btn btn-primary" @click="showAddDevice = true">+ 注册新设备</button>
      </div>
      <table class="data-table" v-if="devices.length">
        <thead>
          <tr><th>名称</th><th>类型</th><th>系统</th><th>API Key</th><th>状态</th><th>摄像头数</th><th>最后心跳</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="d in devices" :key="d.id">
            <td>{{ d.device_name }}</td>
            <td>{{ deviceTypeLabel(d.device_type) }}</td>
            <td>{{ d.os_info || '-' }}</td>
            <td><code class="apikey">{{ maskKey(d.api_key) }}</code></td>
            <td><span :class="'status-badge ' + d.status">{{ statusLabel(d.status) }}</span></td>
            <td>{{ d.cameras?.length || 0 }}</td>
            <td>{{ d.last_heartbeat || '-' }}</td>
            <td>
              <button class="btn btn-sm btn-danger" @click="deleteDevice(d.id)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">
        <p>暂无注册设备。购买AI视觉能力后，在客户电脑上安装 AgentHub Edge 即可自动注册。</p>
      </div>
    </div>

    <!-- ============== TAB2: 摄像头 ============== -->
    <div v-if="activeTab === 'cameras'" class="tab-content">
      <div class="section-header">
        <h2>📷 摄像头列表</h2>
        <button class="btn btn-primary" @click="showAddCamera = true">+ 添加摄像头</button>
      </div>
      <table class="data-table" v-if="cameras.length">
        <thead>
          <tr><th>IP</th><th>品牌</th><th>位置</th><th>RTSP</th><th>状态</th><th>所属设备</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="c in cameras" :key="c.id">
            <td>{{ c.ip }}</td>
            <td>{{ c.camera_type }}</td>
            <td>{{ c.location || '-' }}</td>
            <td><code class="apikey">{{ c.rtsp_url ? c.rtsp_url.substring(0, 30)+'...' : '-' }}</code></td>
            <td><span :class="'status-badge ' + c.status">{{ statusLabel(c.status) }}</span></td>
            <td>{{ c.device_id?.substring(0, 8) || '-' }}</td>
            <td>
              <button class="btn btn-sm btn-danger" @click="deleteCamera(c.id)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">
        <p>暂无摄像头。添加设备后，设备会自动发现局域网内的ONVIF摄像头。</p>
      </div>
    </div>

    <!-- ============== TAB3: 事件 ============== -->
    <div v-if="activeTab === 'events'" class="tab-content">
      <div class="section-header">
        <h2>🚨 告警事件</h2>
        <div class="filters">
          <select v-model="eventFilter.type">
            <option value="">全部类型</option>
            <option value="trash_detected">垃圾检测</option>
            <option value="object_disappeared">物体消失</option>
            <option value="throw_detected">高空抛物</option>
          </select>
          <select v-model="eventFilter.severity">
            <option value="">全部级别</option>
            <option value="info">普通</option>
            <option value="warning">警告</option>
            <option value="critical">严重</option>
          </select>
          <button class="btn btn-primary" @click="loadEvents">查询</button>
        </div>
      </div>
      <table class="data-table" v-if="events.length">
        <thead>
          <tr><th>时间</th><th>类型</th><th>级别</th><th>描述</th><th>置信度</th><th>截图</th><th>状态</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="e in events" :key="e.id">
            <td class="time">{{ e.created_at }}</td>
            <td>{{ eventTypeLabel(e.event_type) }}</td>
            <td><span :class="'severity ' + e.severity">{{ severityLabel(e.severity) }}</span></td>
            <td class="desc">{{ e.description || '-' }}</td>
            <td>{{ (e.confidence * 100).toFixed(0) + '%' }}</td>
            <td>
              <img v-if="e.snapshot_path" :src="'/api/snapshots/' + e.snapshot_path.split('/').pop()" class="thumb"
                   @click="previewImg = '/api/snapshots/' + e.snapshot_path.split('/').pop()" />
              <span v-else>-</span>
            </td>
            <td>{{ e.acknowledged ? '已确认' : '未确认' }}</td>
            <td>
              <button v-if="!e.acknowledged" class="btn btn-sm btn-success" @click="acknowledgeEvent(e.id)">确认</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">
        <p>暂无告警事件。设备上线后，检测到异常会自动上报。</p>
      </div>
    </div>

    <!-- ============== TAB4: 通知渠道 ============== -->
    <div v-if="activeTab === 'notify'" class="tab-content">
      <div class="section-header">
        <h2>🔔 通知渠道配置</h2>
        <button class="btn btn-primary" @click="showAddChannel = true">+ 添加渠道</button>
      </div>
      <table class="data-table" v-if="channels.length">
        <thead>
          <tr><th>类型</th><th>配置摘要</th><th>事件过滤</th><th>状态</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="ch in channels" :key="ch.id">
            <td>{{ channelTypeLabel(ch.channel_type) }}</td>
            <td class="desc"><code class="apikey">{{ channelConfigHint(ch) }}</code></td>
            <td>{{ ch.event_types?.length ? ch.event_types.join(', ') : '全部事件' }}</td>
            <td><span :class="'status-badge ' + (ch.enabled ? 'online' : 'offline')">{{ ch.enabled ? '已启用' : '已禁用' }}</span></td>
            <td>
              <button class="btn btn-sm btn-info" @click="testChannel(ch.id)">测试</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">
        <p>暂无通知渠道。添加后可在检测到异常时自动推送通知。</p>
      </div>
    </div>

    <!-- ============== TAB5: 统计 ============== -->
    <div v-if="activeTab === 'stats'" class="tab-content">
      <h2>📊 数据概览</h2>
      <div class="stats-cards" v-if="stats">
        <div class="stat-card"><span class="num">{{ stats.total_events }}</span><span class="label">总事件数</span></div>
        <div class="stat-card warning"><span class="num">{{ stats.today_events }}</span><span class="label">今日新增</span></div>
        <div class="stat-card alert"><span class="num">{{ stats.unacknowledged }}</span><span class="label">未确认</span></div>
        <div class="stat-card success"><span class="num">{{ devices.length }}</span><span class="label">设备数</span></div>
        <div class="stat-card info"><span class="num">{{ cameras.length }}</span><span class="label">摄像头</span></div>
      </div>
      <div class="stats-detail" v-if="stats">
        <div class="stat-section">
          <h3>事件类型分布</h3>
          <div class="bar-chart">
            <div v-for="item in stats.by_type" :key="item.event_type" class="bar-row">
              <span class="bar-label">{{ eventTypeLabel(item.event_type) }}</span>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: (item.cnt / maxType * 100) + '%' }"></div>
              </div>
              <span class="bar-count">{{ item.cnt }}</span>
            </div>
          </div>
        </div>
        <div class="stat-section">
          <h3>严重级别分布</h3>
          <div class="bar-chart">
            <div v-for="item in stats.by_severity" :key="item.severity" class="bar-row">
              <span class="bar-label">{{ severityLabel(item.severity) }}</span>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: (item.cnt / maxSev * 100) + '%', background: severityColor(item.severity) }"></div>
              </div>
              <span class="bar-count">{{ item.cnt }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ============== 弹窗: 添加设备 ============== -->
    <div v-if="showAddDevice" class="modal-overlay" @click.self="showAddDevice = false">
      <div class="modal">
        <h3>📡 注册新设备</h3>
        <div class="form-group"><label>设备名称</label><input v-model="newDevice.name" placeholder="如：XX小区监控室" /></div>
        <div class="form-group"><label>设备类型</label>
          <select v-model="newDevice.type">
            <option value="edge_box">边缘盒子</option>
            <option value="pc">电脑</option>
            <option value="raspberry_pi">树莓派</option>
          </select>
        </div>
        <div class="form-group"><label>操作系统</label><input v-model="newDevice.os" placeholder="如：Windows 10" /></div>
        <div class="form-group"><label>主机名</label><input v-model="newDevice.hostname" placeholder="可选" /></div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showAddDevice = false">取消</button>
          <button class="btn btn-primary" @click="registerDevice" :disabled="!newDevice.name">注册</button>
        </div>
      </div>
    </div>

    <!-- ============== 弹窗: 添加摄像头 ============== -->
    <div v-if="showAddCamera" class="modal-overlay" @click.self="showAddCamera = false">
      <div class="modal">
        <h3>📷 添加摄像头</h3>
        <div class="form-group">
          <label>所属设备</label>
          <select v-model="newCamera.device_id">
            <option v-for="d in devices" :key="d.id" :value="d.id">{{ d.device_name }}</option>
          </select>
        </div>
        <div class="form-group"><label>摄像头IP</label><input v-model="newCamera.ip" placeholder="192.168.1.100" /></div>
        <div class="form-group"><label>端口</label><input v-model="newCamera.port" placeholder="554" type="number" /></div>
        <div class="form-group"><label>用户名</label><input v-model="newCamera.username" placeholder="admin" /></div>
        <div class="form-group"><label>密码</label><input v-model="newCamera.password" type="password" /></div>
        <div class="form-group"><label>位置说明</label><input v-model="newCamera.location" placeholder="如：小区北门口" /></div>
        <div class="form-group"><label>品牌</label>
          <select v-model="newCamera.camera_type">
            <option value="auto">自动检测</option>
            <option value="hikvision">海康威视</option>
            <option value="dahua">大华</option>
            <option value="tp_link">TP-Link</option>
          </select>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showAddCamera = false">取消</button>
          <button class="btn btn-primary" @click="addCamera" :disabled="!newCamera.ip">添加</button>
        </div>
      </div>
    </div>

    <!-- ============== 弹窗: 添加通知渠道 ============== -->
    <div v-if="showAddChannel" class="modal-overlay" @click.self="showAddChannel = false">
      <div class="modal">
        <h3>🔔 添加通知渠道</h3>
        <div class="form-group"><label>渠道类型</label>
          <select v-model="newChannel.type">
            <option value="wechat_webhook">企业微信机器人</option>
            <option value="dingtalk_webhook">钉钉机器人</option>
            <option value="feishu_webhook">飞书机器人</option>
            <option value="email">邮箱</option>
          </select>
        </div>
        <div v-if="newChannel.type === 'email'" class="form-group">
          <label>接收邮箱</label><input v-model="newChannel.config.to" placeholder="xxx@qq.com" />
        </div>
        <div v-else class="form-group">
          <label>Webhook URL</label><input v-model="newChannel.config.webhook_url"
            placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..." />
        </div>
        <div class="form-group">
          <label>事件过滤（留空=全部）</label>
          <div class="checkbox-group">
            <label><input type="checkbox" value="trash_detected" v-model="newChannel.event_types" /> 垃圾检测</label>
            <label><input type="checkbox" value="object_disappeared" v-model="newChannel.event_types" /> 物体消失</label>
            <label><input type="checkbox" value="throw_detected" v-model="newChannel.event_types" /> 高空抛物</label>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showAddChannel = false">取消</button>
          <button class="btn btn-primary" @click="addChannel" :disabled="!channelValid">添加</button>
        </div>
      </div>
    </div>

    <!-- 截图预览 -->
    <div v-if="previewImg" class="modal-overlay preview" @click.self="previewImg = ''">
      <img :src="previewImg" class="preview-img" />
    </div>
  </div>
</template>

<script>
import { visionAPI } from '../api/index.js'

export default {
  name: 'VisionPanel',
  data() {
    return {
      activeTab: 'devices',
      tabs: [
        { key: 'devices', label: '设备', icon: '📡' },
        { key: 'cameras', label: '摄像头', icon: '📷' },
        { key: 'events', label: '告警事件', icon: '🚨' },
        { key: 'notify', label: '通知渠道', icon: '🔔' },
        { key: 'stats', label: '统计', icon: '📊' },
      ],
      devices: [], cameras: [], events: [], channels: [], stats: null,
      eventFilter: { type: '', severity: '' },
      previewImg: '',
      showAddDevice: false, showAddCamera: false, showAddChannel: false,
      newDevice: { name: '', type: 'pc', os: '', hostname: '' },
      newCamera: { device_id: '', ip: '', port: 554, username: 'admin', password: '', location: '', camera_type: 'auto' },
      newChannel: { type: 'wechat_webhook', config: { webhook_url: '' }, event_types: [] },
    }
  },
  computed: {
    channelValid() {
      const c = this.newChannel
      if (c.type === 'email') return !!c.config.to
      return !!c.config.webhook_url
    },
    maxType() { return Math.max(...this.stats?.by_type?.map(i => i.cnt) || [1], 1) },
    maxSev() { return Math.max(...this.stats?.by_severity?.map(i => i.cnt) || [1], 1) },
  },
  mounted() { this.loadAll() },
  methods: {
    async loadAll() {
      try {
        const [dr, cr, er, ch, st] = await Promise.all([
          visionAPI.devices().catch(() => ({ data: { devices: [] } })),
          visionAPI.cameras().catch(() => ({ data: { cameras: [] } })),
          visionAPI.events({}).catch(() => ({ data: { events: [] } })),
          visionAPI.channels().catch(() => ({ data: { channels: [] } })),
          visionAPI.stats().catch(() => ({ data: {} })),
        ])
        this.devices = dr.data.devices || []
        this.cameras = cr.data.cameras || []
        this.events = er.data.events || []
        this.channels = ch.data.channels || []
        this.stats = st.data
      } catch (e) {
        console.error('Failed to load vision data:', e)
      }
    },
    async loadEvents() {
      const res = await visionAPI.events(this.eventFilter).catch(() => ({ data: { events: [] } }))
      this.events = res.data.events || []
    },
    async registerDevice() {
      await visionAPI.registerDevice({
        device_name: this.newDevice.name,
        device_type: this.newDevice.type,
        os_info: this.newDevice.os,
        hostname: this.newDevice.hostname,
      })
      this.showAddDevice = false
      this.newDevice = { name: '', type: 'pc', os: '', hostname: '' }
      this.loadAll()
    },
    async addCamera() {
      await visionAPI.addCamera(this.newCamera)
      this.showAddCamera = false
      this.newCamera = { device_id: '', ip: '', port: 554, username: 'admin', password: '', location: '', camera_type: 'auto' }
      this.loadAll()
    },
    async addChannel() {
      await visionAPI.addChannel({
        channel_type: this.newChannel.type,
        config: this.newChannel.config,
        event_types: this.newChannel.event_types,
      })
      this.showAddChannel = false
      this.loadAll()
    },
    async testChannel(id) {
      await visionAPI.testChannel(id)
      alert('测试消息已发送，请检查对应渠道')
    },
    async acknowledgeEvent(id) {
      await visionAPI.acknowledgeEvent(id)
      this.loadEvents()
    },
    async deleteDevice(id) {
      if (!confirm('确认删除该设备及相关数据？')) return
      await visionAPI.deleteDevice(id)
      this.loadAll()
    },
    async deleteCamera(id) {
      if (!confirm('确认删除该摄像头？')) return
      // TODO: add delete camera API
      this.loadAll()
    },
    deviceTypeLabel(t) {
      return { edge_box: '边缘盒子', pc: '电脑', raspberry_pi: '树莓派' }[t] || t
    },
    statusLabel(s) {
      return { online: '在线', offline: '离线', running: '运行中', idle: '空闲', error: '故障' }[s] || s
    },
    eventTypeLabel(t) {
      return { trash_detected: '🧹 垃圾检测', object_disappeared: '🔍 物体消失', throw_detected: '🚨 高空抛物' }[t] || t
    },
    severityLabel(s) {
      return { info: '普通', warning: '警告', critical: '严重' }[s] || s
    },
    severityColor(s) {
      return { info: '#3498db', warning: '#f39c12', critical: '#e74c3c' }[s] || '#95a5a6'
    },
    channelTypeLabel(t) {
      return { email: '邮箱', wechat_webhook: '企业微信', dingtalk_webhook: '钉钉', feishu_webhook: '飞书', sms: '短信' }[t] || t
    },
    channelConfigHint(ch) {
      const cfg = typeof ch.config === 'string' ? JSON.parse(ch.config || '{}') : (ch.config || {})
      if (ch.channel_type === 'email') return cfg.to || '-'
      return (cfg.webhook_url || '').substring(0, 40) + '...'
    },
    maskKey(key) {
      if (!key) return '未分配'
      if (key.length <= 12) return key
      return key.substring(0, 8) + '****' + key.substring(key.length - 4)
    },
  }
}
</script>

<style scoped>
.vision-panel {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.panel-title {
  font-size: 24px;
  margin-bottom: 20px;
  color: #2c3e50;
}

/* Tabs */
.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 24px;
  border-bottom: 2px solid #e9ecef;
}

.tab-btn {
  padding: 10px 20px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 14px;
  color: #6c757d;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.2s;
}

.tab-btn:hover { color: #2c3e50; }
.tab-btn.active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
  font-weight: 600;
}

/* Section Header */
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-header h2 {
  font-size: 18px;
  color: #2c3e50;
  margin: 0;
}

/* Data Table */
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.data-table th {
  background: #f8f9fa;
  padding: 10px 12px;
  text-align: left;
  font-weight: 600;
  color: #495057;
  border-bottom: 2px solid #dee2e6;
  white-space: nowrap;
}

.data-table td {
  padding: 8px 12px;
  border-bottom: 1px solid #e9ecef;
}

.data-table tr:hover { background: #f8f9fa; }

.data-table .desc {
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.data-table .time { white-space: nowrap; font-size: 12px; color: #6c757d; }

/* Badges */
.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.online, .status-badge.running { background: #d4edda; color: #155724; }
.status-badge.offline, .status-badge.idle { background: #e9ecef; color: #6c757d; }
.status-badge.error { background: #f8d7da; color: #721c24; }
.status-badge.disabled { background: #f8d7da; color: #721c24; }

.severity {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
}

.severity.info { background: #d1ecf1; color: #0c5460; }
.severity.warning { background: #fff3cd; color: #856404; }
.severity.critical { background: #f8d7da; color: #721c24; }

/* Buttons */
.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: opacity 0.2s;
}

.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: #3b82f6; color: #fff; }
.btn-primary:hover:not(:disabled) { background: #2563eb; }
.btn-success { background: #10b981; color: #fff; }
.btn-success:hover:not(:disabled) { background: #059669; }
.btn-danger { background: #ef4444; color: #fff; }
.btn-danger:hover:not(:disabled) { background: #dc2626; }
.btn-info { background: #06b6d4; color: #fff; }
.btn-info:hover:not(:disabled) { background: #0891b2; }
.btn-secondary { background: #e9ecef; color: #495057; }
.btn-secondary:hover:not(:disabled) { background: #dee2e6; }
.btn-sm { padding: 4px 10px; font-size: 12px; }

/* Filters */
.filters {
  display: flex;
  gap: 8px;
}

.filters select {
  padding: 6px 12px;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  font-size: 13px;
}

/* API Key */
.apikey {
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 11px;
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 3px;
  color: #495057;
}

/* Stats Cards */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border: 1px solid #e9ecef;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
}

.stat-card .num { display: block; font-size: 32px; font-weight: 700; color: #2c3e50; }
.stat-card .label { display: block; font-size: 13px; color: #6c757d; margin-top: 4px; }
.stat-card.warning .num { color: #f39c12; }
.stat-card.alert .num { color: #e74c3c; }
.stat-card.success .num { color: #10b981; }
.stat-card.info .num { color: #3b82f6; }

/* Bar Chart */
.stat-section { margin-bottom: 24px; }
.stat-section h3 { font-size: 15px; margin-bottom: 12px; color: #2c3e50; }
.bar-chart { max-width: 500px; }
.bar-row { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.bar-label { width: 100px; font-size: 13px; color: #495057; text-align: right; }
.bar-track { flex: 1; height: 20px; background: #f0f0f0; border-radius: 10px; overflow: hidden; }
.bar-fill { height: 100%; background: #3b82f6; border-radius: 10px; transition: width 0.3s; min-width: 4px; }
.bar-count { width: 40px; font-size: 13px; color: #6c757d; }

/* Thumbnail */
.thumb {
  width: 60px;
  height: 40px;
  object-fit: cover;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid #dee2e6;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  width: 480px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
}

.modal h3 { margin: 0 0 16px; font-size: 18px; }

.form-group {
  margin-bottom: 12px;
}

.form-group label {
  display: block;
  font-size: 13px;
  color: #495057;
  margin-bottom: 4px;
  font-weight: 500;
}

.form-group input, .form-group select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-group input:focus, .form-group select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
}

.checkbox-group { display: flex; gap: 16px; flex-wrap: wrap; }
.checkbox-group label { display: flex; align-items: center; gap: 4px; font-weight: 400; cursor: pointer; }
.checkbox-group input { width: auto; }

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}

/* Preview */
.modal-overlay.preview img {
  max-width: 90vw;
  max-height: 90vh;
  border-radius: 8px;
}

/* Empty */
.empty {
  text-align: center;
  padding: 60px 20px;
  color: #6c757d;
  background: #f8f9fa;
  border-radius: 12px;
  border: 2px dashed #dee2e6;
}

.empty p { margin: 0; font-size: 14px; }
</style>
