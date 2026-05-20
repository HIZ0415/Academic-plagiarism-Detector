import { ref, watch } from 'vue'

export type DetectionMode = 'fast' | 'precise'

const STORAGE_KEY = 'detection_mode'

export function useDetectionMode() {
  const mode = ref<DetectionMode>(
    (localStorage.getItem(STORAGE_KEY) as DetectionMode) || 'fast',
  )

  watch(mode, (v) => {
    localStorage.setItem(STORAGE_KEY, v)
  })

  function setMode(v: DetectionMode) {
    mode.value = v
    localStorage.setItem(STORAGE_KEY, v)
  }

  function modePayload() {
    return mode.value
  }

  function imageSubmitMode() {
    return mode.value === 'precise' ? 3 : 1
  }

  return { mode, setMode, modePayload, imageSubmitMode }
}
