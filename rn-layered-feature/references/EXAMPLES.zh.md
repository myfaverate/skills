---
name: rn-layered-feature 参考代码
description: rn-layered-feature 架构的完整代码范例,以 src/audio(纯 reducer 状态机 + 注入副作用)为标准实现,src/counter 为对照。
---

# 参考代码

两个完整范例,从简到繁:

- **`counter`**——分层的最小形态:纯逻辑 + 守卫、Hook、视图、容器,无副作用、无 reducer(简单状态用不上)。先看它了解骨架。
- **`audio`**——**标准范例**:真正的状态机(纯 reducer)、注入的副作用(recorder + 权限)、定时器、类型化错误。新增功能模块逐文件对照它。

> 注:此为中文文案版本,英文版见 [EXAMPLES.md](EXAMPLES.md)。

> 各小节按"实现文件在前、测试在后"(`1` → `1t`)排版,仅为方便阅读——**开发顺序相反**:先写测试、看它失败,再写实现(见 SKILL.zh.md 的落地清单)。

## 最小范例:counter 模块

无副作用,所以无需依赖注入;状态只是一个数字,所以 `useState` + 纯函数足矣(转移变复杂时再升级到 reducer——见 `audio`)。它仍遵守其余每条规则:带守卫的纯逻辑、用 `Pressable` 且带 `testID` + 无障碍的纯视图、薄容器,以及每层一个测试。

### 1. 纯逻辑 `src/counter/counterLogic.ts`

```ts
export const INITIAL_COUNT = 0;
export const MIN_COUNT = 0;

export function increment(count: number): number {
  return count + 1;
}

export function decrement(count: number): number {
  return Math.max(MIN_COUNT, count - 1);
}

export function reset(): number {
  return INITIAL_COUNT;
}

// 守卫:减一动作是否可用?(count 在 MIN_COUNT 处被钳制)
export function canDecrement(count: number): boolean {
  return count > MIN_COUNT;
}

export function isEven(count: number): boolean {
  return count % 2 === 0;
}
```

### 1t. 逻辑测试 `__tests__/counterLogic.test.ts`

```ts
import {
  INITIAL_COUNT,
  MIN_COUNT,
  canDecrement,
  decrement,
  increment,
  isEven,
  reset,
} from '../src/counter/counterLogic';

describe('counterLogic (纯)', () => {
  test('increment 加一', () => {
    expect(increment(0)).toBe(1);
    expect(increment(41)).toBe(42);
  });
  test('decrement 减一但钳制在 MIN_COUNT', () => {
    expect(decrement(2)).toBe(1);
    expect(decrement(MIN_COUNT)).toBe(MIN_COUNT);
  });
  test('reset 返回 INITIAL_COUNT', () => {
    expect(reset()).toBe(INITIAL_COUNT);
  });
  test('canDecrement 在下界为 false', () => {
    expect(canDecrement(1)).toBe(true);
    expect(canDecrement(MIN_COUNT)).toBe(false);
  });
  test.each([[0, true], [1, false], [2, true]])('isEven(%i) === %s', (n, e) => {
    expect(isEven(n as number)).toBe(e);
  });
});
```

### 2. Hook `src/counter/useCounter.ts`

```ts
import { useCallback, useMemo, useState } from 'react';
import { INITIAL_COUNT, canDecrement, decrement, increment, reset } from './counterLogic';

export type CounterApi = {
  count: number;
  canDecrement: boolean;
  increment: () => void;
  decrement: () => void;
  reset: () => void;
};

export function useCounter(initial: number = INITIAL_COUNT): CounterApi {
  const [count, setCount] = useState(initial);

  const inc = useCallback(() => setCount(increment), []);
  const dec = useCallback(() => setCount(decrement), []);
  const rst = useCallback(() => setCount(reset()), []);

  return useMemo(
    () => ({ count, canDecrement: canDecrement(count), increment: inc, decrement: dec, reset: rst }),
    [count, inc, dec, rst],
  );
}
```

### 2t. Hook 测试 `__tests__/useCounter.test.ts`

```ts
import { act, renderHook } from '@testing-library/react-native';
import { useCounter } from '../src/counter/useCounter';

test('计数累加、在零处钳制、暴露 canDecrement、重置', () => {
  const { result } = renderHook(() => useCounter());
  expect(result.current.count).toBe(0);
  expect(result.current.canDecrement).toBe(false);

  act(() => result.current.increment());
  expect(result.current.count).toBe(1);
  expect(result.current.canDecrement).toBe(true);

  act(() => result.current.decrement());
  expect(result.current.count).toBe(0);

  act(() => result.current.decrement()); // 钳制,不抛错
  expect(result.current.count).toBe(0);

  act(() => result.current.reset());
  expect(result.current.count).toBe(0);
});
```

### 3. 视图 `src/counter/CounterView.tsx`

```tsx
import { Pressable, StyleSheet, Text, View } from 'react-native';

export type CounterViewProps = {
  count: number;
  canDecrement: boolean;
  onIncrement: () => void;
  onDecrement: () => void;
  onReset: () => void;
};

export function CounterView({
  count,
  canDecrement,
  onIncrement,
  onDecrement,
  onReset,
}: CounterViewProps) {
  return (
    <View style={styles.container}>
      <Text testID="count" style={styles.count}>Count: {count}</Text>
      <View style={styles.row}>
        <ActionButton testID="dec" label="-" disabled={!canDecrement} onPress={onDecrement} />
        <ActionButton testID="inc" label="+" disabled={false} onPress={onIncrement} />
      </View>
      <ActionButton testID="reset" label="reset" disabled={false} onPress={onReset} />
    </View>
  );
}

type ActionButtonProps = {
  testID: string;
  label: string;
  disabled: boolean;
  onPress: () => void;
};

function ActionButton({ testID, label, disabled, onPress }: ActionButtonProps) {
  return (
    <Pressable
      testID={testID}
      disabled={disabled}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ disabled }}
      style={[styles.btn, disabled && styles.btnDisabled]}
    >
      <Text style={styles.btnLabel}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 16 },
  count: { fontSize: 24 },
  row: { flexDirection: 'row', gap: 24 },
  btn: { minWidth: 48, paddingHorizontal: 16, paddingVertical: 10, borderRadius: 8, borderCurve: 'continuous', backgroundColor: '#222', alignItems: 'center' },
  btnDisabled: { backgroundColor: '#bbb' },
  btnLabel: { color: 'white', fontSize: 20, fontWeight: '600' },
});
```

### 3t. 视图测试 `__tests__/CounterView.test.tsx`

```tsx
import { fireEvent, render, screen } from '@testing-library/react-native';
import { CounterView } from '../src/counter/CounterView';

const noop = () => {};

test('渲染计数;canDecrement 为 false 时减号禁用', () => {
  render(<CounterView count={0} canDecrement={false} onIncrement={noop} onDecrement={noop} onReset={noop} />);
  expect(screen.getByTestId('count')).toHaveTextContent('Count: 0');
  expect(screen.getByTestId('dec')).toBeDisabled();
  expect(screen.getByTestId('inc')).toBeEnabled();
});

test('触发回调;禁用的减号不触发', () => {
  const onIncrement = jest.fn();
  const onDecrement = jest.fn();
  const onReset = jest.fn();

  const { rerender } = render(
    <CounterView count={0} canDecrement={false} onIncrement={onIncrement} onDecrement={onDecrement} onReset={onReset} />,
  );

  fireEvent.press(screen.getByTestId('inc'));
  fireEvent.press(screen.getByTestId('reset'));
  fireEvent.press(screen.getByTestId('dec')); // 禁用 -> 忽略
  expect(onIncrement).toHaveBeenCalledTimes(1);
  expect(onReset).toHaveBeenCalledTimes(1);
  expect(onDecrement).not.toHaveBeenCalled();

  rerender(<CounterView count={1} canDecrement={true} onIncrement={onIncrement} onDecrement={onDecrement} onReset={onReset} />);
  fireEvent.press(screen.getByTestId('dec'));
  expect(onDecrement).toHaveBeenCalledTimes(1);
});
```

### 4. 容器 `src/counter/Counter.tsx`

```tsx
import { CounterView } from './CounterView';
import { useCounter } from './useCounter';

export function Counter() {
  const counter = useCounter();
  return (
    <CounterView
      count={counter.count}
      canDecrement={counter.canDecrement}
      onIncrement={counter.increment}
      onDecrement={counter.decrement}
      onReset={counter.reset}
    />
  );
}
```

### 4t. 容器集成测试 `__tests__/Counter.test.tsx`

```tsx
import { fireEvent, render, screen } from '@testing-library/react-native';
import { Counter } from '../src/counter/Counter';

test('用户累加并重置', () => {
  render(<Counter />);
  expect(screen.getByTestId('count')).toHaveTextContent('Count: 0');
  fireEvent.press(screen.getByTestId('inc'));
  fireEvent.press(screen.getByTestId('inc'));
  expect(screen.getByTestId('count')).toHaveTextContent('Count: 2');
  fireEvent.press(screen.getByTestId('reset'));
  expect(screen.getByTestId('count')).toHaveTextContent('Count: 0');
});

test('计数永不为负(零处减号禁用)', () => {
  render(<Counter />);
  fireEvent.press(screen.getByTestId('dec'));
  expect(screen.getByTestId('count')).toHaveTextContent('Count: 0');
});
```

## 标准范例:audio 模块

### 1. 纯逻辑 + reducer `src/audio/audioLogic.ts`

整个状态机都在这里:状态/事件类型、守卫、纯 `audioReducer`。无 React、无副作用。

```ts
export type RecordingStatus = 'idle' | 'recording' | 'recorded' | 'playing';

export type PermissionStatus = 'unknown' | 'granted' | 'denied' | 'blocked';

export type AudioErrorKind = 'permission' | 'device' | 'playback';
export type AudioError = { kind: AudioErrorKind; message: string };

export type AudioState = {
  status: RecordingStatus;
  permission: PermissionStatus;
  durationMs: number;
  uri: string | null;
  error: AudioError | null;
};

export const initialAudioState: AudioState = {
  status: 'idle',
  permission: 'unknown',
  durationMs: 0,
  uri: null,
  error: null,
};

export type AudioEvent =
  | { type: 'permissionChanged'; permission: PermissionStatus }
  | { type: 'recordingStarted' }
  | { type: 'tick'; durationMs: number }
  | { type: 'recordingStopped'; uri: string }
  | { type: 'playbackStarted' }
  | { type: 'playbackEnded' }
  | { type: 'failed'; error: AudioError };

// --- 守卫(纯谓词) ---

// UI 可用性守卫:录音按钮该不该亮?
// 故意不看权限——按下按钮正是触发权限申请的途径。
export function canRequestStart(status: RecordingStatus): boolean {
  return status === 'idle' || status === 'recorded';
}

// 完整前置条件守卫:录音到底能不能开始?
// Hook 在 start() 内部、权限解析之后重新校验。
export function canStartRecording(
  permission: PermissionStatus,
  status: RecordingStatus,
): boolean {
  return permission === 'granted' && canRequestStart(status);
}

export function canStopRecording(status: RecordingStatus): boolean {
  return status === 'recording';
}

export function canPlay(status: RecordingStatus, uri: string | null): boolean {
  return status === 'recorded' && uri !== null;
}

export function canStopPlayback(status: RecordingStatus): boolean {
  return status === 'playing';
}

export function formatDuration(ms: number): string {
  const safe = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(safe / 60);
  const seconds = safe % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

// --- reducer(纯转移;非法转移即 no-op) ---

export function audioReducer(state: AudioState, event: AudioEvent): AudioState {
  switch (event.type) {
    case 'permissionChanged':
      return { ...state, permission: event.permission };

    case 'recordingStarted':
      if (!canRequestStart(state.status)) {
        return state;
      }
      return { ...state, status: 'recording', durationMs: 0, uri: null, error: null };

    case 'tick':
      if (state.status !== 'recording') {
        return state;
      }
      return { ...state, durationMs: event.durationMs };

    case 'recordingStopped':
      if (state.status !== 'recording') {
        return state;
      }
      return { ...state, status: 'recorded', uri: event.uri };

    case 'playbackStarted':
      if (!canPlay(state.status, state.uri)) {
        return state;
      }
      return { ...state, status: 'playing', error: null };

    case 'playbackEnded':
      if (state.status !== 'playing') {
        return state;
      }
      return { ...state, status: 'recorded' };

    case 'failed':
      // device 失败把录音中止回 idle;其他类型保持当前状态。
      return {
        ...state,
        error: event.error,
        status: event.error.kind === 'device' ? 'idle' : state.status,
      };
  }
}
```

### 1t. 逻辑测试 `__tests__/audioLogic.test.ts`

最厚也最廉价的测试文件:纯、同步、无 React。守卫测真/假分支与边界;reducer **穷举每种事件 × 每个相关源状态,包括非法转移为 no-op**。

```ts
import {
  audioReducer,
  canPlay,
  canRequestStart,
  canStartRecording,
  formatDuration,
  initialAudioState,
  type AudioState,
} from '../src/audio/audioLogic';

const state = (over: Partial<AudioState> = {}): AudioState => ({
  ...initialAudioState,
  ...over,
});

describe('守卫', () => {
  test.each([
    ['idle', true],
    ['recorded', true],
    ['recording', false],
    ['playing', false],
  ] as const)('canRequestStart(%s) === %s', (status, expected) => {
    expect(canRequestStart(status)).toBe(expected);
  });

  test('canStartRecording 需要权限已授予且状态可启动', () => {
    expect(canStartRecording('granted', 'idle')).toBe(true);
    expect(canStartRecording('denied', 'idle')).toBe(false);
    expect(canStartRecording('granted', 'recording')).toBe(false);
  });

  test('canPlay 需要 recorded 状态且有 uri', () => {
    expect(canPlay('recorded', 'file://r.m4a')).toBe(true);
    expect(canPlay('recorded', null)).toBe(false);
    expect(canPlay('idle', 'file://r.m4a')).toBe(false);
  });
});

describe('audioReducer', () => {
  test('recordingStarted 重置时长/uri/错误(重录场景)', () => {
    const next = audioReducer(
      state({
        status: 'recorded',
        durationMs: 5000,
        uri: 'file://old.m4a',
        error: { kind: 'playback', message: 'x' },
      }),
      { type: 'recordingStarted' },
    );
    expect(next).toEqual(state({ status: 'recording' }));
  });

  test.each(['recording', 'playing'] as const)(
    '%s 状态下 recordingStarted 为 no-op',
    status => {
      const s = state({ status });
      expect(audioReducer(s, { type: 'recordingStarted' })).toBe(s);
    },
  );

  test('tick 仅在录音中更新时长', () => {
    const recording = state({ status: 'recording' });
    expect(audioReducer(recording, { type: 'tick', durationMs: 1200 }).durationMs).toBe(1200);
    const idle = state();
    expect(audioReducer(idle, { type: 'tick', durationMs: 1200 })).toBe(idle);
  });

  test('recordingStopped 保存 uri;非录音中为 no-op', () => {
    const next = audioReducer(state({ status: 'recording' }), {
      type: 'recordingStopped',
      uri: 'file://r.m4a',
    });
    expect(next.status).toBe('recorded');
    expect(next.uri).toBe('file://r.m4a');
    const idle = state();
    expect(audioReducer(idle, { type: 'recordingStopped', uri: 'file://r.m4a' })).toBe(idle);
  });

  test('播放生命周期:仅 recorded+uri 可开始,仅 playing 可结束', () => {
    const recorded = state({ status: 'recorded', uri: 'file://r.m4a' });
    expect(audioReducer(recorded, { type: 'playbackStarted' }).status).toBe('playing');
    expect(audioReducer(state({ status: 'recorded', uri: null }), { type: 'playbackStarted' }).status).toBe('recorded');
    expect(audioReducer(state({ status: 'playing', uri: 'file://r.m4a' }), { type: 'playbackEnded' }).status).toBe('recorded');
    expect(audioReducer(recorded, { type: 'playbackEnded' })).toBe(recorded);
  });

  test('failed:device 错误中止回 idle,playback 错误保持状态', () => {
    const deviceFail = audioReducer(state({ status: 'recording' }), {
      type: 'failed',
      error: { kind: 'device', message: 'mic busy' },
    });
    expect(deviceFail.status).toBe('idle');
    expect(deviceFail.error).toEqual({ kind: 'device', message: 'mic busy' });

    const playFail = audioReducer(state({ status: 'playing', uri: 'file://r.m4a' }), {
      type: 'failed',
      error: { kind: 'playback', message: 'corrupt' },
    });
    expect(playFail.status).toBe('playing');
  });
});

describe('formatDuration', () => {
  test.each([
    [0, '00:00'],
    [999, '00:00'],
    [1000, '00:01'],
    [61000, '01:01'],
    [-5, '00:00'],
  ])('formatDuration(%i) === %s', (ms, expected) => {
    expect(formatDuration(ms)).toBe(expected);
  });
});
```

### 2. 依赖接口 `src/audio/audioRecorder.ts`(接口 + 模拟实现)

```ts
export type PlaybackEndUnsubscribe = () => void;

export type Recorder = {
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<string>;
  startPlayback: (uri: string) => Promise<void>;
  stopPlayback: () => Promise<void>;
  onPlaybackEnd?: (cb: () => void) => PlaybackEndUnsubscribe;
};

export function createSimulatedRecorder(): Recorder {
  let uri: string | null = null;
  return {
    async startRecording() {
      uri = null;
    },
    async stopRecording() {
      uri = `simulated://recording-${Date.now()}.m4a`;
      return uri;
    },
    async startPlayback(_uri: string) {},
    async stopPlayback() {},
  };
}
```

### 3. 真实实现 `src/audio/nitroSoundRecorder.ts`

```ts
import Sound from 'react-native-nitro-sound';
import type { Recorder } from './audioRecorder';

export function createNitroSoundRecorder(): Recorder {
  return {
    async startRecording() {
      await Sound.startRecorder();
    },
    async stopRecording() {
      return await Sound.stopRecorder();
    },
    async startPlayback(uri: string) {
      await Sound.startPlayer(uri);
    },
    async stopPlayback() {
      await Sound.stopPlayer();
    },
    onPlaybackEnd(cb: () => void) {
      Sound.addPlaybackEndListener(() => cb());
      return () => Sound.removePlaybackEndListener();
    },
  };
}
```

### 3b. 适配器委托测试 `__tests__/nitroSoundRecorder.test.ts`

真实实现是薄适配器,需要一个**委托测试**:mock 原生库,只断言转发——绝不测原生行为本身。

```ts
jest.mock('react-native-nitro-sound', () => ({
  __esModule: true,
  default: {
    startRecorder: jest.fn(),
    stopRecorder: jest.fn(),
    startPlayer: jest.fn(),
    stopPlayer: jest.fn(),
    addPlaybackEndListener: jest.fn(),
    removePlaybackEndListener: jest.fn(),
  },
}));

import Sound from 'react-native-nitro-sound';
import { createNitroSoundRecorder } from '../src/audio/nitroSoundRecorder';

test('stopRecording 委托并返回保存的 uri', async () => {
  (Sound.stopRecorder as jest.Mock).mockResolvedValue('file://r.m4a');
  await expect(createNitroSoundRecorder().stopRecording()).resolves.toBe(
    'file://r.m4a',
  );
});

test('startPlayback 转发 uri', async () => {
  await createNitroSoundRecorder().startPlayback('file://r.m4a');
  expect(Sound.startPlayer).toHaveBeenCalledWith('file://r.m4a');
});

test('onPlaybackEnd 订阅,返回的函数退订', () => {
  const unsubscribe = createNitroSoundRecorder().onPlaybackEnd!(() => {});
  expect(Sound.addPlaybackEndListener).toHaveBeenCalled();
  unsubscribe();
  expect(Sound.removePlaybackEndListener).toHaveBeenCalled();
});
```

### 4. 权限接口 `src/audio/audioPermissions.ts`(接口 + 模拟实现)

权限和其他副作用一样,走与 recorder 相同的模式:接口 + 模拟实现放一个文件,真实适配器**单独成文件**(4b)。接口文件**零 `react-native` import**——引用 `MicrophonePermissions` 类型永远不会拖进原生模块。Hook 通过注入接收它,绝不直接 import 原生实现。

```ts
import type { PermissionStatus } from './audioLogic';

export type MicrophonePermissions = {
  check: () => Promise<PermissionStatus>;
  request: () => Promise<PermissionStatus>;
  promptOpenSettings: () => void;
};

export function createSimulatedPermissions(
  initial: PermissionStatus = 'granted',
): MicrophonePermissions {
  return {
    async check() {
      return initial;
    },
    async request() {
      return initial;
    },
    promptOpenSettings() {},
  };
}
```

### 4b. 原生实现 `src/audio/nativeMicrophonePermissions.ts`

> ⚠️ **仅 Android 的参考实现。** iOS 上这个占位实现不弹窗直接返回 `'granted'`。真实 iOS 支持需要 [`react-native-permissions`](https://github.com/zoontek/react-native-permissions)(`PERMISSIONS.IOS.MICROPHONE`)——保留接口,换实现即可。

```ts
import { Alert, Linking, PermissionsAndroid, Platform } from 'react-native';
import type { PermissionStatus } from './audioLogic';
import type { MicrophonePermissions } from './audioPermissions';

export type RequestMicrophoneOptions = {
  rationaleTitle?: string;
  rationaleMessage?: string;
  blockedTitle?: string;
  blockedMessage?: string;
  openSettingsLabel?: string;
  cancelLabel?: string;
};

const DEFAULTS: Required<RequestMicrophoneOptions> = {
  rationaleTitle: '麦克风权限',
  rationaleMessage: '需要使用麦克风才能录音',
  blockedTitle: '权限被拒绝',
  blockedMessage: '请在系统设置中开启麦克风权限',
  openSettingsLabel: '打开设置',
  cancelLabel: '取消',
};

export function createNativeMicrophonePermissions(
  options: RequestMicrophoneOptions = {},
): MicrophonePermissions {
  const opts = { ...DEFAULTS, ...options };

  const promptOpenSettings = () => {
    Alert.alert(opts.blockedTitle, opts.blockedMessage, [
      { text: opts.cancelLabel, style: 'cancel' },
      { text: opts.openSettingsLabel, onPress: () => Linking.openSettings() },
    ]);
  };

  return {
    async check(): Promise<PermissionStatus> {
      if (Platform.OS === 'android') {
        const granted = await PermissionsAndroid.check(
          PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
        );
        return granted ? 'granted' : 'denied';
      }
      return 'unknown'; // iOS 占位——见上方警告
    },

    async request(): Promise<PermissionStatus> {
      if (Platform.OS === 'android') {
        const already = await PermissionsAndroid.check(
          PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
        );
        if (already) {
          return 'granted';
        }

        const result = await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
          {
            title: opts.rationaleTitle,
            message: opts.rationaleMessage,
            buttonPositive: '允许',
            buttonNegative: opts.cancelLabel,
          },
        );

        if (result === PermissionsAndroid.RESULTS.GRANTED) {
          return 'granted';
        }
        if (result === PermissionsAndroid.RESULTS.NEVER_ASK_AGAIN) {
          // 这里不弹窗——Hook 在拿到 'blocked' 后会调 promptOpenSettings(),
          // request() 自己再弹会让用户被提示两次。
          return 'blocked';
        }
        return 'denied';
      }

      return 'granted'; // iOS 占位——见上方警告
    },

    promptOpenSettings,
  };
}
```

### 4c. 原生权限测试 `__tests__/nativeMicrophonePermissions.test.ts`

与 recorder 不同,这个适配器含真实**映射逻辑**(已授权短路、`NEVER_ASK_AGAIN` → `blocked`),所以它的测试要断言映射——依然 mock 原生模块。

```ts
jest.mock('react-native', () => ({
  Alert: { alert: jest.fn() },
  Linking: { openSettings: jest.fn() },
  Platform: { OS: 'android' },
  PermissionsAndroid: {
    check: jest.fn(),
    request: jest.fn(),
    PERMISSIONS: { RECORD_AUDIO: 'android.permission.RECORD_AUDIO' },
    RESULTS: { GRANTED: 'granted', DENIED: 'denied', NEVER_ASK_AGAIN: 'never_ask_again' },
  },
}));

import { Alert, PermissionsAndroid } from 'react-native';
import { createNativeMicrophonePermissions } from '../src/audio/nativeMicrophonePermissions';

const check = PermissionsAndroid.check as jest.Mock;
const request = PermissionsAndroid.request as jest.Mock;

beforeEach(() => jest.clearAllMocks());

test('已授权时 request 短路返回 granted(不弹窗)', async () => {
  check.mockResolvedValue(true);
  await expect(createNativeMicrophonePermissions().request()).resolves.toBe('granted');
  expect(request).not.toHaveBeenCalled();
});

test('request 正确映射 GRANTED 与 denied 结果', async () => {
  check.mockResolvedValue(false);
  request.mockResolvedValueOnce('granted');
  await expect(createNativeMicrophonePermissions().request()).resolves.toBe('granted');
  request.mockResolvedValueOnce('denied');
  await expect(createNativeMicrophonePermissions().request()).resolves.toBe('denied');
});

test('NEVER_ASK_AGAIN 映射为 blocked,且不自行弹窗(由 Hook 负责提示)', async () => {
  check.mockResolvedValue(false);
  request.mockResolvedValue('never_ask_again');
  await expect(createNativeMicrophonePermissions().request()).resolves.toBe('blocked');
  expect(Alert.alert).not.toHaveBeenCalled();
});

test('promptOpenSettings 弹出设置引导', () => {
  createNativeMicrophonePermissions().promptOpenSettings();
  expect(Alert.alert).toHaveBeenCalled();
});
```

### 5. Hook `src/audio/useAudio.ts`(useReducer + 编排 IO + dispatch)

Hook 持有 `useReducer`,通过注入依赖做 IO,然后 dispatch 一个事件——它从不自己决定下一个状态。动作回调从 ref 读 state(ref 在 effect 中赋值,绝不在渲染期写),保持稳定;start 动作有重入守护。时长 tick 在 `useEffect` 中**派生自状态**,所以任何离开 `recording` 的路径——停止、设备失败、卸载——都会自动清理它。返回的 API 经 `useMemo`。

```ts
import { useCallback, useEffect, useMemo, useReducer, useRef } from 'react';
import {
  audioReducer,
  canPlay,
  canRequestStart,
  canStartRecording,
  canStopPlayback,
  canStopRecording,
  initialAudioState,
  type AudioError,
  type PermissionStatus,
  type RecordingStatus,
} from './audioLogic';
import type { MicrophonePermissions } from './audioPermissions';
import type { Recorder } from './audioRecorder';

export type AudioApi = {
  status: RecordingStatus;
  permission: PermissionStatus;
  durationMs: number;
  uri: string | null;
  error: AudioError | null;
  canStart: boolean;
  canStop: boolean;
  canPlay: boolean;
  canStopPlay: boolean;
  start: () => Promise<void>;
  stop: () => Promise<void>;
  play: () => Promise<void>;
  stopPlay: () => Promise<void>;
};

export type UseAudioOptions = {
  recorder: Recorder;                 // 必填——不许静默兜底
  permissions: MicrophonePermissions; // 必填——权限同样是副作用
  tickMs?: number;
};

export function useAudio(options: UseAudioOptions): AudioApi {
  const { recorder, permissions } = options;
  const tickMs = options.tickMs ?? 250;

  const [state, dispatch] = useReducer(audioReducer, initialAudioState);

  // 把 state 镜像进 ref,让动作回调能读到最新值,又不必把 state
  // 列进依赖(从而保持回调稳定)。在 effect 中赋值——渲染期写 ref
  // 违反 Rules of React。
  const stateRef = useRef(state);
  useEffect(() => {
    stateRef.current = state;
  });

  const startedAtRef = useRef(0);
  const inFlightRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    permissions.check().then(p => {
      if (!cancelled) {
        dispatch({ type: 'permissionChanged', permission: p });
      }
    });
    return () => {
      cancelled = true;
    };
  }, [permissions]);

  // tick interval 派生自状态,而非在动作里启动:所有离开 'recording'
  // 的路径(停止、设备失败、卸载)都会自动清理它。
  useEffect(() => {
    if (state.status !== 'recording') {
      return;
    }
    const id = setInterval(() => {
      dispatch({ type: 'tick', durationMs: Date.now() - startedAtRef.current });
    }, tickMs);
    return () => clearInterval(id);
  }, [state.status, tickMs]);

  useEffect(() => {
    if (!recorder.onPlaybackEnd) {
      return;
    }
    return recorder.onPlaybackEnd(() => dispatch({ type: 'playbackEnded' }));
  }, [recorder]);

  const start = useCallback(async () => {
    if (!canRequestStart(stateRef.current.status) || inFlightRef.current) {
      return;
    }
    inFlightRef.current = true;
    try {
      let permission = stateRef.current.permission;
      if (permission !== 'granted') {
        permission = await permissions.request();
        dispatch({ type: 'permissionChanged', permission });
      }
      if (!canStartRecording(permission, stateRef.current.status)) {
        if (permission === 'blocked') {
          permissions.promptOpenSettings();
        }
        return;
      }
      await recorder.startRecording();
      startedAtRef.current = Date.now();
      dispatch({ type: 'recordingStarted' });
    } catch (e) {
      dispatch({ type: 'failed', error: { kind: 'device', message: toMessage(e) } });
    } finally {
      inFlightRef.current = false;
    }
  }, [recorder, permissions]);

  const stop = useCallback(async () => {
    if (!canStopRecording(stateRef.current.status)) {
      return;
    }
    try {
      const uri = await recorder.stopRecording();
      dispatch({ type: 'recordingStopped', uri });
    } catch (e) {
      dispatch({ type: 'failed', error: { kind: 'device', message: toMessage(e) } });
    }
  }, [recorder]);

  const play = useCallback(async () => {
    const { status, uri } = stateRef.current;
    if (!canPlay(status, uri)) {
      return;
    }
    try {
      await recorder.startPlayback(uri as string);
      dispatch({ type: 'playbackStarted' });
    } catch (e) {
      dispatch({ type: 'failed', error: { kind: 'playback', message: toMessage(e) } });
    }
  }, [recorder]);

  const stopPlay = useCallback(async () => {
    if (!canStopPlayback(stateRef.current.status)) {
      return;
    }
    try {
      await recorder.stopPlayback();
      dispatch({ type: 'playbackEnded' });
    } catch (e) {
      dispatch({ type: 'failed', error: { kind: 'playback', message: toMessage(e) } });
    }
  }, [recorder]);

  return useMemo<AudioApi>(
    () => ({
      status: state.status,
      permission: state.permission,
      durationMs: state.durationMs,
      uri: state.uri,
      error: state.error,
      canStart: canRequestStart(state.status),
      canStop: canStopRecording(state.status),
      canPlay: canPlay(state.status, state.uri),
      canStopPlay: canStopPlayback(state.status),
      start,
      stop,
      play,
      stopPlay,
    }),
    [state, start, stop, play, stopPlay],
  );
}

function toMessage(e: unknown): string {
  if (e instanceof Error) {
    return e.message;
  }
  return String(e);
}
```

### 5b. Hook 测试 `__tests__/useAudio.test.ts`(桩 + 假定时器 + 重入)

只测 Hook 在 reducer 之上额外做的事。reducer 的真值表已由 `audioLogic.test.ts` 覆盖。

> ⚠️ **注入依赖必须在 `renderHook` 回调之外创建。** 若写成 `renderHook(() => useAudio({ permissions: createSimulatedPermissions('granted') }))`,每次渲染都会新建 `permissions` 对象,挂载 effect 的 `[permissions]` 依赖每次都变 → 无限重跑 → 测试卡死。把桩放进稳定变量再闭包引用。

```ts
import { act, renderHook } from '@testing-library/react-native';
import { useAudio } from '../src/audio/useAudio';
import {
  createSimulatedPermissions,
  type MicrophonePermissions,
} from '../src/audio/audioPermissions';
import type { Recorder } from '../src/audio/audioRecorder';

function baseRecorder(over: Partial<Recorder> = {}): Recorder {
  return {
    startRecording: jest.fn(async () => {}),
    stopRecording: jest.fn(async () => 'file://r.m4a'),
    startPlayback: jest.fn(async () => {}),
    stopPlayback: jest.fn(async () => {}),
    ...over,
  };
}

test('录音中时长在递增(假定时器)', async () => {
  jest.useFakeTimers();
  try {
    const recorder = baseRecorder();
    const permissions = createSimulatedPermissions('granted'); // 稳定,在 render 外
    const { result } = renderHook(() => useAudio({ recorder, permissions, tickMs: 100 }));

    await act(async () => {
      await result.current.start();
    });
    act(() => {
      jest.advanceTimersByTime(250);
    });

    expect(result.current.status).toBe('recording');
    expect(result.current.durationMs).toBeGreaterThan(0);
  } finally {
    jest.useRealTimers();
  }
});

test('连点两次 start 只录一次(重入被守护)', async () => {
  let resolveStart!: () => void;
  const recorder = baseRecorder({
    startRecording: jest.fn(() => new Promise<void>(r => (resolveStart = r))),
  });
  const permissions = createSimulatedPermissions('granted');
  const { result } = renderHook(() => useAudio({ recorder, permissions }));

  await act(async () => {
    result.current.start(); // 卡在 pending 的 startRecording 内
    await result.current.start(); // 第二次立即退出
    resolveStart();
  });

  expect(recorder.startRecording).toHaveBeenCalledTimes(1);
});

test('device 失败抛出类型化错误并回到 idle', async () => {
  const recorder = baseRecorder({
    startRecording: jest.fn(async () => {
      throw new Error('mic busy');
    }),
  });
  const permissions = createSimulatedPermissions('granted');
  const { result } = renderHook(() => useAudio({ recorder, permissions }));

  await act(async () => {
    await result.current.start();
  });

  expect(result.current.error).toEqual({ kind: 'device', message: 'mic busy' });
  expect(result.current.status).toBe('idle');
});

test('权限被禁(blocked):request 一次、弹设置引导、绝不录音', async () => {
  const recorder = baseRecorder();
  const permissions: MicrophonePermissions = {
    check: jest.fn(async () => 'denied' as const),
    request: jest.fn(async () => 'blocked' as const),
    promptOpenSettings: jest.fn(),
  };
  const { result } = renderHook(() => useAudio({ recorder, permissions }));

  await act(async () => {
    await result.current.start();
  });

  expect(permissions.request).toHaveBeenCalledTimes(1);
  expect(permissions.promptOpenSettings).toHaveBeenCalledTimes(1);
  expect(recorder.startRecording).not.toHaveBeenCalled();
  expect(result.current.permission).toBe('blocked');
  expect(result.current.status).toBe('idle');
});
```

### 6. 视图 `src/audio/AudioView.tsx`(纯展示 + testID + a11y + Pressable)

```tsx
import { Pressable, StyleSheet, Text, View } from 'react-native';
import {
  formatDuration,
  type AudioError,
  type PermissionStatus,
  type RecordingStatus,
} from './audioLogic';

export type AudioViewProps = {
  status: RecordingStatus;
  permission: PermissionStatus;
  durationMs: number;
  uri: string | null;
  error: AudioError | null;
  canStart: boolean;
  canStop: boolean;
  canPlay: boolean;
  canStopPlay: boolean;
  onStart: () => void;
  onStop: () => void;
  onPlay: () => void;
  onStopPlay: () => void;
};

export function AudioView({
  status, permission, durationMs, uri, error,
  canStart, canStop, canPlay, canStopPlay,
  onStart, onStop, onPlay, onStopPlay,
}: AudioViewProps) {
  return (
    <View style={styles.container}>
      <Text testID="audio-status" style={styles.status}>状态: {labelFor(status)}</Text>
      <Text testID="audio-permission" style={styles.muted}>权限: {labelForPermission(permission)}</Text>
      <Text testID="audio-duration" style={styles.duration}>{formatDuration(durationMs)}</Text>
      <Text testID="audio-uri" style={styles.muted} numberOfLines={1}>{uri ?? '尚未录音'}</Text>
      {error !== null ? (
        <Text testID="audio-error" style={styles.error}>{error.message}</Text>
      ) : null}
      <View style={styles.row}>
        <ActionButton testID="audio-start" label={status === 'recorded' ? '重新录音' : '开始录音'} disabled={!canStart} onPress={onStart} />
        <ActionButton testID="audio-stop" label="停止录音" disabled={!canStop} onPress={onStop} />
      </View>
      <View style={styles.row}>
        <ActionButton testID="audio-play" label="播放" disabled={!canPlay} onPress={onPlay} />
        <ActionButton testID="audio-stop-play" label="停止播放" disabled={!canStopPlay} onPress={onStopPlay} />
      </View>
    </View>
  );
}

type ActionButtonProps = {
  testID: string;
  label: string;
  disabled: boolean;
  onPress: () => void;
};

function ActionButton({ testID, label, disabled, onPress }: ActionButtonProps) {
  return (
    <Pressable
      testID={testID}
      disabled={disabled}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ disabled }}
      style={[styles.btn, disabled && styles.btnDisabled]}
    >
      <Text style={styles.btnLabel}>{label}</Text>
    </Pressable>
  );
}

function labelFor(status: RecordingStatus): string {
  switch (status) {
    case 'idle': return '空闲';
    case 'recording': return '录音中';
    case 'recorded': return '已录制';
    case 'playing': return '播放中';
  }
}

function labelForPermission(p: PermissionStatus): string {
  switch (p) {
    case 'granted': return '已授权';
    case 'denied': return '未授权';
    case 'blocked': return '已禁用';
    case 'unknown': return '未知';
  }
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 16, gap: 12 },
  status: { fontWeight: '600' },
  muted: { color: '#888' },
  duration: { fontWeight: '600' },
  error: { color: '#c0392b' },
  row: { flexDirection: 'row', gap: 16 },
  btn: { paddingHorizontal: 16, paddingVertical: 10, borderRadius: 8, borderCurve: 'continuous', backgroundColor: '#222' },
  btnDisabled: { backgroundColor: '#bbb' },
  btnLabel: { color: 'white', fontWeight: '600' },
});
```

### 7. 容器 `src/audio/AudioScreen.tsx`(薄胶水层)

```tsx
import { AudioView } from './AudioView';
import { useAudio, type UseAudioOptions } from './useAudio';

export function AudioScreen(options: UseAudioOptions) {
  const audio = useAudio(options);
  return (
    <AudioView
      status={audio.status}
      permission={audio.permission}
      durationMs={audio.durationMs}
      uri={audio.uri}
      error={audio.error}
      canStart={audio.canStart}
      canStop={audio.canStop}
      canPlay={audio.canPlay}
      canStopPlay={audio.canStopPlay}
      onStart={audio.start}
      onStop={audio.stop}
      onPlay={audio.play}
      onStopPlay={audio.stopPlay}
    />
  );
}
```

### 8. 组合根接线真实实现 `App.tsx`

真实实现只在这里注入**一次**——其他任何地方都不 import 它们。

```tsx
import React, { useMemo } from 'react';
import { StatusBar, useColorScheme } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { createNativeMicrophonePermissions } from './src/audio/nativeMicrophonePermissions';
import { AudioScreen } from './src/audio/AudioScreen';
import { createNitroSoundRecorder } from './src/audio/nitroSoundRecorder';

function App() {
  const isDarkMode = useColorScheme() === 'dark';
  const recorder = useMemo(() => createNitroSoundRecorder(), []);
  const permissions = useMemo(() => createNativeMicrophonePermissions(), []);

  return (
    <SafeAreaProvider>
      <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />
      <AudioScreen recorder={recorder} permissions={permissions} />
    </SafeAreaProvider>
  );
}

export default App;
```

