<template>
  <div class="section-header">
    <div class="section-header-left">
      <el-icon v-if="icon" class="section-icon"><component :is="icon" /></el-icon>
      <slot />
    </div>
    <div v-if="$slots.right" class="section-header-right">
      <slot name="right" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  icon: { type: [Object, Function], default: null },
})
</script>

<style scoped>
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-header-left {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 15px;
  line-height: 1;
}

.section-icon {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}
</style>
