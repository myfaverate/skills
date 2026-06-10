---
name: rn-layered-feature
description: 本项目新增 React Native 功能模块时使用的标准架构——纯逻辑/Hook/视图三层分离 + 依赖注入,且必须 TDD 测试先行。Use when adding a new feature module under src/, creating screens, hooks, or any component that touches side effects (recording, network, storage, timers), or when asked to follow the project's architecture/分层/约定. Enforces test-first (red-green-refactor) development.
metadata:
  version: '1.0.0'
---

# RN 功能模块分层架构

本项目每个功能模块(见 `src/audio`、`src/counter`)都遵循同一套分层。新增功能时按此模式落地,保持一致与可测试。

> ⚠️ **强制 TDD:本架构的所有开发必须测试先行。** 写任何实现文件之前,先为该层写好详细测试用例并确认其失败(红),再写最少实现让它通过(绿),最后重构(保持绿)。**严禁先写实现再补测试。** 配合 `tdd` 技能执行红-绿-重构循环。

> 完整可对照的逐文件代码范例见 [references/EXAMPLES.md](references/EXAMPLES.md)(audio 为标准实现,counter 为对照)。

## 四个文件,各司其职

| 文件 | 角色 | 规则 |
|---|---|---|
| `xxxLogic.ts` | 纯逻辑 | 只放纯函数:状态机判断(`canXxx`)、计算、格式化。**无 React、无副作用、无 import 平台 API**。 |
| `useXxx.ts` | Hook | 管理 `useState`/`useRef`/`useEffect`,编排副作用,调用 logic 与注入的依赖。返回扁平的 API 对象(状态 + `canXxx` 布尔 + 动作函数)。 |
| `XxxView.tsx` | 视图 | 纯展示,**只吃 props**。无业务逻辑、无 hook、无副作用。每个交互元素带 `testID`。 |
| `Xxx.tsx` / `XxxScreen.tsx` | 容器 | 极薄胶水层:调 `useXxx()`,把结果摊平传给 `XxxView`。 |

## 依赖注入(副作用边界)

凡是触碰原生/IO 的能力(录音、网络、存储…),先定义接口,再提供真实 + 模拟两套实现:

- 接口:`audioRecorder.ts` 的 `Recorder` 类型
- 真实实现:`nitroSoundRecorder.ts`(`createNitroSoundRecorder`)
- 模拟实现:`createSimulatedRecorder`(测试与无设备环境用)

Hook 通过 options 接收依赖,**默认用模拟实现**;`App.tsx` 在根部注入真实实现:

```ts
export function useAudio(options: UseAudioOptions = {}): AudioApi {
  const recorder = useMemo(
    () => options.recorder ?? createSimulatedRecorder(),
    [options.recorder],
  );
  // ...
}
```

好处:View / Hook / Logic 都能脱离真机单测,通过注入桩来断言行为。

## 状态机约定

- 在 logic 层定义状态联合类型(如 `RecordingStatus = 'idle' | 'recording' | ...`)。
- 每个动作的「是否可用」由 logic 的纯守卫函数推导(`canStopRecording(status)`),**不要在 View 里写条件**。
- Hook 把这些守卫算成布尔(`canStart`/`canStop`…)传给 View,按钮的 `disabled` 直接绑定。

## 测试约定(测试先行)

每层都**先写测试再写实现**,测试放在根目录 `__tests__/`:
- `xxxLogic.test.ts` — 纯函数,直接断言输入输出。覆盖每个状态机守卫的真/假分支与边界值。
- `useXxx.test.ts` — 用 `@testing-library/react-native` 的 `renderHook`,注入 `createSimulatedXxx` 桩,断言状态流转与 `canXxx` 派生值。
- `XxxView.test.tsx` — 按 `testID` 渲染 + 断言:文案、`disabled` 状态、`onPress` 回调被调用。
- 集成测用模拟依赖驱动 `XxxScreen`,跑通完整用户路径(见 `AudioScreen.test.tsx`)。

测试用例要**详细**:每个状态分支、每个 `canXxx` 守卫、每个错误路径(`recorder` 抛错→`error` 被设置)都要有断言,不是只测 happy path。

## 落地清单(红-绿-重构)

新增功能 `foo` 时,**每一步都先写测试(红)→ 再写实现(绿)→ 重构**:

1. `__tests__/fooLogic.test.ts` → `src/foo/fooLogic.ts` — 状态类型 + 纯函数守卫/格式化。
2. (若有副作用)定义 `Recorder` 式接口 + `__tests__` 里准备 `createSimulatedXxx` 桩 → `src/foo/fooClient.ts`;真实实现单独成文件(真实实现不强求单测,靠接口契约保证)。
3. `__tests__/useFoo.test.ts` → `src/foo/useFoo.ts` — 注入桩,断言状态流转与派生布尔。
4. `__tests__/FooView.test.tsx` → `src/foo/FooView.tsx` — 纯展示,props 驱动,元素带 `testID`。
5. `src/foo/Foo.tsx` — 薄容器(逻辑已被各层测试覆盖,容器本身可只做集成测)。
6. `__tests__/FooScreen.test.tsx` — 用模拟依赖跑通端到端用户路径。

全程保持 `npm test` 绿;提交前确保新增测试确实先经历过失败再变绿。

## 反面教材(勿模仿)

`src/counter` 是早期模板示例,其 `CounterView` 用 `<Text onPress>` 当按钮——**应改用 `Pressable`**(见 `AudioView` 的 `ActionButton`)。新代码以 `audio` 模块为准。
