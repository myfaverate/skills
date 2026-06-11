---
name: rn-layered-feature
description: React Native 功能模块的分层架构——纯逻辑+reducer / Hook / 视图三层分离,副作用显式依赖注入,业务状态机为纯 reducer,且必须 TDD 测试先行。Use when adding a new feature module, creating screens, hooks, or any component that touches side effects (recording, network, storage, timers, permissions), or when asked to build a testable / layered RN feature. Enforces test-first (red-green-refactor) development.
metadata:
  version: '3.1.0'
---

# RN 功能模块分层架构

每个功能都让**业务状态机成为纯函数**,所有副作用走注入。这样既保持一致,又能让整个状态机脱离 React、脱离真机、**同步**单测。

> ⚠️ **强制 TDD:本架构的所有开发必须测试先行。** 写任何实现文件之前,先为该层写好详细测试用例并确认其失败(红),再写最少实现让它通过(绿),最后重构(保持绿)。**严禁先写实现再补测试。** 若环境中有 `tdd` 技能,配合它执行红-绿-重构循环;没有则手动遵循该循环。

> 参考实现见 [references/EXAMPLES.zh.md](references/EXAMPLES.zh.md):先是 `counter` 模块(分层的最小形态),再是 `audio` 录音模块(完整标准范例)——新增功能时逐文件对照落地。

## 核心思想:纯状态机 + 副作用留在边缘

功能的难点在于**状态转移**(idle → recording → recorded → playing,外加错误与权限)。把这整个决策放进 logic 层的一个**纯 reducer**。Hook 通过注入依赖做 IO,然后 **dispatch 一个事件**描述"发生了什么";由 reducer 独自决定下一个状态。**Hook 绝不命令式地调 `setStatus(...)`。**

为什么:reducer 是同步纯函数,所以每条转移(包括非法转移)都能脱离 React、脱离真机被穷举测试。Hook 因此收缩为"做 IO、dispatch 结果",只剩这一小块才真正需要较重的 `renderHook` 测试。

## 四个文件,各司其职

| 文件 | 角色 | 规则 |
|---|---|---|
| `xxxLogic.ts` | 纯逻辑 + reducer | 状态/事件类型、`initialState`、`xxxReducer(state, event)` 纯转移函数、纯守卫(`canXxx`)、计算、格式化。**无 React、无副作用、无 import 平台 API**。 |
| `useXxx.ts` | Hook | 管理 `useReducer`、ref、`useEffect`;通过注入依赖编排副作用;dispatch 事件;返回经 `useMemo` 的扁平 API 对象(状态 + `canXxx` 布尔 + 动作函数)。 |
| `XxxView.tsx` | 视图 | 纯展示,**只吃 props**。无业务逻辑、无 hook、无副作用。每个交互元素带 `testID` 与无障碍属性。 |
| `Xxx.tsx` / `XxxScreen.tsx` | 容器 | 极薄胶水层:调 `useXxx()`,把结果摊平传给 `XxxView`。 |

## 状态机:守卫 + reducer(都纯,都在 logic 层)

logic 层拥有**完整**状态机,分两部分:

1. **守卫**——纯谓词。两类,务必分开:
   - **UI 可用性守卫**——如 `canRequestStart(status)`:按钮该不该亮?故意忽略动作自己能解决的前置条件(没有麦克风权限时录音键也该亮,因为按下去正是触发权限申请)。
   - **完整前置条件守卫**——如 `canStartRecording(permission, status)`:动作到底能不能执行?Hook 在动作内部、权限解析之后重新校验它。
2. **reducer**——`xxxReducer(state, event): state`,纯转移函数。它是"下一个状态是什么"的唯一真相来源。**非法转移即 no-op**(原样返回 `state`)——例如非录音状态下收到 `tick` 事件什么都不变。这让非法状态在构造上不可达。

Hook 返回的每个 `canXxx` 布尔都必须来自守卫;Hook **绝不内联转移或条件**。真值表只存在于一个被测试覆盖的地方。

## 类型化领域错误

错误建模为类型化联合,而非裸字符串。每个错误带一个 `kind`,让 reducer 能正确反应(如录音 `device` 失败回退到 `idle`,`playback` 失败保持当前状态),也让 View 能分支/国际化:

```ts
export type AudioErrorKind = 'permission' | 'device' | 'playback';
export type AudioError = { kind: AudioErrorKind; message: string };
```

绝不要把原生库的裸 `message` 直接当作唯一错误通道丢给用户——在边界处包成类型化错误。

## 依赖注入(副作用边界)

凡是触碰原生/IO 的能力(录音、网络、存储、**权限、弹窗、跳系统设置**…),先定义接口,再提供真实 + 模拟两套实现:

- 接口:如 `audioRecorder.ts` 的 `Recorder` 类型
- 真实实现:对原生库的薄适配器(如 `createNitroSoundRecorder`)
- 模拟实现:如 `createSimulatedRecorder`(测试与无设备环境用)

**必须显式注入——Hook 不得静默回退到模拟实现。** 静默兜底意味着:一旦忘了在根部注入真实现,应用会拿着假实现"正常运行",生产环境无任何报错。副作用依赖在 options 里声明为必填;组合根(`App.tsx`)注入真实现,测试注入桩:

```ts
export type UseAudioOptions = {
  recorder: Recorder;                 // 必填——不许静默兜底
  permissions: MicrophonePermissions; // 必填——权限同样是副作用
  tickMs?: number;                    // 普通配置可以有默认值
};
```

权限、Alert 弹窗、跳转系统设置同样是副作用——一律抽接口、走注入。若 Hook 直接 import 它们,Hook 测试就被迫 `jest.mock`,违背 DI 初衷。每个接口只承载一种能力;不相关方法堆积时(如录音 + 上传)就拆分。

**接口文件不得 import 平台模块。** 接口 + 模拟实现放在一起(`audioRecorder.ts`、`audioPermissions.ts`);每个真实适配器单独成文件(`nitroSoundRecorder.ts`、`nativeMicrophonePermissions.ts`)。这样引用类型或测试桩永远不会拖进原生模块。

## 异步动作与 effect:稳定回调、杜绝重入、定时器派生自状态

副作用动作是 `async`,带来几个 Hook 必须处理的隐患:

- **重入 / 竞态。** 入口守卫与状态变更之间隔着一个 `await`;连点两次可能两次都通过守卫、两次触发 IO(如两次 `startRecording()`)。用一个 in-flight `ref` 守护会创建会话的动作,保证同时只跑一个。
- **闭包读到过期 state。** 直接读 `state` 会把 `status`/`permission` 塞进回调依赖,每次变化都重建回调、破坏被 memo 的子组件。把 state 镜像进 `ref`(`stateRef.current`)再读,让动作回调只依赖(稳定的)注入依赖。**镜像必须在 effect 里赋值**(`useEffect(() => { stateRef.current = state; })`)——渲染期写 ref 违反 Rules of React,会被 React Compiler 的 lint 标记。`useReducer` 的 `dispatch` 本身就稳定。
- **长生命周期副作用派生自状态。** interval、订阅等要在以对应状态为 key 的 `useEffect` 里启停(如时长 tick 只在 `status === 'recording'` 时运行),绝不在动作回调里命令式启动。这样**所有**离开该状态的路径——用户停止、设备失败、组件卸载——都会自动清理;命令式启动的 interval 会在你漏掉的那条退出路径上泄漏。

返回的 API 对象用 `useMemo` 包裹,给消费方一个稳定引用。

## 测试约定(测试先行)

每层都**先写测试再写实现**,测试放在根目录 `__tests__/`。各层测试各管一摊,**不要跨层重复覆盖**:

- `xxxLogic.test.ts` — 最厚也最廉价的测试文件(纯、同步、无 React):
  - 守卫:每个守卫的真/假分支与边界值。
  - **reducer:穷举。** 对每种事件类型,从每个相关源状态断言结果状态,**包括非法转移为 no-op**,以及错误事件设置正确的 `kind` 与回退状态。
- 适配器委托测试(如 `nitroSoundRecorder.test.ts`)——真实实现是薄适配器:mock 原生库,断言每个接口方法正确转发(参数、返回值、监听器订阅/退订)。**不**测原生行为。若适配器含映射逻辑——如权限实现把 `NEVER_ASK_AGAIN` 映射为 `blocked`——也要断言该映射(`nativeMicrophonePermissions.test.ts`)。
- `useXxx.test.ts` — 用 `@testing-library/react-native` 的 `renderHook`,注入模拟桩。只断言 Hook 在 reducer 之上**额外**做的事:IO 被调用且其结果被 dispatch、错误路径产生 `failed` 事件、**权限被拒/被禁路径**(request 被调用、IO 未被调用、`promptOpenSettings` 被触发)、**重入被拦截**(双调 → IO 只调一次)、定时器生效。定时器用 `jest.useFakeTimers()` + `act(() => jest.advanceTimersByTime(...))` 驱动;**不要**在这里重测 reducer 的真值表。**注入桩必须在 `renderHook` 回调之外创建**——每次渲染都新建依赖对象会让挂载 effect 的依赖每次都变、无限重跑(测试卡死)。
- `XxxView.test.tsx` — 用 props 渲染,按 `testID` 断言:文案、**`disabled` / 无障碍状态**、`onPress` 回调被调用。不含状态逻辑。
- `XxxScreen.test.tsx` — 集成:用模拟依赖驱动 Screen,只跑**完整用户路径**;分支细节已由下层覆盖。

## 落地清单(红-绿-重构)

新增功能 `foo` 时,**每一步都先写测试(红)→ 再写实现(绿)→ 重构**:

1. `__tests__/fooLogic.test.ts` → `src/foo/fooLogic.ts` — 状态/事件类型、`initialState`、守卫、**reducer**(穷举转移测试,含 no-op)。
2. (若有副作用)在 `src/foo/fooClient.ts` 定义接口 + 模拟实现;真实适配器单独成文件,由 mock 原生库的委托测试驱动(`__tests__/fooNativeClient.test.ts`)。
3. `__tests__/useFoo.test.ts` → `src/foo/useFoo.ts` — 通过必填 options 注入桩;断言 IO-后-dispatch、错误事件、权限路径、重入、定时器(假定时器)。
4. `__tests__/FooView.test.tsx` → `src/foo/FooView.tsx` — 纯展示,props 驱动,元素带 `testID` + 无障碍属性。
5. `__tests__/FooScreen.test.tsx` → `src/foo/Foo.tsx` — 容器同样测试先行:先写用模拟依赖跑**完整用户路径**的集成测试,再写让它通过的薄容器(分支细节已由下层覆盖)。
6. 真实现只在组合根(`App.tsx`)接线**一次**。

全程保持 `npm test` 绿;提交前确保新增测试确实先经历过失败再变绿。

## 无障碍(a11y)

每个交互元素都是 `Pressable`(或 RN 按钮),除 `testID` 外还带 `accessibilityRole="button"` 与 `accessibilityState={{ disabled }}`。这也正是禁用 `<Text onPress>` 的原因(见下)——它没有角色、没有 disabled 语义、没有按压反馈。

## 参考代码的已知局限

- 权限参考实现**仅支持 Android**;iOS 上返回的是占位值(`request` 不弹窗直接返回 `'granted'`)。真实 iOS 支持需要 [`react-native-permissions`](https://github.com/zoontek/react-native-permissions)(`PERMISSIONS.IOS.MICROPHONE`)。保留 `MicrophonePermissions` 接口,换实现即可。
- Hook 在组件卸载时不会停止进行中的录音:tick interval 会自行清理(它派生自状态),但 recorder 仍在录。若离开页面必须取消录音,加一个调用 `recorder.stopRecording()` 的卸载 effect。

## 反面教材(勿模仿)

永远不要用 `<Text onPress>` 当按钮——不支持 `disabled`、无无障碍角色、无按压反馈。用带 `accessibilityRole`/`accessibilityState` 的 `Pressable`(见两个参考模块里的 `ActionButton`)。
