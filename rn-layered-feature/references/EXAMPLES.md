---
name: rn-layered-feature reference code
description: Complete code examples for the rn-layered-feature architecture, with src/audio as the canonical implementation and src/counter as the contrast case.
---

# Reference code

The `audio` module is the **canonical example** of this architecture. Build new features file-by-file against the code below. `counter` is at the end (an older template, contrast only).

> Note: UI string literals below are shown in English for this reference. The actual app source uses Chinese copy — see [EXAMPLES.zh.md](EXAMPLES.zh.md) for the verbatim original.

## Canonical example: the audio module

### 1. Pure logic `src/audio/audioLogic.ts`

```ts
export type RecordingStatus = 'idle' | 'recording' | 'recorded' | 'playing';

export type PermissionStatus = 'unknown' | 'granted' | 'denied' | 'blocked';

export function canStartRecording(
  permission: PermissionStatus,
  status: RecordingStatus,
): boolean {
  return permission === 'granted' && (status === 'idle' || status === 'recorded');
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

### 4. Permissions `src/audio/audioPermissions.ts` (configurable copy + "open settings" on blocked)

```ts
import { Alert, Linking, PermissionsAndroid, Platform } from 'react-native';
import type { PermissionStatus } from './audioLogic';

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

export async function checkMicrophonePermission(): Promise<PermissionStatus> {
  if (Platform.OS === 'android') {
    const granted = await PermissionsAndroid.check(
      PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
    );
    return granted ? 'granted' : 'denied';
  }
  return 'unknown';
}

export async function requestMicrophonePermission(
  options: RequestMicrophoneOptions = {},
): Promise<PermissionStatus> {
  const opts = { ...DEFAULTS, ...options };

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
      promptOpenSettings(opts);
      return 'blocked';
    }
    return 'denied';
  }

  return 'granted';
}

export function promptOpenSettings(options: RequestMicrophoneOptions = {}): void {
  const opts = { ...DEFAULTS, ...options };
  Alert.alert(opts.blockedTitle, opts.blockedMessage, [
    { text: opts.cancelLabel, style: 'cancel' },
    { text: opts.openSettingsLabel, onPress: () => Linking.openSettings() },
  ]);
}
```

### 5. Hook `src/audio/useAudio.ts` (inject dependency + orchestrate side effects + return flat API)

```ts
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  canPlay,
  canStopPlayback,
  canStopRecording,
  type PermissionStatus,
  type RecordingStatus,
} from './audioLogic';
import {
  checkMicrophonePermission,
  promptOpenSettings,
  requestMicrophonePermission,
} from './audioPermissions';
import { createSimulatedRecorder, type Recorder } from './audioRecorder';

export type AudioApi = {
  status: RecordingStatus;
  permission: PermissionStatus;
  durationMs: number;
  uri: string | null;
  error: string | null;
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
  recorder?: Recorder;
  tickMs?: number;
};

export function useAudio(options: UseAudioOptions = {}): AudioApi {
  const recorder = useMemo(
    () => options.recorder ?? createSimulatedRecorder(),
    [options.recorder],
  );
  const tickMs = options.tickMs ?? 250;

  const [status, setStatus] = useState<RecordingStatus>('idle');
  const [permission, setPermission] = useState<PermissionStatus>('unknown');
  const [durationMs, setDurationMs] = useState(0);
  const [uri, setUri] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startedAtRef = useRef<number>(0);

  useEffect(() => {
    let cancelled = false;
    checkMicrophonePermission().then(p => {
      if (!cancelled) {
        setPermission(p);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const clearTick = useCallback(() => {
    if (tickRef.current !== null) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
  }, []);

  useEffect(() => clearTick, [clearTick]);

  useEffect(() => {
    if (!recorder.onPlaybackEnd) {
      return;
    }
    const unsubscribe = recorder.onPlaybackEnd(() => {
      setStatus(prev => (prev === 'playing' ? 'recorded' : prev));
    });
    return unsubscribe;
  }, [recorder]);

  const start = useCallback(async () => {
    setError(null);
    let current = permission;
    if (current !== 'granted') {
      current = await requestMicrophonePermission();
      setPermission(current);
    }
    if (current !== 'granted') {
      if (current === 'blocked') {
        promptOpenSettings();
      }
      return;
    }

    try {
      await recorder.startRecording();
      startedAtRef.current = Date.now();
      setDurationMs(0);
      setUri(null);
      setStatus('recording');
      clearTick();
      tickRef.current = setInterval(() => {
        setDurationMs(Date.now() - startedAtRef.current);
      }, tickMs);
    } catch (e) {
      setError(toMessage(e));
      setStatus('idle');
    }
  }, [permission, recorder, tickMs, clearTick]);

  const stop = useCallback(async () => {
    if (!canStopRecording(status)) {
      return;
    }
    clearTick();
    try {
      const savedUri = await recorder.stopRecording();
      setUri(savedUri);
      setStatus('recorded');
    } catch (e) {
      setError(toMessage(e));
      setStatus('idle');
    }
  }, [status, recorder, clearTick]);

  const play = useCallback(async () => {
    if (!canPlay(status, uri)) {
      return;
    }
    setError(null);
    try {
      await recorder.startPlayback(uri as string);
      setStatus('playing');
    } catch (e) {
      setError(toMessage(e));
    }
  }, [status, uri, recorder]);

  const stopPlay = useCallback(async () => {
    if (!canStopPlayback(status)) {
      return;
    }
    try {
      await recorder.stopPlayback();
      setStatus('recorded');
    } catch (e) {
      setError(toMessage(e));
    }
  }, [status, recorder]);

  return {
    status,
    permission,
    durationMs,
    uri,
    error,
    canStart: status === 'idle' || status === 'recorded',
    canStop: canStopRecording(status),
    canPlay: canPlay(status, uri),
    canStopPlay: canStopPlayback(status),
    start,
    stop,
    play,
    stopPlay,
  };
}

function toMessage(e: unknown): string {
  if (e instanceof Error) {
    return e.message;
  }
  return String(e);
}
```

### 6. View `src/audio/AudioView.tsx` (pure presentation + testID + Pressable)

```tsx
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { formatDuration, type PermissionStatus, type RecordingStatus } from './audioLogic';

export type AudioViewProps = {
  status: RecordingStatus;
  permission: PermissionStatus;
  durationMs: number;
  uri: string | null;
  error: string | null;
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
        <Text testID="audio-error" style={styles.error}>{error}</Text>
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

export function AudioScreen(options: UseAudioOptions = {}) {
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

### 8. Inject the real implementation at the root `App.tsx`

```tsx
import React, { useMemo } from 'react';
import { StatusBar, useColorScheme } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { AudioScreen } from './src/audio/AudioScreen';
import { createNitroSoundRecorder } from './src/audio/nitroSoundRecorder';

function App() {
  const isDarkMode = useColorScheme() === 'dark';
  const recorder = useMemo(() => createNitroSoundRecorder(), []);

  return (
    <SafeAreaProvider>
      <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />
      <AudioScreen recorder={recorder} />
    </SafeAreaProvider>
  );
}

export default App;
```

---

## Contrast (older template): the counter module

`counter` shows the minimal form of the same layering (no side effects, no dependency injection). **Note its View uses `<Text onPress>` as a button, which is an anti-pattern** — new code should use `Pressable` instead (see `ActionButton` above).

### `src/counter/counterLogic.ts`

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

export function isEven(count: number): boolean {
  return count % 2 === 0;
}
```

### `src/counter/useCounter.ts`

```ts
import { useCallback, useState } from 'react';
import { INITIAL_COUNT, decrement, increment, reset } from './counterLogic';

export type CounterApi = {
  count: number;
  increment: () => void;
  decrement: () => void;
  reset: () => void;
};

export function useCounter(initial: number = INITIAL_COUNT): CounterApi {
  const [count, setCount] = useState(initial);

  return {
    count,
    increment: useCallback(() => setCount(increment), []),
    decrement: useCallback(() => setCount(decrement), []),
    reset: useCallback(() => setCount(reset()), []),
  };
}
```

### `src/counter/Counter.tsx`

```tsx
import { CounterView } from './CounterView';
import { useCounter } from './useCounter';

export function Counter() {
  const { count, increment, decrement, reset } = useCounter();
  return (
    <CounterView
      count={count}
      onIncrement={increment}
      onDecrement={decrement}
      onReset={reset}
    />
  );
}
```
