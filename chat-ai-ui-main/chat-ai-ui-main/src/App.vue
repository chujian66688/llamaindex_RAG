<script setup lang="ts">
</script>

<template>
  <div class="app">
    <RouterView v-slot="{ Component }">
      <Transition name="page" mode="out-in">
        <component :is="Component" />
      </Transition>
    </RouterView>
  </div>
</template>

<style>
/* 全局页面过渡动画 */
.page-enter-active {
  transition: opacity 0.3s ease-out, transform 0.3s ease-out;
}

.page-leave-active {
  transition: opacity 0.2s ease-in, transform 0.2s ease-in;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
