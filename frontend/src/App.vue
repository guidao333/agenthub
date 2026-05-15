<template>
  <div class="min-h-screen flex flex-col">
    <Navbar v-if="showNav" />
    <main class="flex-1">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Navbar from './components/Navbar.vue'

const route = useRoute()
const showNav = computed(() => !['login', 'register'].includes(route.name))
</script>
