---
name: java-safe
description: Java coding conventions for safe, reviewable code — JSpecify nullability (@NullMarked default-non-null + @Nullable), minimal visibility (package-private by default), final by default, no var, and generics over Object. Use whenever writing, generating, refactoring, or reviewing Java (.java) code — new classes, methods, fields, records, enums, tests — or when asked to audit Java for nullability, access-modifier, final, var-usage, or raw-Object violations. Apply these conventions even when the user does not name them explicitly; any time you author or touch Java in this project, this is the house style.
metadata:
  version: '1.4.0'
---

# Java Safe Conventions

Write Java that is **safe by default and cheap to review**. Five conventions do most of the work: every reference's nullability is explicit, every declaration is as private as it can be, every binding is `final` unless it must change, every type is spelled out, and "any type" is a real type parameter rather than `Object`. A reviewer should be able to read one method and know — without scrolling — what can be null, who can call this, what can be reassigned, what every name's type is, and whether a value's type survives the boundary.

> A Chinese version of this skill is kept at [SKILL.zh.md](SKILL.zh.md).

These rules apply to all Java you author or modify here: classes, interfaces, records, enums, and tests. When you touch a file that already follows them, keep it conforming; when you touch one that doesn't, see [Reviewing and fixing existing code](#reviewing-and-fixing-existing-code).

## The five conventions

| # | Convention | One-line rule |
|---|---|---|
| 1 | **Nullability** | `@NullMarked` the scope so non-null is the default; mark only the nullable references `@Nullable`. |
| 2 | **Minimal visibility** | Start package-private (no modifier); widen to `protected`/`public` only for real external callers. |
| 3 | **`final` by default** | Locals, parameters, and fields are `final` unless reassignment is genuinely required. |
| 4 | **No `var`** | Always write the explicit type, even when the right-hand side makes it obvious. |
| 5 | **Generics over `Object`** | Express "any type" with a type parameter `<T>`, not `Object`; reach for `Object` only where the contract demands it. |

Each is explained below with the reasoning, because the reasoning is what lets you handle the edge cases the table can't.

## 1. Nullability with JSpecify

Use [JSpecify](https://jspecify.dev) `1.0.0` (`org.jspecify.annotations`). The idiomatic way to get "non-null by default" is **not** to write `@NonNull` everywhere — it's to mark a scope with `@NullMarked` so that every unannotated type is non-null, and then annotate only the references that can be null with `@Nullable`. This is far less noisy and makes the nullable cases jump out.

**Set the default once, at the widest scope you own.** Prefer a `package-info.java` so an entire package is non-null by default:

```java
@NullMarked
package com.example.orders;

import org.jspecify.annotations.NullMarked;
```

Inside a `@NullMarked` scope, write `@Nullable` only on the references that genuinely accept or return null:

```java
@NullMarked
final class UserLookup {
    private final UserRepository repository;

    UserLookup(final UserRepository repository) {
        this.repository = repository;
    }

    // returns null when no user matches — so the return type is @Nullable
    @Nullable 
    User findByEmail(final String email) {
        return repository.queryByEmail(email);
    }

    // never returns null; throws instead — so no annotation needed
    User requireByEmail(final String email) {
        final User user = findByEmail(email);
        if (user == null) {
            throw new NoSuchElementException(email);
        }
        return user;
    }
}
```

Here `repository`, `email`, the `requireByEmail` return, and the local `user`-after-the-check are all non-null *by default* — no `@NonNull` clutter. Only the one reference that can actually be null carries an annotation. That asymmetry is the point: the annotation marks the exception, so a reviewer's eye is drawn exactly to where null is in play.

### `@NonNull` is the rare exception, not the rule

Because `@NullMarked` already makes everything non-null, you almost never write `@NonNull`. Reach for it only to *override* a surrounding nullable context — e.g. one non-null type argument inside an otherwise-nullable generic, or re-asserting non-null inside a `@NullUnmarked` region. If you find yourself sprinkling `@NonNull` across ordinary parameters and fields, the scope isn't `@NullMarked` and you should fix that instead.

### Placement: these are `TYPE_USE` annotations

`@Nullable` and `@NonNull` annotate the **type**, not the declaration, so placement matters for arrays and generics — this is the part people get wrong:

```java
// A nullable String:
@Nullable 
String name;

// An array that may itself be null, of non-null Strings:
String @Nullable [] names;

// A non-null array of nullable Strings:
@Nullable 
String[] names;

// A non-null list whose elements may be null:
List<@Nullable String> tokens;

// A nullable list of non-null Strings:
@Nullable 
List<String> tokens;
```

Put the annotation immediately before the type component it describes. For a plain reference type the leading position reads naturally (`@Nullable User`); for arrays and generics, stop and place it on the exact component you mean.

### The `equals` pitfall: override with `@Nullable`

The single most common `@NullMarked` mistake is `equals`. `Object.equals`'s contract explicitly accepts null (`x.equals(null)` must return `false`), but inside a `@NullMarked` scope an unannotated parameter is non-null — so the obvious override has the *wrong* signature:

```java
@Override public boolean equals(Object obj) { ... }   // wrong: obj is non-null here
```

A null-checker rejects this because the parameter's nullability no longer matches the supertype. Annotate the parameter to match the inherited contract:

```java
@Override public boolean equals(@Nullable Object obj) {
    if (this == obj) {
        return true;
    }
    if (!(obj instanceof User other)) {   // instanceof handles null too
        return false;
    }
    return email.equals(other.email);
}
```

Same principle as a `@Nullable` return: the annotation marks the one reference that genuinely steps outside the non-null default. `hashCode()` and `toString()` need no annotation — their contracts don't involve null.

### Setup

Add the dependency if it isn't present (it's annotations-only, no runtime cost):

```xml
<!-- Maven -->
<dependency>
  <groupId>org.jspecify</groupId>
  <artifactId>jspecify</artifactId>
  <version>1.0.0</version>
</dependency>
```

```kotlin
// Gradle
implementation("org.jspecify:jspecify:1.0.0")
```

Import from `org.jspecify.annotations`: `Nullable`, `NonNull`, `NullMarked`, `NullUnmarked`.

## 2. Minimal visibility

Start every type, method, and field at the **lowest** access level that compiles, and widen only when a real caller outside the current scope forces it. The default is package-private — **no modifier at all**. Reach for `public` or `protected` only when something genuinely must be used from another package or extended by a subclass.

```java
// good: package-private by default — visible to collaborators in the same
// package, invisible (and so unconstraining) to the rest of the world
final class OrderValidator {
    private static final int MAX_ITEMS = 50;   // private: nobody else needs it

    boolean isValid(final Order order) {        // package-private: used by OrderService next door
        return order.items().size() <= MAX_ITEMS;
    }
}
```

Why this matters more than it looks: **access level is a contract, and `public` is the most expensive one.** Every `public` member is something you've promised the outside world it can depend on, which means it's something you can't freely rename, remove, or change the semantics of later. Package-private members can be refactored at will because the compiler can see every caller. Narrow visibility keeps your future self free.

A practical consequence: don't reflexively make fields `private` and then add a `public` getter/setter. If only same-package code reads a field, a package-private field (or accessor) is enough; add the getter and widen to `public` when an actual external reader appears, not preemptively. The same goes for "I might need this elsewhere someday" — widen when *someday* arrives, because narrowing later is a breaking change while widening later is free.

`private` still has its place: it's the right default for fields and for helper methods that are an implementation detail of a single class. The rule isn't "prefer package-private over private" — it's "pick the narrowest level that works," which is `private` for internals and package-private (not `public`) for the class's collaborators.

## 3. `final` by default

Make every local variable, method parameter, and field `final` unless it is genuinely reassigned. Treat reassignability as the thing you opt *into*, not out of.

```java
final class PriceCalculator {
    private final TaxTable taxTable;          // set once in the constructor

    PriceCalculator(final TaxTable taxTable) {
        this.taxTable = taxTable;
    }

    Money total(final List<LineItem> items) {  // parameter never reassigned
        final Money subtotal = sum(items);      // computed once
        final Money tax = taxTable.on(subtotal);
        return subtotal.plus(tax);
    }
}
```

Why: `final` turns "this never changes after it's bound" from a thing the reader has to *verify* by scanning the whole method into a thing the compiler *guarantees* at a glance. It eliminates a whole class of bugs (accidental reassignment, especially the classic "reused the loop variable") and it documents intent — a non-`final` local is now a signal that says "watch this, it changes." When everything that *can* be `final` *is*, the few mutable bindings that remain carry real information.

This extends to fields: a `final` field is set exactly once (at declaration or in the constructor) and is safe to read from multiple threads without further synchronization. Prefer immutable objects built from `final` fields; reach for a mutable field only when the object genuinely has changing state.

When reassignment *is* required — an accumulator that can't be expressed as a stream/reduce, a field that legitimately changes — just leave off `final`. The absence then means something. (Note: `final` on a parameter or local is purely local; it doesn't change the API or bytecode in any observable way, so there's no cost to applying it broadly.)

**Records are the exception — don't write `final` on components.** A record's components are *already* implicitly `final`, and the language forbids the modifier: `record Point(final int x, int y)` is a compile error. So a record needs no `final` on its components at all — it's the one place this convention is satisfied for free. Nullability still applies normally, on the component's type:

```java
record User(String email, @Nullable String displayName) {}
```

Here `email` is non-null by the `@NullMarked` default and `displayName` is the one nullable component. Add `final` only to locals and parameters *inside* the record's methods, just like any other class.

## 4. No `var`

Always declare the explicit type. Even when the right-hand side makes the type obvious to *you*, write it out.

```java
// good
final Map<String, List<Order>> ordersByCustomer = groupByCustomer(orders);
final UserRepository repository = new JdbcUserRepository(dataSource);

// avoid — even though the type is "obvious"
var ordersByCustomer = groupByCustomer(orders);
var repository = new JdbcUserRepository(dataSource);
```

Why we choose explicitness here: code is read far more often than written, and often in contexts where inference isn't available — a diff in a pull request, a `git blame` excerpt, a code-review comment, a snippet in a chat. In all of those the right-hand side may be a method call like `groupByCustomer(orders)` whose return type isn't visible, and `var` forces the reader to go hunting. The explicit type is documentation that travels with the line. It also keeps the codebase visually consistent: one declaration style everywhere, no per-line judgment call about whether the type is "obvious enough."

This is a deliberate house-style choice, not a claim that `var` is bad in general. In this project, prefer the explicit type every time.

### Lambda parameters

The same rule applies, but with one carve-out for lambdas. The `var` form is banned like everywhere else:

```java
// avoid — explicit var keyword in a lambda parameter
list.stream().map((var order) -> order.total());
```

But an **implicit lambda parameter is fine** — it doesn't use `var`, and its type is fixed by the functional interface's target type, which is almost always visible in the immediately surrounding call (a stream chain, a callback). Forcing an explicit type there is noise, not documentation, so prefer the implicit form:

```java
// good — implicit parameter, type inferred from the target type
list.stream()
    .filter(order -> order.isPaid())
    .map(order -> order.total());

names.forEach(name -> log(name));
```

Write an explicit lambda parameter type (`(Order order) -> ...`) only when you genuinely need it — e.g. to disambiguate an overload or to attach an annotation. The ban is on `var`, not on inference.

## 5. Generics over `Object`

When a class, method, or field works with "some type the caller chooses," express that with a **type parameter**, not `Object`. `Object` throws the type away at the boundary: every caller has to cast on the way out, and a wrong cast is a `ClassCastException` at runtime instead of a compile error. A type parameter keeps the relationship — what goes in is what comes out, checked by the compiler.

```java
// avoid — Object erases the type; callers must cast, and can cast wrong
final class Box {
    private final Object value;
    Box(final Object value) { this.value = value; }
    Object get() { return value; }
}
final String s = (String) box.get();   // a ClassCastException waiting to happen

// good — the type parameter carries the type through, no cast needed
final class Box<T> {
    private final T value;
    Box(final T value) { this.value = value; }
    T get() { return value; }
}
final String s = box.get();            // compiler-guaranteed
```

The same applies to collections and signatures: prefer `List<Order>` or `List<T>` over `List<Object>`, and `<T> T first(List<T> items)` over `Object first(List<Object> items)`. When a method accepts a family of types it doesn't need to name, use a bounded type parameter or a wildcard (`List<? extends Number>`) rather than `List<Object>`.

### When `Object` *is* correct

Reach for `Object` only where the contract is genuinely about *any* object, or the language forces it:

- **Overrides whose supertype uses `Object`** — `equals(@Nullable Object)`, and methods inherited from an interface that takes `Object`. You can't narrow these (see §1).
- **Type-parameter bounds** — `<T extends @Nullable Object>` is the JSpecify way to say "`T` may be nullable"; that `Object` is a *bound*, not a value type, and is correct.
- **Genuinely type-agnostic uses** — a lock (`private final Object lock = new Object();`), reflection (`Class<?>`), or interop with a pre-generics API you don't control.

The rule is "don't use `Object` as a stand-in for a type parameter," not "never write `Object`."

## Putting it together

A small class touching the first four conventions (the 5th needs a generic scenario, omitted here):

```java
@NullMarked
package com.example.checkout;

import org.jspecify.annotations.NullMarked;
```

```java
package com.example.checkout;

import java.util.List;
import org.jspecify.annotations.Nullable;

final class DiscountResolver {                       // package-private (2), final class
    private final List<DiscountRule> rules;          // private + final (2, 3)

    DiscountResolver(final List<DiscountRule> rules) {  // final param (3)
        this.rules = rules;
    }

    // returns null when no rule applies — the one nullable reference (1)
    @Nullable Discount resolve(final Cart cart) {    // final param (3)
        for (final DiscountRule rule : rules) {      // final loop var (3), explicit type (4)
            final Discount discount = rule.apply(cart);  // explicit type (4)
            if (discount != null) {
                return discount;
            }
        }
        return null;
    }
}
```

Notice what's *absent*: no `@NonNull` (the `@NullMarked` package default handles it), no `public`, no `var`. The only annotation is the single `@Nullable` that flags the genuinely-nullable return. That signal-to-noise ratio is the goal.

## Reviewing and fixing existing code

When asked to audit or fix Java, scan for these violations in priority order (most-bug-prone first):

1. **Missing nullability discipline** — no `@NullMarked` on the package/class, or methods that can return null without a `@Nullable` return type. These hide NPEs. Add `@NullMarked` at the package level first, then annotate the genuinely-nullable references; the compiler/analyzer will surface the rest.
2. **Over-broad visibility** — `public` types and members with no caller outside their package. Narrow them. (Be careful: a `public` method that *is* called from another module is a real contract — don't narrow blindly. Check for external callers first; if you can't be sure, flag it rather than break it.)
3. **`Object` standing in for a type parameter** — fields/params/returns typed `Object` (or `List<Object>` and friends) that really mean "a type the caller chooses." Introduce a type parameter and drop the casts. Like visibility, this changes signatures and can ripple to callers, so check call sites — and leave the legitimate `Object` uses alone (`equals`, locks, reflection, `<T extends @Nullable Object>` bounds).
4. **Missing `final`** — locals, params, and fields that are never reassigned. Add `final`.
5. **`var` usage** — replace each with the explicit type.

Fix in that order and re-run the build between nullability changes and the signature-changing ones (visibility, generics), since those can surface call sites you didn't expect. Don't bundle a giant mechanical `final`/`var` sweep with risky visibility narrowing or generics changes in one unreviewable change — separate the safe mechanical edits from the ones that can break callers.

## Verify it compiles

After writing or changing Java, build with whatever the project already uses — **detect, don't assume**:

- `pom.xml` present → Maven: `mvn -q compile` (and `mvn -q test` if tests are in scope).
- `build.gradle` / `build.gradle.kts` present → Gradle: `./gradlew compileJava` (prefer the wrapper `./gradlew` over a system `gradle`).
- Neither → compile the changed files with `javac` as a sanity check, and say so.

A clean compile is the floor, not proof of correctness. The nullability annotations only catch bugs if a checker (e.g. NullAway, or the Checker Framework) is wired into the build — if one is present, let it run and treat its findings as real; if none is, the annotations are still valuable as enforced-by-review documentation, so don't add a heavyweight checker unless the user asks.

## Scanning an existing project

This skill bundles a scanner that flags the machine-checkable conventions across a tree of `.java` files and writes a self-contained HTML report **with the offending source lines shown inline**. Run it inside a throwaway venv so the system Python is never touched:

```bash
# one-time: an isolated interpreter under build/ (git-ignored)
python3 -m venv build/java-safe-venv
# scan; the report lands in build/reports/ by default
build/java-safe-venv/bin/python -m scripts.scan path/to/src
# CI gate: exit non-zero if anything is found
build/java-safe-venv/bin/python -m scripts.scan path/to/src --fail-on-violations
```

What it checks, and **how deeply** — the report's coverage matrix says the same, so a clean scan is never mistaken for full compliance:

| # | Convention | Machine check |
|---|---|---|
| 3 | `final` locals/params | **Full** — Checkstyle `FinalLocalVariable` + `FinalParameters`. |
| 4 | No `var` | **Full** — Checkstyle. Known edge: a `var` inside a string literal can false-positive (rare). |
| 1 | Nullability | **Subset** — a missing `@NullMarked` default (the file or its `package-info.java`) is flagged. Whether a specific return/param should be `@Nullable` still needs NullAway. |
| 2 | Minimal visibility | **Subset** — a `public` top-level type that nothing imports from another package is flagged as narrowable. Methods/fields and reflection/DI/SPI/entry-point uses are out of scope — verify before narrowing. |
| 5 | Generics over `Object` | **Not checked** — telling `Object`-as-pseudo-generic from legitimate `Object` (`equals`, locks, reflection, bounds) needs judgment. |

Conventions whose checks are subsets (1, 2) or absent (5) still go through the manual review in [Reviewing and fixing existing code](#reviewing-and-fixing-existing-code).

On first run the scanner downloads the Checkstyle jar to `~/.cache/java-safe/` (Checkstyle 13.x needs JDK 21+ — point `JAVA_HOME` at one); set `CHECKSTYLE_JAR` to reuse an existing jar offline. The report defaults to `build/reports/java-safe-report.html` (override with `--out`; `--format json` gives a machine-readable dump).

When you run the scanner for someone, **give them the report location**: it prints an absolute path and a `file://` URL (`Open in a browser: file://…`) — surface that link so they can open it directly.
