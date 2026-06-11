---
name: react-layered-feature
description: Layered architecture for React (web) feature modules — pure logic+reducer / hook / view three-layer separation, explicit dependency injection for side effects, and a pure state-machine reducer, with mandatory test-first TDD. Use when adding a new feature module, creating pages, hooks, or any component that touches side effects (media APIs, network, storage, timers, permissions), or when asked to build a testable / layered React feature. Enforces test-first (red-green-refactor) development.
metadata:
  version: '1.0.0'
---

# React Layered Feature Architecture

Build every feature so the **business state machine is a pure function** and all side effects are injected. This keeps features consistent, and lets the whole state machine be unit-tested synchronously outside the browser — no React, no real browser APIs.

> ⚠️ **Mandatory TDD: all development in this architecture is test-first.** Before writing any implementation file, write detailed test cases for that layer and confirm they fail (red), then write the minimum implementation to make them pass (green), then refactor (stay green). **Never write the implementation first and backfill tests.** If a `tdd` skill is available, use it to run the red-green-refactor loop; otherwise follow the loop manually.

> A Chinese version of this skill is kept at [SKILL.zh.md](SKILL.zh.md) / [references/EXAMPLES.zh.md](references/EXAMPLES.zh.md).

> The reference implementation is in [references/EXAMPLES.md](references/EXAMPLES.md): a `counter` module (the minimal form of the layering) first, then an `audio` recording module (the canonical full example) — build new features file-by-file against them. This is the web sibling of the `rn-layered-feature` skill; the logic and hook layers are **platform-agnostic and identical** across the two — only the adapters and the view differ.

## The core idea: a pure state machine, side effects at the edge

The hard part of a feature is its **state transitions** (idle → recording → recorded → playing, plus errors and permissions). Put that entire decision in a **pure reducer** in the logic layer. The hook performs IO through injected dependencies and then **dispatches an event** describing what happened; the reducer alone decides the next state. The hook never calls `setStatus(...)` imperatively.

Why: the reducer is a synchronous pure function, so every transition (including illegal ones) is exhaustively testable without React or a browser. The hook shrinks to "do IO, dispatch result", which is all that actually needs the heavier `renderHook` test.

## Four files, each with one job

| File | Role | Rules |
|---|---|---|
| `xxxLogic.ts` | Pure logic + reducer | State/event types, `initialState`, the `xxxReducer(state, event)` pure transition function, pure guards (`canXxx`), computation, formatting. **No React, no side effects, no browser API access.** |
| `useXxx.ts` | Hook | Owns `useReducer`, refs, and `useEffect`; orchestrates side effects via injected dependencies; dispatches events; returns a memoized flat API object (state + `canXxx` booleans + action functions). |
| `XxxView.tsx` | View | Pure presentation, **props-only**. No business logic, no hooks, no side effects. Every interactive element has a `data-testid` and native semantics. |
| `Xxx.tsx` / `XxxScreen.tsx` | Container | Ultra-thin glue: calls `useXxx()` and spreads the result down into `XxxView`. |

## State machine: guards + reducer (both pure, both in logic)

The logic layer owns the **whole** state machine, in two parts:

1. **Guards** — pure predicates. Two distinct kinds, keep them separate:
   - **UI-availability guard** — e.g. `canRequestStart(status)`: should the button be enabled? Deliberately ignores preconditions the action can resolve itself (the start button stays enabled without mic permission, because pressing it triggers the permission request).
   - **Full-precondition guard** — e.g. `canStartRecording(permission, status)`: may the action actually run? The hook re-checks this *inside* the action after resolving permission.
2. **Reducer** — `xxxReducer(state, event): state`, a pure transition function. It is the single source of truth for "what state comes next". **Illegal transitions are no-ops** (return `state` unchanged) — e.g. a `tick` event while not recording changes nothing. This makes invalid states unreachable by construction.

Every `canXxx` boolean the hook returns must come from a guard; the hook must **never inline a transition or a condition**. The truth table lives in one tested place.

## Typed domain errors

Model errors as a typed union, not a bare string. Each error carries a `kind` so the reducer can react correctly (e.g. a recording-`device` failure falls back to `idle`, a `playback` failure keeps the current state) and the View can branch/localize:

```ts
export type AudioErrorKind = 'permission' | 'device' | 'playback';
export type AudioError = { kind: AudioErrorKind; message: string };
```

Never put a raw browser-API `message` straight in front of the user as the only error channel — wrap it in a typed error at the boundary.

## Dependency injection (the side-effect boundary)

For any capability that touches browser APIs / IO (media recording, network, storage, **permissions, dialogs**…), define an interface first, then provide both a real and a simulated implementation:

- Interface: e.g. the `Recorder` type in `audioRecorder.ts`
- Real implementation: a thin adapter over the browser APIs (e.g. `createBrowserRecorder` over `MediaRecorder` + `getUserMedia`)
- Simulated implementation: e.g. `createSimulatedRecorder` (for tests and browser-less environments)

**Inject explicitly — the hook must not silently default to the simulated implementation.** A silent fallback means forgetting to inject the real implementation at the root produces an app that "works" against a fake, with no error in production. Make side-effect dependencies required options; the composition root (`App.tsx`) injects the real ones, tests inject stubs:

```ts
export type UseAudioOptions = {
  recorder: Recorder;                   // required — no silent default
  permissions: MicrophonePermissions;   // permissions are a side effect too
  tickMs?: number;                      // plain config may have defaults
};
```

Permissions, dialogs, and clipboard access are side effects like any other — put them behind an interface and inject them the same way. If the hook reads `navigator.*` or `window.*` directly, hook tests are forced into global monkey-patching, which defeats the point of DI. Keep each interface to a single capability; split it when unrelated methods accumulate (e.g. recording + upload).

**Keep the interface file free of browser-global access.** Interface + simulated impl live together (`audioRecorder.ts`, `audioPermissions.ts`); each real adapter lives in its own file (`browserRecorder.ts`, `browserMicrophonePermissions.ts`). Then importing a type or a test stub never touches `navigator`/`window`, and the file stays loadable in any test environment.

## Async actions & effects: stable callbacks, no re-entrancy, state-derived timers

Side-effecting actions are `async`, which creates hazards the hook must handle:

- **Re-entrancy / races.** Between the entry guard and the state change there is an `await`; a double-click can pass the guard twice and fire the IO twice (e.g. two `startRecording()`). Guard the session-creating action with an in-flight `ref` so only one runs at a time.
- **Stale closures over state.** Reading `state` directly forces `status`/`permission` into the callback's deps, rebuilding it on every change and destabilizing memoized children. Mirror state into a `ref` (`stateRef.current`) and read from it, so action callbacks depend only on the (stable) injected dependencies. **Assign the mirror inside an effect** (`useEffect(() => { stateRef.current = state; })`) — writing a ref during render breaks the Rules of React and is flagged by the React Compiler lint. `dispatch` from `useReducer` is already stable.
- **Long-lived effects derive from state.** Start/stop intervals and subscriptions in a `useEffect` keyed on the state that warrants them (e.g. the duration tick runs only while `status === 'recording'`), never imperatively inside action callbacks. Then *every* exit from that state — user stop, device failure, unmount — tears them down automatically; an imperatively-started interval leaks on whatever exit path you forgot.

Return the API object wrapped in `useMemo` so consumers get a stable reference.

## Testing conventions (test-first)

Write tests before the implementation at every layer; tests live in the root `__tests__/` and run in a `jsdom` environment with `@testing-library/react` + `@testing-library/jest-dom` (or the Vitest equivalents). Each layer's tests have one job — **don't duplicate coverage across layers**:

- `xxxLogic.test.ts` — the heaviest test file, and the cheapest to run (pure, synchronous, no React):
  - Guards: both true/false branches and boundary values of every guard.
  - **Reducer: exhaustive.** For every event type, assert the resulting state from each relevant source state, **including illegal transitions are no-ops**, and that error events set the right `kind` and fallback status.
- Adapter test (e.g. `browserRecorder.test.ts`) — the real implementation is a thin adapter over browser globals: mock the globals (`MediaRecorder`, `navigator.mediaDevices.getUserMedia`, `Audio`, `URL.createObjectURL`), assert every interface method drives them correctly (arguments, return values, listener subscribe/unsubscribe). Do **not** test real browser behavior. If the adapter contains mapping logic — like the permissions impl translating a persistent deny → `blocked` — assert that mapping too (`browserMicrophonePermissions.test.ts`).
- `useXxx.test.ts` — use `renderHook` from `@testing-library/react`, inject simulated stubs. Assert only what the hook *adds* on top of the reducer: that IO is called and its result is dispatched, error paths produce a `failed` event, the **permission-denied/blocked path** (request fires, IO does not, `promptOpenSettings` is called), **re-entrancy is blocked** (double-call → IO called once), and timers work. Drive timers with `jest.useFakeTimers()` + `act(() => jest.advanceTimersByTime(...))`; do **not** re-test the reducer's truth table here. **Create the injected stubs outside the `renderHook` callback** — building a new dependency object on each render changes the mount effect's deps every render and re-runs it forever (the test hangs).
- `XxxView.test.tsx` — render with props and assert by `data-testid`: text, **`disabled` state** (`toBeDisabled()`), and that `onClick` callbacks fire (clicks on a disabled `<button>` do not fire). No state logic here.
- `XxxScreen.test.tsx` — integration: drive the screen with simulated dependencies through **complete user paths** only; branch details are already covered below.

## Build checklist (red-green-refactor)

When adding a feature `foo`, **each step is test-first (red) → implementation (green) → refactor**:

1. `__tests__/fooLogic.test.ts` → `src/foo/fooLogic.ts` — state/event types, `initialState`, guards, and the **reducer** (exhaustive transition tests, including no-ops).
2. (If it has side effects) define the interface + simulated implementation in `src/foo/fooClient.ts`; the real adapter goes in its own file, driven by a test that mocks the browser globals (`__tests__/fooBrowserClient.test.ts`).
3. `__tests__/useFoo.test.ts` → `src/foo/useFoo.ts` — inject stubs via required options; assert IO-then-dispatch, error events, permission paths, re-entrancy, timers (fake timers).
4. `__tests__/FooView.test.tsx` → `src/foo/FooView.tsx` — pure presentation, props-driven, elements carry `data-testid` + native semantics.
5. `__tests__/FooScreen.test.tsx` → `src/foo/Foo.tsx` — the container is test-first too: write the integration test driving **complete user paths** with the simulated dependencies, then the thin container that makes it pass (branch details are already covered by the lower layers).
6. Wire the real implementations **once**, at the composition root (`App.tsx`).

Keep `npm test` green throughout; before committing, make sure each new test genuinely went red before it went green.

## Accessibility

Every interactive element is a real `<button type="button">` carrying `data-testid` and the `disabled` attribute. A native button gives you the role, keyboard activation (Enter/Space), focusability, and disabled semantics for free — only reach for ARIA when building a non-native widget. This is also why `<div onClick>` is forbidden (see below).

## Known limits of the reference code

- `navigator.permissions.query({ name: 'microphone' })` is not supported in every browser (notably older Safari/Firefox); where unavailable, `check()` degrades to `'unknown'` and a persistent deny cannot be distinguished from a one-time deny (`'blocked'` degrades to `'denied'`). Keep the `MicrophonePermissions` interface and harden the implementation as needed.
- Browsers cannot open site settings programmatically — `promptOpenSettings()` can only show guidance text.
- The reference never calls `URL.revokeObjectURL` on a replaced recording; a long-lived session that re-records repeatedly should revoke the previous object URL.
- The hook does not stop an in-progress recording on unmount: the tick interval clears itself (it derives from state), but the recorder keeps recording. If leaving the page must cancel recording, add an unmount effect that calls `recorder.stopRecording()`.

## Anti-pattern (do not copy)

Never use `<div onClick>` or `<span onClick>` as a button — no role, no `disabled` support, no keyboard activation, no focus. Use a native `<button type="button">` (see `ActionButton` in both reference modules). The explicit `type="button"` matters: inside a `<form>`, a bare `<button>` defaults to `type="submit"`.
