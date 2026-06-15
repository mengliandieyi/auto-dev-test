const COMMAND_LABELS: Record<string, string> = {
  validate: '检查 PRD',
  parse: '提取用例',
  generate: '生成脚本',
  'generate-pipeline': '一键生成',
  test: '运行测试',
  'run-full': '生成并运行',
  report: '验收报告',
  dev: '生成业务代码',
  'heal-loop': '自动修复循环',
};

const DEV_LAYER_LABELS: Record<string, string> = {
  frontend: '生成前端代码',
  backend: '生成后端代码',
  all: '前后端都生成',
};

export function jobCommandLabel(job: {
  command: string;
  args?: Record<string, unknown>;
}): string {
  if (job.command === 'dev') {
    const layer = job.args?.layer as string | undefined;
    if (layer && DEV_LAYER_LABELS[layer]) return DEV_LAYER_LABELS[layer];
  }
  return COMMAND_LABELS[job.command] || job.command;
}

export function dashboardCommandLabel(command: string): string {
  const map: Record<string, string> = {
    validate: '校验 PRD',
    parse: '解析',
    generate: '生成测试',
    'generate-pipeline': '生成链路',
    test: '执行测试',
    'run-full': '一键全流程',
    report: '生成报告',
    dev: '业务代码',
    'heal-loop': '自动修复',
  };
  return map[command] ?? command;
}
