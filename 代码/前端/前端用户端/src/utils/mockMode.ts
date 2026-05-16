/** 本地真实联调：Mock 与全栈预览已关闭，始终走 Django API */
export function fullFrontendMockEnabled(): boolean {
  return false
}

export function mockAigcFeaturesEnabled(): boolean {
  return false
}
