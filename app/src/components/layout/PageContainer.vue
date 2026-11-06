<script setup lang="ts">
/** 页面内容容器：断点令牌控制三档宽度（§3.3），视图只管内容 */
</script>

<template>
  <section class="page-container">
    <slot />
  </section>
</template>

<style scoped>
.page-container {
  width: 100%;
  max-width: var(--container-tablet);
  margin-inline: auto;
  padding: var(--sp-5) var(--sp-4) var(--sp-12);
}

@media (min-width: 1200px) {
  .page-container {
    max-width: var(--container-max);
    padding: var(--sp-8) var(--sp-6) var(--sp-16);
  }
}
</style>
