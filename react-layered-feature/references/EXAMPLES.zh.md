---
name: react-layered-feature 参考代码
description: react-layered-feature 架构的完整代码范例,以 src/audio(纯 reducer 状态机 + 基于浏览器 API 的注入副作用)为标准实现,src/counter 为对照。
---

# 参考代码

两个完整范例,从简到繁:

- **`counter`**——分层的最小形态:纯逻辑 + 守卫、Hook、视图、容器,无副作用、无 reducer(简单状态用不上)。先看它了解骨架。
- **`audio`**——**标准范例**:真正的状态机(纯 reducer)、注入的副作用(基于 `MediaRecorder` / Permissions API 的 recorder + 权限)、定时器、类型化错误。新增功能模块逐文件对照它。

> 注:此为中文文案版本,英文版见 [EXAMPLES.md](EXAMPLES.md)。

> 各小节按"实现文件在前、测试在后"(`1` → `1t`)排版,仅为方便阅读——**开发顺序相反**:先写测试、看它失败,再写实现(见 SKILL.zh.md 的落地清单)。

> logic 层(`audioLogic.ts`)与 Hook 层(`useAudio.ts`)和 React Native 姊妹技能(`rn-layered-feature`)**完全相同**——这正是"状态机保持纯、副作用走注入"的回报。只有适配器与视图是 Web 特有的。

## 目录

可从头读完整构建流程,或跳到某个模块再按文件名搜索。每个文件后紧跟其测试
(`N` → `Nt` / `Nb`);构建顺序相反——测试先行(见 SKILL.zh.md 的落地清单)。

**[`counter` — 最小分层](#最小范例counter-模块)**(无副作用,`useState` + 纯函数):`counterLogic.ts` + 测试 · `useCounter.ts` + 测试 · `CounterView.tsx` + 测试 · `Counter.tsx` + 测试。

**[`audio` — 标准完整范例](#标准范例audio-模块)**(纯 reducer、注入副作用、计时器、类型化错误):
- `audioLogic.ts`(逻辑 + reducer)+ 测试
- `audioRecorder.ts`(接口)· `browserRecorder.ts`(真实适配器)+ 测试
- `audioPermissions.ts`(接口)· `browserMicrophonePermissions.ts`(浏览器实现)+ 测试
- `useAudio.ts`(Hook)+ 测试
- `AudioView.tsx`(视图)· `AudioScreen.tsx`(容器)· `App.tsx`(组合根)

## 最小范例:counter 模块

无副作用,所以无需依赖注入;状态只是一个数字,所以 `useState` + 纯函数足矣(转移变复杂时再升级到 reducer——见 `audio`)。它仍遵守其余每条规则:带守卫的纯逻辑、用原生 `<button>` 且带 `data-testid` 的纯视图、薄容器,以及每层一个测试。

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
import { act, renderHook } from '@testing-library/react';
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
import type { CSSProperties } from 'react';

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
    <div style={styles.container}>
      <p data-testid="count" style={styles.count}>Count: {count}</p>
      <div style={styles.row}>
        <ActionButton testID="dec" label="-" disabled={!canDecrement} onClick={onDecrement} />
        <ActionButton testID="inc" label="+" disabled={false} onClick={onIncrement} />
      </div>
      <ActionButton testID="reset" label="重置" disabled={false} onClick={onReset} />
    </div>
  );
}

type ActionButtonProps = {
  testID: string;
  label: string;
  disabled: boolean;
  onClick: () => void;
};

function ActionButton({ testID, label, disabled, onClick }: ActionButtonProps) {
  return (
    <button
      type="button"
      data-testid={testID}
      disabled={disabled}
      onClick={onClick}
      style={{ ...styles.btn, ...(disabled ? styles.btnDisabled : undefined) }}
    >
      {label}
    </button>
  );
}

const styles: Record<string, CSSProperties> = {
  container: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 },
  count: { fontSize: 24 },
  row: { display: 'flex', gap: 24 },
  btn: { minWidth: 48, padding: '10px 16px', borderRadius: 8, border: 'none', background: '#222', color: 'white', fontSize: 20, fontWeight: 600, cursor: 'pointer' },
  btnDisabled: { background: '#bbb', cursor: 'default' },
};
```

### 3t. 视图测试 `__tests__/CounterView.test.tsx`

```tsx
import { fireEvent, render, screen } from '@testing-library/react';
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

  fireEvent.click(screen.getByTestId('inc'));
  fireEvent.click(screen.getByTestId('reset'));
  fireEvent.click(screen.getByTestId('dec')); // 禁用 -> 忽略
  expect(onIncrement).toHaveBeenCalledTimes(1);
  expect(onReset).toHaveBeenCalledTimes(1);
  expect(onDecrement).not.toHaveBeenCalled();

  rerender(<CounterView count={1} canDecrement={true} onIncrement={onIncrement} onDecrement={onDecrement} onReset={onReset} />);
  fireEvent.click(screen.getByTestId('dec'));
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
import { fireEvent, render, screen } from '@testing-library/react';
import { Counter } from '../src/counter/Counter';

test('用户累加并重置', () => {
  render(<Counter />);
  expect(screen.getByTestId('count')).toHaveTextContent('Count: 0');
  fireEvent.click(screen.getByTestId('inc'));
  fireEvent.click(screen.getByTestId('inc'));
  expect(screen.getByTestId('count')).toHaveTextContent('Count: 2');
  fireEvent.click(screen.getByTestId('reset'));
  expect(screen.getByTestId('count')).toHaveTextContent('Count: 0');
});

test('计数永不为负(零处减号禁用)', () => {
  render(<Counter />);
  fireEvent.click(screen.getByTestId('dec'));
  expect(screen.getByTestId('count')).toHaveTextContent('Count: 0');
});
```

## 标准范例:audio 模块

### 1. 纯逻辑 + reducer `src/audio/audioLogic.ts`

整个状态机都在这里:状态/事件类型、守卫、纯 `audioReducer`。无 React、无副作用、不触碰浏览器 API——此文件与 React Native 版逐字相同。

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
    expect(canPlay('recorded', 'blob:r')).toBe(true);
    expect(canPlay('recorded', null)).toBe(false);
    expect(canPlay('idle', 'blob:r')).toBe(false);
  });
});

describe('audioReducer', () => {
  test('recordingStarted 重置时长/uri/错误(重录场景)', () => {
    const next = audioReducer(
      state({
        status: 'recorded',
        durationMs: 5000,
        uri: 'blob:old',
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
      uri: 'blob:r',
    });
    expect(next.status).toBe('recorded');
    expect(next.uri).toBe('blob:r');
    const idle = state();
    expect(audioReducer(idle, { type: 'recordingStopped', uri: 'blob:r' })).toBe(idle);
  });

  test('播放生命周期:仅 recorded+uri 可开始,仅 playing 可结束', () => {
    const recorded = state({ status: 'recorded', uri: 'blob:r' });
    expect(audioReducer(recorded, { type: 'playbackStarted' }).status).toBe('playing');
    expect(audioReducer(state({ status: 'recorded', uri: null }), { type: 'playbackStarted' }).status).toBe('recorded');
    expect(audioReducer(state({ status: 'playing', uri: 'blob:r' }), { type: 'playbackEnded' }).status).toBe('recorded');
    expect(audioReducer(recorded, { type: 'playbackEnded' })).toBe(recorded);
  });

  test('failed:device 错误中止回 idle,playback 错误保持状态', () => {
    const deviceFail = audioReducer(state({ status: 'recording' }), {
      type: 'failed',
      error: { kind: 'device', message: 'mic busy' },
    });
    expect(deviceFail.status).toBe('idle');
    expect(deviceFail.error).toEqual({ kind: 'device', message: 'mic busy' });

    const playFail = audioReducer(state({ status: 'playing', uri: 'blob:r' }), {
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
      uri = `simulated://recording-${Date.now()}.webm`;
      return uri;
    },
    async startPlayback(_uri: string) {},
    async stopPlayback() {},
  };
}
```

### 3. 真实实现 `src/audio/browserRecorder.ts`

对 `getUserMedia` + `MediaRecorder`(录音)与 `HTMLAudioElement`(播放)的薄适配器。录音结果暴露为 object URL——架构其余部分早已理解的同一个 `string` uri。

```ts
import type { Recorder } from './audioRecorder';

export function createBrowserRecorder(): Recorder {
  let active: MediaRecorder | null = null;
  let chunks: Blob[] = [];
  let player: HTMLAudioElement | null = null;
  const endListeners = new Set<() => void>();

  return {
    async startRecording() {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunks = [];
      active = new MediaRecorder(stream);
      active.ondataavailable = e => {
        chunks.push(e.data);
      };
      active.start();
    },

    async stopRecording() {
      const recorder = active;
      if (recorder === null) {
        throw new Error('stopRecording called while not recording');
      }
      active = null;
      const uri = await new Promise<string>(resolve => {
        recorder.onstop = () => {
          resolve(URL.createObjectURL(new Blob(chunks, { type: recorder.mimeType })));
        };
        recorder.stop();
      });
      recorder.stream.getTracks().forEach(track => track.stop()); // 释放麦克风
      return uri;
    },

    async startPlayback(uri: string) {
      player = new Audio(uri);
      player.onended = () => {
        endListeners.forEach(cb => cb());
      };
      await player.play();
    },

    async stopPlayback() {
      player?.pause();
      player = null;
    },

    onPlaybackEnd(cb: () => void) {
      endListeners.add(cb);
      return () => {
        endListeners.delete(cb);
      };
    },
  };
}
```

### 3b. 适配器测试 `__tests__/browserRecorder.test.ts`

真实实现是对浏览器全局对象的薄适配器,测试 mock 全局(`MediaRecorder`、`getUserMedia`、`Audio`、`URL.createObjectURL`),只断言适配器正确驱动它们——绝不测真实浏览器行为。

```ts
import { createBrowserRecorder } from '../src/audio/browserRecorder';

const tracks = [{ stop: jest.fn() }];
const fakeStream = { getTracks: () => tracks } as unknown as MediaStream;

class FakeMediaRecorder {
  static last: FakeMediaRecorder | null = null;
  ondataavailable: ((e: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  mimeType = 'audio/webm';
  start = jest.fn();
  stop = jest.fn(() => {
    this.onstop?.();
  });
  constructor(public stream: MediaStream) {
    FakeMediaRecorder.last = this;
  }
}

class FakeAudio {
  static last: FakeAudio | null = null;
  onended: (() => void) | null = null;
  play = jest.fn(async () => {});
  pause = jest.fn();
  constructor(public src: string) {
    FakeAudio.last = this;
  }
}

beforeEach(() => {
  jest.clearAllMocks();
  (globalThis as Record<string, unknown>).MediaRecorder = FakeMediaRecorder;
  (globalThis as Record<string, unknown>).Audio = FakeAudio;
  URL.createObjectURL = jest.fn(() => 'blob:recording');
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: { getUserMedia: jest.fn(async () => fakeStream) },
  });
});

test('startRecording 申请麦克风并启动 MediaRecorder', async () => {
  await createBrowserRecorder().startRecording();
  expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({ audio: true });
  expect(FakeMediaRecorder.last!.start).toHaveBeenCalled();
});

test('stopRecording 解析为 object URL 并释放麦克风', async () => {
  const recorder = createBrowserRecorder();
  await recorder.startRecording();
  await expect(recorder.stopRecording()).resolves.toBe('blob:recording');
  expect(tracks[0].stop).toHaveBeenCalled();
});

test('startPlayback 播放 uri;onPlaybackEnd 订阅与退订', async () => {
  const recorder = createBrowserRecorder();
  const cb = jest.fn();
  const unsubscribe = recorder.onPlaybackEnd!(cb);

  await recorder.startPlayback('blob:recording');
  expect(FakeAudio.last!.src).toBe('blob:recording');
  expect(FakeAudio.last!.play).toHaveBeenCalled();

  FakeAudio.last!.onended!();
  expect(cb).toHaveBeenCalledTimes(1);

  unsubscribe();
  FakeAudio.last!.onended!();
  expect(cb).toHaveBeenCalledTimes(1);
});
```

### 4. 权限接口 `src/audio/audioPermissions.ts`(接口 + 模拟实现)

权限和其他副作用一样,走与 recorder 相同的模式:接口 + 模拟实现放一个文件,真实适配器**单独成文件**(4b)。接口文件**不触碰任何浏览器全局对象**——引用 `MicrophonePermissions` 类型或测试桩在任何测试环境都安全。Hook 通过注入接收它,绝不直接 import 浏览器实现。

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

### 4b. 浏览器实现 `src/audio/browserMicrophonePermissions.ts`

> ⚠️ **浏览器兼容性提示。** `navigator.permissions.query({ name: 'microphone' })` 并非处处可用(较旧的 Safari/Firefox)。不可用时 `check()` 退化为 `'unknown'`,且持久拒绝无法与一次性拒绝区分(`'blocked'` 退化为 `'denied'`)。`request()` 在所有支持 `getUserMedia` 的环境都可用。浏览器无法以编程方式打开站点设置,所以 `promptOpenSettings()` 只能展示引导文案。

```ts
import type { PermissionStatus } from './audioLogic';
import type { MicrophonePermissions } from './audioPermissions';

export type BrowserMicrophonePermissionsOptions = {
  blockedMessage?: string;
};

const DEFAULT_BLOCKED_MESSAGE =
  '麦克风访问已被禁用。请在浏览器的站点设置中为本站开启麦克风权限后重试。';

async function queryState(): Promise<PermissionState | null> {
  if (!navigator.permissions?.query) {
    return null; // Permissions API 不可用——见上方提示
  }
  try {
    const status = await navigator.permissions.query({
      name: 'microphone' as PermissionName,
    });
    return status.state;
  } catch {
    return null;
  }
}

export function createBrowserMicrophonePermissions(
  options: BrowserMicrophonePermissionsOptions = {},
): MicrophonePermissions {
  const blockedMessage = options.blockedMessage ?? DEFAULT_BLOCKED_MESSAGE;

  return {
    async check(): Promise<PermissionStatus> {
      const state = await queryState();
      if (state === 'granted') {
        return 'granted';
      }
      if (state === 'denied') {
        return 'denied';
      }
      return 'unknown'; // 'prompt' 或 Permissions API 不可用
    },

    async request(): Promise<PermissionStatus> {
      try {
        const probe = await navigator.mediaDevices.getUserMedia({ audio: true });
        probe.getTracks().forEach(track => track.stop()); // 仅探测权限——立即释放
        return 'granted';
      } catch {
        // 持久(被记住的)拒绝在 Permissions API 中表现为 'denied',
        // 且再次 request 不会弹窗——这就是 'blocked'。
        const state = await queryState();
        return state === 'denied' ? 'blocked' : 'denied';
      }
    },

    promptOpenSettings() {
      // 浏览器无法编程打开站点设置——只展示引导。
      // 何时调用由 Hook 决定(blocked 时);request() 自己绝不弹窗,
      // 因此用户不会被提示两次。
      window.alert(blockedMessage);
    },
  };
}
```

### 4c. 浏览器权限测试 `__tests__/browserMicrophonePermissions.test.ts`

与 recorder 不同,这个适配器含真实**映射逻辑**(探测后立即释放、持久拒绝 → `blocked`、无 Permissions API 时降级),所以它的测试要断言映射——依然 mock 全局对象。

```ts
import { createBrowserMicrophonePermissions } from '../src/audio/browserMicrophonePermissions';

function setGetUserMedia(getUserMedia: jest.Mock) {
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: { getUserMedia },
  });
}

function setPermissionsQuery(query: jest.Mock | undefined) {
  Object.defineProperty(navigator, 'permissions', {
    configurable: true,
    value: query ? { query } : undefined,
  });
}

test('request:getUserMedia 成功 → granted,探测流被释放', async () => {
  const stop = jest.fn();
  setGetUserMedia(jest.fn(async () => ({ getTracks: () => [{ stop }] })));
  await expect(createBrowserMicrophonePermissions().request()).resolves.toBe('granted');
  expect(stop).toHaveBeenCalled();
});

test('request:被拒 + Permissions API 报 denied → blocked', async () => {
  setGetUserMedia(jest.fn(async () => {
    throw new DOMException('Permission denied', 'NotAllowedError');
  }));
  setPermissionsQuery(jest.fn(async () => ({ state: 'denied' })));
  await expect(createBrowserMicrophonePermissions().request()).resolves.toBe('blocked');
});

test('request:被拒且无 Permissions API → 降级为 denied', async () => {
  setGetUserMedia(jest.fn(async () => {
    throw new DOMException('Permission denied', 'NotAllowedError');
  }));
  setPermissionsQuery(undefined);
  await expect(createBrowserMicrophonePermissions().request()).resolves.toBe('denied');
});

test('check 正确映射 granted / denied / prompt', async () => {
  setPermissionsQuery(jest.fn(async () => ({ state: 'granted' })));
  await expect(createBrowserMicrophonePermissions().check()).resolves.toBe('granted');
  setPermissionsQuery(jest.fn(async () => ({ state: 'denied' })));
  await expect(createBrowserMicrophonePermissions().check()).resolves.toBe('denied');
  setPermissionsQuery(jest.fn(async () => ({ state: 'prompt' })));
  await expect(createBrowserMicrophonePermissions().check()).resolves.toBe('unknown');
});

test('promptOpenSettings 展示引导(浏览器无法打开设置)', () => {
  const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {});
  createBrowserMicrophonePermissions().promptOpenSettings();
  expect(alertSpy).toHaveBeenCalled();
  alertSpy.mockRestore();
});
```

### 5. Hook `src/audio/useAudio.ts`(useReducer + 编排 IO + dispatch)

Hook 持有 `useReducer`,通过注入依赖做 IO,然后 dispatch 一个事件——它从不自己决定下一个状态。动作回调从 ref 读 state(ref 在 effect 中赋值,绝不在渲染期写),保持稳定;start 动作有重入守护。时长 tick 在 `useEffect` 中**派生自状态**,所以任何离开 `recording` 的路径——停止、设备失败、卸载——都会自动清理它。返回的 API 经 `useMemo`。此文件与 React Native 版完全相同。

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
import { act, renderHook } from '@testing-library/react';
import { useAudio } from '../src/audio/useAudio';
import {
  createSimulatedPermissions,
  type MicrophonePermissions,
} from '../src/audio/audioPermissions';
import type { Recorder } from '../src/audio/audioRecorder';

function baseRecorder(over: Partial<Recorder> = {}): Recorder {
  return {
    startRecording: jest.fn(async () => {}),
    stopRecording: jest.fn(async () => 'blob:r'),
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

### 6. 视图 `src/audio/AudioView.tsx`(纯展示 + data-testid + 原生按钮)

```tsx
import type { CSSProperties } from 'react';
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
    <div style={styles.container}>
      <p data-testid="audio-status" style={styles.status}>状态: {labelFor(status)}</p>
      <p data-testid="audio-permission" style={styles.muted}>权限: {labelForPermission(permission)}</p>
      <p data-testid="audio-duration" style={styles.duration}>{formatDuration(durationMs)}</p>
      <p data-testid="audio-uri" style={styles.uri}>{uri ?? '尚未录音'}</p>
      {error !== null ? (
        <p data-testid="audio-error" style={styles.error}>{error.message}</p>
      ) : null}
      <div style={styles.row}>
        <ActionButton testID="audio-start" label={status === 'recorded' ? '重新录音' : '开始录音'} disabled={!canStart} onClick={onStart} />
        <ActionButton testID="audio-stop" label="停止录音" disabled={!canStop} onClick={onStop} />
      </div>
      <div style={styles.row}>
        <ActionButton testID="audio-play" label="播放" disabled={!canPlay} onClick={onPlay} />
        <ActionButton testID="audio-stop-play" label="停止播放" disabled={!canStopPlay} onClick={onStopPlay} />
      </div>
    </div>
  );
}

type ActionButtonProps = {
  testID: string;
  label: string;
  disabled: boolean;
  onClick: () => void;
};

function ActionButton({ testID, label, disabled, onClick }: ActionButtonProps) {
  return (
    <button
      type="button"
      data-testid={testID}
      disabled={disabled}
      onClick={onClick}
      style={{ ...styles.btn, ...(disabled ? styles.btnDisabled : undefined) }}
    >
      {label}
    </button>
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

const styles: Record<string, CSSProperties> = {
  container: { display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 16, gap: 12 },
  status: { fontWeight: 600 },
  muted: { color: '#888' },
  duration: { fontWeight: 600 },
  uri: { color: '#888', maxWidth: 320, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  error: { color: '#c0392b' },
  row: { display: 'flex', gap: 16 },
  btn: { padding: '10px 16px', borderRadius: 8, border: 'none', background: '#222', color: 'white', fontWeight: 600, cursor: 'pointer' },
  btnDisabled: { background: '#bbb', cursor: 'default' },
};
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
import { useMemo } from 'react';
import { AudioScreen } from './src/audio/AudioScreen';
import { createBrowserMicrophonePermissions } from './src/audio/browserMicrophonePermissions';
import { createBrowserRecorder } from './src/audio/browserRecorder';

export default function App() {
  const recorder = useMemo(() => createBrowserRecorder(), []);
  const permissions = useMemo(() => createBrowserMicrophonePermissions(), []);

  return <AudioScreen recorder={recorder} permissions={permissions} />;
}
```
