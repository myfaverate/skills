---
name: rn-layered-feature reference code
description: Complete code examples for the rn-layered-feature architecture, with src/audio (pure reducer state machine + injected side effects) as the canonical implementation and src/counter as the contrast case.
---

# Reference code

Two worked examples, simplest first:

- **`counter`** — the minimal form of the layering: pure logic + guard, hook, view, container, with no side effects and no reducer (trivial state needs none). Start here to see the shape.
- **`audio`** — the **canonical example**: a real state machine (pure reducer), injected side effects (recorder + permissions), timers, typed errors. Build new feature modules file-by-file against it.

> Note: UI string literals are shown in English here; [EXAMPLES.zh.md](EXAMPLES.zh.md) is the Chinese-language version.

> Sections show each implementation file followed by its test (`1` → `1t`) for reading flow only — **the development order is the reverse**: write the test first, watch it fail, then implement (see the build checklist in SKILL.md).

## Contents

Read top-to-bottom for the full build, or jump to a module and search the file
name. Each file is shown followed by its test (`N` → `Nt` / `Nb`); the build
order is the reverse — test first (see the build checklist in SKILL.md).

**[`counter` — minimal layering](#minimal-example-the-counter-module)** (no side effects, `useState` + pure functions): `counterLogic.ts` + test · `useCounter.ts` + test · `CounterView.tsx` + test · `Counter.tsx` + test.

**[`audio` — canonical full example](#canonical-example-the-audio-module)** (pure reducer, injected side effects, timers, typed errors):
- `audioLogic.ts` (logic + reducer) + test
- `audioRecorder.ts` (interface) · `nitroSoundRecorder.ts` (real adapter) + test
- `audioPermissions.ts` (interface) · `nativeMicrophonePermissions.ts` (native impl) + test
- `useAudio.ts` (hook) + test
- `AudioView.tsx` (view) · `AudioScreen.tsx` (container) · `App.tsx` (composition root)

## Minimal example: the counter module

No side effects, so no dependency injection; state is a single number, so `useState` + pure functions is enough (promote to a reducer only when transitions get real — see `audio`). It still follows every other rule: pure logic with a guard, a props-only view using `Pressable` with `testID` + accessibility, a thin container, and a test at each layer.

### 1. Pure logic `src/counter/counterLogic.ts`

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

// guard: is the decrement action available? (count is clamped at MIN_COUNT)
export function canDecrement(count: number): boolean {
  return count > MIN_COUNT;
}

export function isEven(count: number): boolean {
  return count % 2 === 0;
}
```

### 1t. Logic test `__tests__/counterLogic.test.ts`

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

describe('counterLogic (pure)', () => {
  test('increment adds one', () => {
    expect(increment(0)).toBe(1);
    expect(increment(41)).toBe(42);
  });
  test('decrement subtracts one but clamps at MIN_COUNT', () => {
    expect(decrement(2)).toBe(1);
    expect(decrement(MIN_COUNT)).toBe(MIN_COUNT);
  });
  test('reset returns INITIAL_COUNT', () => {
    expect(reset()).toBe(INITIAL_COUNT);
  });
  test('canDecrement is false at the floor', () => {
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

### 2t. Hook test `__tests__/useCounter.test.ts`

```ts
import { act, renderHook } from '@testing-library/react-native';
import { useCounter } from '../src/counter/useCounter';

test('counts up, clamps at zero, exposes canDecrement, resets', () => {
  const { result } = renderHook(() => useCounter());
  expect(result.current.count).toBe(0);
  expect(result.current.canDecrement).toBe(false);

  act(() => result.current.increment());
  expect(result.current.count).toBe(1);
  expect(result.current.canDecrement).toBe(true);

  act(() => result.current.decrement());
  expect(result.current.count).toBe(0);

  act(() => result.current.decrement()); // clamped, no throw
  expect(result.current.count).toBe(0);

  act(() => result.current.reset());
  expect(result.current.count).toBe(0);
});
```

### 3. View `src/counter/CounterView.tsx`

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

### 3t. View test `__tests__/CounterView.test.tsx`

```tsx
import { fireEvent, render, screen } from '@testing-library/react-native';
import { CounterView } from '../src/counter/CounterView';

const noop = () => {};

test('renders count and disables minus when canDecrement is false', () => {
  render(<CounterView count={0} canDecrement={false} onIncrement={noop} onDecrement={noop} onReset={noop} />);
  expect(screen.getByTestId('count')).toHaveTextContent('Count: 0');
  expect(screen.getByTestId('dec')).toBeDisabled();
  expect(screen.getByTestId('inc')).toBeEnabled();
});

test('fires callbacks; a disabled minus does not fire', () => {
  const onIncrement = jest.fn();
  const onDecrement = jest.fn();
  const onReset = jest.fn();

  const { rerender } = render(
    <CounterView count={0} canDecrement={false} onIncrement={onIncrement} onDecrement={onDecrement} onReset={onReset} />,
  );

  fireEvent.press(screen.getByTestId('inc'));
  fireEvent.press(screen.getByTestId('reset'));
  fireEvent.press(screen.getByTestId('dec')); // disabled -> ignored
  expect(onIncrement).toHaveBeenCalledTimes(1);
  expect(onReset).toHaveBeenCalledTimes(1);
  expect(onDecrement).not.toHaveBeenCalled();

  rerender(<CounterView count={1} canDecrement={true} onIncrement={onIncrement} onDecrement={onDecrement} onReset={onReset} />);
  fireEvent.press(screen.getByTestId('dec'));
  expect(onDecrement).toHaveBeenCalledTimes(1);
});
```

### 4. Container `src/counter/Counter.tsx`

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

### 4t. Container integration test `__tests__/Counter.test.tsx`

```tsx
import { fireEvent, render, screen } from '@testing-library/react-native';
import { Counter } from '../src/counter/Counter';

test('user counts up and resets', () => {
  render(<Counter />);
  expect(screen.getByTestId('count')).toHaveTextContent('Count: 0');
  fireEvent.press(screen.getByTestId('inc'));
  fireEvent.press(screen.getByTestId('inc'));
  expect(screen.getByTestId('count')).toHaveTextContent('Count: 2');
  fireEvent.press(screen.getByTestId('reset'));
  expect(screen.getByTestId('count')).toHaveTextContent('Count: 0');
});

test('count never goes negative (minus disabled at zero)', () => {
  render(<Counter />);
  fireEvent.press(screen.getByTestId('dec'));
  expect(screen.getByTestId('count')).toHaveTextContent('Count: 0');
});
```

## Canonical example: the audio module

### 1. Pure logic + reducer `src/audio/audioLogic.ts`

The whole state machine lives here: state/event types, guards, and the pure `audioReducer`. No React, no side effects.

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

// --- guards (pure predicates) ---

// UI-availability guard: should the start button be enabled?
// Deliberately ignores permission — pressing start triggers the permission request.
export function canRequestStart(status: RecordingStatus): boolean {
  return status === 'idle' || status === 'recorded';
}

// Full-precondition guard: may recording actually begin?
// The hook re-checks this inside start() after resolving permission.
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

// --- reducer (pure transition; illegal transitions are no-ops) ---

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
      // A device failure aborts recording back to idle; other kinds keep the state.
      return {
        ...state,
        error: event.error,
        status: event.error.kind === 'device' ? 'idle' : state.status,
      };
  }
}
```

### 1t. Logic test `__tests__/audioLogic.test.ts`

The heaviest test file and the cheapest to run: pure, synchronous, no React. Guards get both branches and boundaries; the reducer gets **every event from every relevant source state, including no-op illegal transitions**.

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

describe('guards', () => {
  test.each([
    ['idle', true],
    ['recorded', true],
    ['recording', false],
    ['playing', false],
  ] as const)('canRequestStart(%s) === %s', (status, expected) => {
    expect(canRequestStart(status)).toBe(expected);
  });

  test('canStartRecording needs granted permission AND a startable status', () => {
    expect(canStartRecording('granted', 'idle')).toBe(true);
    expect(canStartRecording('denied', 'idle')).toBe(false);
    expect(canStartRecording('granted', 'recording')).toBe(false);
  });

  test('canPlay needs recorded status AND a uri', () => {
    expect(canPlay('recorded', 'file://r.m4a')).toBe(true);
    expect(canPlay('recorded', null)).toBe(false);
    expect(canPlay('idle', 'file://r.m4a')).toBe(false);
  });
});

describe('audioReducer', () => {
  test('recordingStarted resets duration/uri/error (re-record case)', () => {
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
    'recordingStarted while %s is a no-op',
    status => {
      const s = state({ status });
      expect(audioReducer(s, { type: 'recordingStarted' })).toBe(s);
    },
  );

  test('tick updates duration only while recording', () => {
    const recording = state({ status: 'recording' });
    expect(audioReducer(recording, { type: 'tick', durationMs: 1200 }).durationMs).toBe(1200);
    const idle = state();
    expect(audioReducer(idle, { type: 'tick', durationMs: 1200 })).toBe(idle);
  });

  test('recordingStopped stores the uri; no-op when not recording', () => {
    const next = audioReducer(state({ status: 'recording' }), {
      type: 'recordingStopped',
      uri: 'file://r.m4a',
    });
    expect(next.status).toBe('recorded');
    expect(next.uri).toBe('file://r.m4a');
    const idle = state();
    expect(audioReducer(idle, { type: 'recordingStopped', uri: 'file://r.m4a' })).toBe(idle);
  });

  test('playback lifecycle: started only from recorded+uri, ended only from playing', () => {
    const recorded = state({ status: 'recorded', uri: 'file://r.m4a' });
    expect(audioReducer(recorded, { type: 'playbackStarted' }).status).toBe('playing');
    expect(audioReducer(state({ status: 'recorded', uri: null }), { type: 'playbackStarted' }).status).toBe('recorded');
    expect(audioReducer(state({ status: 'playing', uri: 'file://r.m4a' }), { type: 'playbackEnded' }).status).toBe('recorded');
    expect(audioReducer(recorded, { type: 'playbackEnded' })).toBe(recorded);
  });

  test('failed: device errors abort to idle, playback errors keep the state', () => {
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

### 2. Dependency interface `src/audio/audioRecorder.ts` (interface + simulated impl)

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

### 3. Real implementation `src/audio/nitroSoundRecorder.ts`

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

### 3b. Adapter delegation test `__tests__/nitroSoundRecorder.test.ts`

The real implementation is a thin adapter, so it gets a **delegation test**: mock the native library and assert forwarding only — never native behavior.

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

test('stopRecording delegates and returns the saved uri', async () => {
  (Sound.stopRecorder as jest.Mock).mockResolvedValue('file://r.m4a');
  await expect(createNitroSoundRecorder().stopRecording()).resolves.toBe(
    'file://r.m4a',
  );
});

test('startPlayback forwards the uri', async () => {
  await createNitroSoundRecorder().startPlayback('file://r.m4a');
  expect(Sound.startPlayer).toHaveBeenCalledWith('file://r.m4a');
});

test('onPlaybackEnd subscribes and the returned fn unsubscribes', () => {
  const unsubscribe = createNitroSoundRecorder().onPlaybackEnd!(() => {});
  expect(Sound.addPlaybackEndListener).toHaveBeenCalled();
  unsubscribe();
  expect(Sound.removePlaybackEndListener).toHaveBeenCalled();
});
```

### 4. Permissions interface `src/audio/audioPermissions.ts` (interface + simulated impl)

Permissions are a side effect like any other, so they follow the same pattern as the recorder: interface + simulated impl in one file, the real adapter in **its own file** (4b). The interface file has **zero `react-native` imports** — importing the `MicrophonePermissions` type never drags in a native module. The hook receives it by injection and never imports the native impl directly.

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

### 4b. Native implementation `src/audio/nativeMicrophonePermissions.ts`

> ⚠️ **Android-only reference.** On iOS this placeholder resolves `'granted'` without asking. Real iOS support needs [`react-native-permissions`](https://github.com/zoontek/react-native-permissions) (`PERMISSIONS.IOS.MICROPHONE`) — keep the interface, swap the implementation.

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
  rationaleTitle: 'Microphone permission',
  rationaleMessage: 'Microphone access is required to record audio',
  blockedTitle: 'Permission denied',
  blockedMessage: 'Please enable microphone access in Settings',
  openSettingsLabel: 'Open Settings',
  cancelLabel: 'Cancel',
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
      return 'unknown'; // iOS placeholder — see warning above
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
            buttonPositive: 'Allow',
            buttonNegative: opts.cancelLabel,
          },
        );

        if (result === PermissionsAndroid.RESULTS.GRANTED) {
          return 'granted';
        }
        if (result === PermissionsAndroid.RESULTS.NEVER_ASK_AGAIN) {
          // No prompt here — the hook calls promptOpenSettings() on 'blocked',
          // so prompting from request() too would alert the user twice.
          return 'blocked';
        }
        return 'denied';
      }

      return 'granted'; // iOS placeholder — see warning above
    },

    promptOpenSettings,
  };
}
```

### 4c. Native permissions test `__tests__/nativeMicrophonePermissions.test.ts`

Unlike the recorder, this adapter contains real **mapping logic** (already-granted short-circuit, `NEVER_ASK_AGAIN` → `blocked`), so its test asserts the mapping — still with the native modules mocked.

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

test('request short-circuits to granted when already granted (no dialog)', async () => {
  check.mockResolvedValue(true);
  await expect(createNativeMicrophonePermissions().request()).resolves.toBe('granted');
  expect(request).not.toHaveBeenCalled();
});

test('request maps GRANTED and denied results', async () => {
  check.mockResolvedValue(false);
  request.mockResolvedValueOnce('granted');
  await expect(createNativeMicrophonePermissions().request()).resolves.toBe('granted');
  request.mockResolvedValueOnce('denied');
  await expect(createNativeMicrophonePermissions().request()).resolves.toBe('denied');
});

test('NEVER_ASK_AGAIN maps to blocked without auto-prompting (the hook prompts)', async () => {
  check.mockResolvedValue(false);
  request.mockResolvedValue('never_ask_again');
  await expect(createNativeMicrophonePermissions().request()).resolves.toBe('blocked');
  expect(Alert.alert).not.toHaveBeenCalled();
});

test('promptOpenSettings shows the settings alert', () => {
  createNativeMicrophonePermissions().promptOpenSettings();
  expect(Alert.alert).toHaveBeenCalled();
});
```

### 5. Hook `src/audio/useAudio.ts` (useReducer + IO orchestration + dispatch)

The hook owns `useReducer` and does IO through the injected dependencies, then dispatches an event — it never decides the next state itself. Action callbacks read state from a ref (assigned in an effect, never during render) so they stay stable, and the start action is guarded against re-entrancy. The duration tick is **derived from state** in a `useEffect`, so any exit from `recording` — stop, device failure, unmount — clears it automatically. The returned API is memoized.

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
  recorder: Recorder;                 // required — no silent default
  permissions: MicrophonePermissions; // required — permissions are a side effect too
  tickMs?: number;
};

export function useAudio(options: UseAudioOptions): AudioApi {
  const { recorder, permissions } = options;
  const tickMs = options.tickMs ?? 250;

  const [state, dispatch] = useReducer(audioReducer, initialAudioState);

  // Mirror state into a ref so action callbacks can read the latest value
  // without listing state in their deps (keeps them stable). Assigned in an
  // effect — writing a ref during render breaks the Rules of React.
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

  // Tick interval derived from state, not started inside actions: every
  // exit from 'recording' (stop, device failure, unmount) clears it.
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

### 5b. Hook test `__tests__/useAudio.test.ts` (stubs + fake timers + re-entrancy)

Test only what the hook adds on top of the reducer. The reducer's truth table is already covered in `audioLogic.test.ts`.

> ⚠️ **Create the injected dependencies *outside* the `renderHook` callback.** If you write `renderHook(() => useAudio({ permissions: createSimulatedPermissions('granted') }))`, a new `permissions` object is created on every render, so the mount effect's `[permissions]` dependency changes each render and re-runs forever — the test hangs. Hold the stubs in stable variables and close over them.

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

test('duration ticks while recording (fake timers)', async () => {
  jest.useFakeTimers();
  try {
    const recorder = baseRecorder();
    const permissions = createSimulatedPermissions('granted'); // stable, outside render
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

test('double start only records once (re-entrancy guarded)', async () => {
  let resolveStart!: () => void;
  const recorder = baseRecorder({
    startRecording: jest.fn(() => new Promise<void>(r => (resolveStart = r))),
  });
  const permissions = createSimulatedPermissions('granted');
  const { result } = renderHook(() => useAudio({ recorder, permissions }));

  await act(async () => {
    result.current.start(); // holds inside the pending startRecording
    await result.current.start(); // second call bails out immediately
    resolveStart();
  });

  expect(recorder.startRecording).toHaveBeenCalledTimes(1);
});

test('a device failure surfaces a typed error and returns to idle', async () => {
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

test('blocked permission: requests once, prompts settings, never records', async () => {
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

### 6. View `src/audio/AudioView.tsx` (pure presentation + testID + a11y + Pressable)

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
      <Text testID="audio-status" style={styles.status}>Status: {labelFor(status)}</Text>
      <Text testID="audio-permission" style={styles.muted}>Permission: {labelForPermission(permission)}</Text>
      <Text testID="audio-duration" style={styles.duration}>{formatDuration(durationMs)}</Text>
      <Text testID="audio-uri" style={styles.muted} numberOfLines={1}>{uri ?? 'No recording yet'}</Text>
      {error !== null ? (
        <Text testID="audio-error" style={styles.error}>{error.message}</Text>
      ) : null}
      <View style={styles.row}>
        <ActionButton testID="audio-start" label={status === 'recorded' ? 'Re-record' : 'Start recording'} disabled={!canStart} onPress={onStart} />
        <ActionButton testID="audio-stop" label="Stop recording" disabled={!canStop} onPress={onStop} />
      </View>
      <View style={styles.row}>
        <ActionButton testID="audio-play" label="Play" disabled={!canPlay} onPress={onPlay} />
        <ActionButton testID="audio-stop-play" label="Stop playback" disabled={!canStopPlay} onPress={onStopPlay} />
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
    case 'idle': return 'Idle';
    case 'recording': return 'Recording';
    case 'recorded': return 'Recorded';
    case 'playing': return 'Playing';
  }
}

function labelForPermission(p: PermissionStatus): string {
  switch (p) {
    case 'granted': return 'Granted';
    case 'denied': return 'Denied';
    case 'blocked': return 'Blocked';
    case 'unknown': return 'Unknown';
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

### 7. Container `src/audio/AudioScreen.tsx` (thin glue layer)

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

### 8. Wire the real implementations at the composition root `App.tsx`

The real implementations are injected **once**, here — nowhere else imports them.

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

