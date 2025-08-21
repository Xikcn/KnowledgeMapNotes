<template>
  <svg aria-hidden="true" :class="svgClass" :style="`width:${size};height:${size}`">
    <use :xlink:href="symbolId" :fill="color"/>
  </svg>
</template>

<script setup lang="ts">
import {computed} from 'vue';

const props = defineProps({
  prefix: {
    type: String,
    default: 'icon'
  },
  iconClass: {
    type: String,
  },
  iconName: {
    type: String,
    required: false
  },
  color: {
    type: String
  },
  size: {
    type: String,
    default: '1em'
  }
});

const symbolId = computed(() => `#${props.prefix}-${props.iconName}`);
const svgClass = computed(() => {
  if (props.iconClass) {
    return `svg-icon ${props.iconClass}`
  }
  return 'svg-icon'
})
</script>

<style scoped>
.svg-icon {
  overflow: hidden;
  fill: currentColor;
}
</style>
