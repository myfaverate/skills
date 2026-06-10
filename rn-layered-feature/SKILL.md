---
name: rn-layered-feature
description: Standard architecture for adding a React Native feature module in this project — pure-logic / hook / view three-layer separation + dependency injection, with mandatory test-first TDD. Use when adding a new feature module under src/, creating screens, hooks, or any component that touches side effects (recording, network, storage, timers), or when asked to follow the project's architecture/conventions. Enforces test-first (red-green-refactor) development.
metadata:
  version: '1.0.0'
---

# RN Layered Feature Architecture

Every feature module in this project (see `src/audio`, `src/counter`) follows the same layering. Build new features this way to stay consistent and testable.

> ⚠️ **Mandatory TDD: all development in this architecture is test-first.** Before writing any implementation file, write detailed test cases for that layer and confirm they fail (red), then write the minimum implementation to make them pass (green), then refactor (stay green). **Never write the implementation first and backfill tests.** Use the `tdd` skill to run the red-green-refactor loop.

> A Chinese version of this skill is kept at [SKILL.zh.md](SKILL.zh.md) / [references/EXAMPLES.zh.md](references/EXAMPLES.zh.md) as a backup.

> Full file-by-file code examples are in [references/EXAMPLES.md](references/EXAMPLES.md) (audio is the canonical implementation, counter is the contrast case).

## Four files, each with one job

| File | Role | Rules |
|---|---|---|
| `xxxLogic.ts` | Pure logic | Pure functions only: state-machine guards (`canXxx`), computation, formatting. **No React, no side effects, no platform API imports.** |
| `useXxx.ts` | Hook | Owns `useState`/`useRef`/`useEffect`, orchestrates side effects, calls logic and the injected dependency. Returns a flat API object (state + `canXxx` booleans + action functions). |
| `XxxView.tsx` | View | Pure presentation, **props-only**. No business logic, no hooks, no side effects. Every interactive element has a `testID`. |
| `Xxx.tsx` / `XxxScreen.tsx` | Container | Ultra-thin glue: calls `useXxx()` and spreads the result down into `XxxView`. |

## Dependency injection (the side-effect boundary)

For any capability that touches native/IO (recording, network, storage…), define an interface first, then provide both a real and a simulated implementation:

- Interface: the `Recorder` type in `audioRecorder.ts`
- Real implementation: `nitroSoundRecorder.ts` (`createNitroSoundRecorder`)
- Simulated implementation: `createSimulatedRecorder` (for tests and device-less environments)

The hook receives the dependency via options and **defaults to the simulated implementation**; `App.tsx` injects the real one at the root:

```ts
export function useAudio(options: UseAudioOptions = {}): AudioApi {
  const recorder = useMemo(
    () => options.recorder ?? createSimulatedRecorder(),
    [options.recorder],
  );
  // ...
}
```

Benefit: View / Hook / Logic can all be unit-tested off-device by injecting a stub to assert behavior.

## State-machine conventions

- Define a state union type in the logic layer (e.g. `RecordingStatus = 'idle' | 'recording' | ...`).
- Whether each action is available is derived by pure guard functions in the logic layer (`canStopRecording(status)`). **Do not write conditionals in the View.**
- The hook computes these guards into booleans (`canStart`/`canStop`…) and passes them to the View; bind a button's `disabled` directly to them.

## Testing conventions (test-first)

Write tests before the implementation at every layer; tests live in the root `__tests__/`:
- `xxxLogic.test.ts` — pure functions, assert inputs/outputs directly. Cover both true/false branches and boundary values of every state-machine guard.
- `useXxx.test.ts` — use `renderHook` from `@testing-library/react-native`, inject the `createSimulatedXxx` stub, assert state transitions and derived `canXxx` values.
- `XxxView.test.tsx` — render and assert by `testID`: text, `disabled` state, and that `onPress` callbacks fire.
- Integration: drive `XxxScreen` with the simulated dependency to exercise the full user path (see `AudioScreen.test.tsx`).

Test cases must be **detailed**: every state branch, every `canXxx` guard, and every error path (`recorder` throws → `error` is set) needs an assertion — not just the happy path.

## Build checklist (red-green-refactor)

When adding a feature `foo`, **each step is test-first (red) → implementation (green) → refactor**:

1. `__tests__/fooLogic.test.ts` → `src/foo/fooLogic.ts` — state types + pure guards/formatting.
2. (If it has side effects) define a `Recorder`-style interface and prepare a `createSimulatedXxx` stub in `__tests__` → `src/foo/fooClient.ts`; the real implementation goes in its own file (the real impl needs no unit test of its own — the interface contract guarantees it).
3. `__tests__/useFoo.test.ts` → `src/foo/useFoo.ts` — inject the stub, assert state transitions and derived booleans.
4. `__tests__/FooView.test.tsx` → `src/foo/FooView.tsx` — pure presentation, props-driven, elements carry `testID`.
5. `src/foo/Foo.tsx` — thin container (logic is already covered by the lower-layer tests; the container itself only needs integration coverage).
6. `__tests__/FooScreen.test.tsx` — drive the end-to-end user path with the simulated dependency.

Keep `npm test` green throughout; before committing, make sure each new test genuinely went red before it went green.

## Anti-pattern (do not copy)

`src/counter` is an early template example; its `CounterView` uses `<Text onPress>` as a button — **use `Pressable` instead** (see `ActionButton` in `AudioView`). For new code, follow the `audio` module.
