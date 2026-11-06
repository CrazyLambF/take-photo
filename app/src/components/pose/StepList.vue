<script setup lang="ts">
/** 分步要点：纵向 stepper（§5.2） */
const props = defineProps<{ steps: string[] }>()
</script>

<template>
  <ol class="steps">
    <li v-for="(s, i) in props.steps" :key="i" class="step">
      <span class="no" aria-hidden="true">{{ i + 1 }}</span>
      <p>{{ s }}</p>
    </li>
  </ol>
</template>

<style scoped>
.steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--sp-3);
}

.step {
  display: grid;
  grid-template-columns: 28px 1fr;
  gap: var(--sp-3);
  align-items: start;
}

.no {
  width: 28px;
  height: 28px;
  border-radius: var(--r-full);
  background: var(--c-accent-soft);
  color: var(--c-accent-deep);
  font-weight: 700;
  font-size: var(--fs-14);
  display: grid;
  place-items: center;
}

.step p {
  margin: 3px 0 0;
  font-size: var(--fs-15);
  line-height: 1.6;
  color: var(--c-ink);
}
</style>
