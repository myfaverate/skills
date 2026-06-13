---
name: java-safe
description: Java 编码规范,面向安全、易审查的代码——JSpecify 空值标注(@NullMarked 默认非空 + @Nullable)、最小可见性(默认包级私有)、默认 final、禁用 var。Use whenever writing, generating, refactoring, or reviewing Java (.java) code — new classes, methods, fields, records, enums, tests — or when asked to audit Java for nullability, access-modifier, final, or var-usage violations. Apply these conventions even when the user does not name them explicitly; any time you author or touch Java in this project, this is the house style.
metadata:
  version: '1.2.0'
---

# Java 安全编码规范

写出**默认安全、审查成本低**的 Java。四条规范承担了大部分工作:每个引用的可空性都显式可见、每个声明都尽可能私有、每个绑定除非必须改变否则都是 `final`、每个类型都写全。审查者读一个方法时,无需上下翻找就能知道——什么可能为 null、谁能调用它、什么可以被重新赋值、每个名字的类型是什么。

> 本技能的英文版本保存在 [SKILL.md](SKILL.md)。

这些规则适用于你在此处编写或修改的所有 Java:类、接口、record、enum 和测试。当你改动一个已经遵循它们的文件时,保持其合规;当你改动一个不合规的文件时,见[审查与修复存量代码](#审查与修复存量代码)。

## 四条规范

| # | 规范 | 一句话规则 |
|---|---|---|
| 1 | **可空性** | 用 `@NullMarked` 标记作用域,使非空成为默认;只给可空引用加 `@Nullable`。 |
| 2 | **最小可见性** | 从包级私有(无修饰符)起步;仅在真有外部调用方时才放宽到 `protected`/`public`。 |
| 3 | **默认 `final`** | 局部变量、参数、字段默认 `final`,除非确实需要重新赋值。 |
| 4 | **禁用 `var`** | 始终写明类型,即便右侧已让类型显而易见。 |

每条都在下文给出**理由**,因为理由才是让你处理表格覆盖不到的边界情况的依据。

## 1. 用 JSpecify 标注可空性

使用 [JSpecify](https://jspecify.dev) `1.0.0`(`org.jspecify.annotations`)。获得"默认非空"的地道做法**不是**到处写 `@NonNull`——而是用 `@NullMarked` 标记一个作用域,使其中每个未标注的类型都视为非空,然后**只**给能为 null 的引用加 `@Nullable`。这样噪音小得多,可空的情况也会一眼凸显出来。

**在你能掌控的最大作用域上设定一次默认值。**优先使用 `package-info.java`,让整个包默认非空:

```java
@NullMarked
package com.example.orders;

import org.jspecify.annotations.NullMarked;
```

在 `@NullMarked` 作用域内,只给确实接受或返回 null 的引用写 `@Nullable`:

```java
@NullMarked
final class UserLookup {
    private final UserRepository repository;

    UserLookup(final UserRepository repository) {
        this.repository = repository;
    }

    // 无匹配用户时返回 null——所以返回类型是 @Nullable
    @Nullable User findByEmail(final String email) {
        return repository.queryByEmail(email);
    }

    // 永不返回 null,而是抛异常——所以无需标注
    User requireByEmail(final String email) {
        final User user = findByEmail(email);
        if (user == null) {
            throw new NoSuchElementException(email);
        }
        return user;
    }
}
```

这里 `repository`、`email`、`requireByEmail` 的返回值,以及判空之后的局部变量 `user`,都*默认*非空——没有 `@NonNull` 噪音。只有那一个真能为 null 的引用带标注。这种不对称正是要点:标注标记的是**例外**,于是审查者的视线会被精确引导到 null 真正参与的地方。

### `@NonNull` 是罕见例外,而非常态

因为 `@NullMarked` 已让一切默认非空,你几乎不需要写 `@NonNull`。仅在需要*覆盖*周围的可空上下文时才用它——例如在整体可空的泛型里指定某个非空类型实参,或在 `@NullUnmarked` 区域内重新断言非空。如果你发现自己在普通参数和字段上到处撒 `@NonNull`,那说明作用域没有 `@NullMarked`,应该去修那个问题。

### 放置位置:它们是 `TYPE_USE` 注解

`@Nullable` 和 `@NonNull` 标注的是**类型**而非声明,所以对数组和泛型而言放置位置很关键——这正是容易出错之处:

```java
// 一个可空的 String:
@Nullable String name;

// 数组本身可能为 null,元素是非空 String:
String @Nullable [] names;

// 非空数组,元素是可空 String:
@Nullable String[] names;

// 非空 List,其元素可能为 null:
List<@Nullable String> tokens;

// 可空 List,其元素是非空 String:
@Nullable List<String> tokens;
```

把注解紧贴在它所描述的类型成分之前。对普通引用类型,放在最前面读起来很自然(`@Nullable User`);对数组和泛型,要停下来,放到你真正指代的那个成分上。

### `equals` 陷阱:用 `@Nullable` 覆盖

最常见的 `@NullMarked` 错误就是 `equals`。`Object.equals` 的契约明确接受 null(`x.equals(null)` 必须返回 `false`),但在 `@NullMarked` 作用域内,未标注的参数是非空的——于是那个想当然的覆盖签名是*错的*:

```java
@Override public boolean equals(Object obj) { ... }   // 错:此处 obj 被当成非空
```

空值检查器会拒绝它,因为参数的可空性不再与父类匹配。给参数加标注,以匹配继承来的契约:

```java
@Override public boolean equals(@Nullable Object obj) {
    if (this == obj) {
        return true;
    }
    if (!(obj instanceof User other)) {   // instanceof 也能处理 null
        return false;
    }
    return email.equals(other.email);
}
```

道理和 `@Nullable` 返回值一样:标注标记的是那个真正跨出非空默认的引用。`hashCode()` 和 `toString()` 无需标注——它们的契约与 null 无关。

### 引入依赖

若项目尚未引入,添加依赖(仅注解,无运行时开销):

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

从 `org.jspecify.annotations` 导入:`Nullable`、`NonNull`、`NullMarked`、`NullUnmarked`。

## 2. 最小可见性

让每个类型、方法、字段都从**能编译通过的最低**访问级别起步,只有当当前作用域之外真有调用方时才放宽。默认是包级私有——**完全不写修饰符**。只有当某物确实需要被另一个包使用、或被子类继承时,才动用 `public` 或 `protected`。

```java
// 好:默认包级私有——同包协作者可见,
// 对世界其余部分不可见(因而不构成约束)
final class OrderValidator {
    private static final int MAX_ITEMS = 50;   // private:别人不需要它

    boolean isValid(final Order order) {        // 包级私有:被隔壁的 OrderService 使用
        return order.items().size() <= MAX_ITEMS;
    }
}
```

为什么它比看上去更重要:**访问级别是一种契约,而 `public` 是最昂贵的那种。**每个 `public` 成员都是你对外界许下的承诺——它能依赖这个东西,这意味着你日后无法随意重命名、删除或改变它的语义。包级私有成员则可以随意重构,因为编译器能看到每一个调用方。窄可见性让未来的你保持自由。

一个实际推论:不要条件反射地把字段设为 `private` 再加一对 `public` getter/setter。如果只有同包代码读取某字段,包级私有的字段(或访问器)就够了;等真正出现外部读者时再加 getter、再放宽到 `public`,而不是预先就做。"我以后某处可能会用到"也同理——等"以后"真的到来时再放宽,因为日后收窄是破坏性变更,而日后放宽是免费的。

`private` 仍有其位置:它是字段、以及作为单个类实现细节的辅助方法的正确默认值。规则不是"包级私有优于 private",而是"选能用的最窄级别"——内部实现用 `private`,类的协作者用包级私有(而非 `public`)。

## 3. 默认 `final`

把每个局部变量、方法参数、字段都设为 `final`,除非它确实会被重新赋值。把"可重新赋值"当作你主动*选入*的特性,而非要去*选出*的。

```java
final class PriceCalculator {
    private final TaxTable taxTable;          // 构造时设定一次

    PriceCalculator(final TaxTable taxTable) {
        this.taxTable = taxTable;
    }

    Money total(final List<LineItem> items) {  // 参数从不重新赋值
        final Money subtotal = sum(items);      // 只计算一次
        final Money tax = taxTable.on(subtotal);
        return subtotal.plus(tax);
    }
}
```

为什么:`final` 把"绑定之后绝不改变"从一件读者必须*扫遍整个方法去核实*的事,变成编译器*一眼就能保证*的事。它消除了一整类 bug(意外的重新赋值,尤其是经典的"复用了循环变量"),并且表达了意图——一个非 `final` 的局部变量如今成了一个信号:"注意这里,它会变"。当所有*能* `final` 的都 `final` 了,剩下那几个可变绑定就承载了真正的信息。

这也延伸到字段:`final` 字段恰好被设定一次(在声明处或构造函数中),可以被多个线程安全读取而无需额外同步。优先用 `final` 字段构建不可变对象;只有当对象确实拥有变化的状态时,才使用可变字段。

当确实*需要*重新赋值时——一个无法用 stream/reduce 表达的累加器、一个合理地会变化的字段——直接不写 `final` 即可。此时 `final` 的缺席就有了含义。(注意:参数或局部变量上的 `final` 纯属局部,不会以任何可观察的方式改变 API 或字节码,所以广泛使用它没有成本。)

**record 是例外——不要给组件写 `final`。**record 的组件*本就*隐式 `final`,且语言禁止该修饰符:`record Point(final int x, int y)` 会编译报错。所以 record 的组件完全无需写 `final`——这是本规范唯一一处免费满足的地方。可空性照常适用,标在组件的类型上:

```java
record User(String email, @Nullable String displayName) {}
```

这里 `email` 因 `@NullMarked` 默认而非空,`displayName` 是那个唯一可空的组件。只在 record 方法*内部*的局部变量和参数上加 `final`,与其他类一样。

## 4. 禁用 `var`

始终声明显式类型。即便右侧已让类型对*你*显而易见,也要写出来。

```java
// 好
final Map<String, List<Order>> ordersByCustomer = groupByCustomer(orders);
final UserRepository repository = new JdbcUserRepository(dataSource);

// 避免——即便类型"显而易见"
var ordersByCustomer = groupByCustomer(orders);
var repository = new JdbcUserRepository(dataSource);
```

为什么我们在此选择显式:代码被阅读的次数远多于被编写,且常常在没有类型推断的场景下被阅读——pull request 里的 diff、`git blame` 片段、代码审查评论、聊天里的代码段。在所有这些场景里,右侧可能是一个像 `groupByCustomer(orders)` 的方法调用,其返回类型并不可见,而 `var` 会逼读者去翻找。显式类型是随这一行一起旅行的文档。它也让代码库在视觉上保持一致:处处一种声明风格,无需逐行判断类型是否"足够明显"。

这是一个刻意的团队风格选择,而非声称 `var` 普遍不好。在本项目中,每次都优先写显式类型。

### Lambda 形参

同样的规则适用,但 lambda 有一处特殊处理。`var` 写法和别处一样被禁止:

```java
// 避免——lambda 形参里显式用了 var 关键字
list.stream().map((var order) -> order.total());
```

但**隐式 lambda 形参没问题**——它没用 `var`,其类型由函数式接口的目标类型固定,而这个目标类型几乎总在紧邻的调用中可见(stream 链、回调)。在那里强制写显式类型是噪音而非文档,所以优先用隐式形式:

```java
// 好——隐式形参,类型由目标类型推断
list.stream()
    .filter(order -> order.isPaid())
    .map(order -> order.total());

names.forEach(name -> log(name));
```

只在确实需要时才写显式 lambda 形参类型(`(Order order) -> ...`)——例如消除重载歧义或附加注解。禁的是 `var`,不是类型推断。

## 综合示例

一个触及全部四条规范的小类:

```java
@NullMarked
package com.example.checkout;

import org.jspecify.annotations.NullMarked;
```

```java
package com.example.checkout;

import java.util.List;
import org.jspecify.annotations.Nullable;

final class DiscountResolver {                       // 包级私有(2)、final 类
    private final List<DiscountRule> rules;          // private + final(2、3)

    DiscountResolver(final List<DiscountRule> rules) {  // final 参数(3)
        this.rules = rules;
    }

    // 无规则适用时返回 null——唯一的可空引用(1)
    @Nullable Discount resolve(final Cart cart) {    // final 参数(3)
        for (final DiscountRule rule : rules) {      // final 循环变量(3)、显式类型(4)
            final Discount discount = rule.apply(cart);  // 显式类型(4)
            if (discount != null) {
                return discount;
            }
        }
        return null;
    }
}
```

注意什么*不在*这里:没有 `@NonNull`(包级 `@NullMarked` 默认已处理)、没有 `public`、没有 `var`。唯一的注解就是那个标记真正可空返回值的 `@Nullable`。这种信噪比正是目标所在。

## 审查与修复存量代码

当被要求审查或修复 Java 时,按以下优先级(最易出 bug 的在前)扫描违规项:

1. **缺少可空性约束**——包/类上没有 `@NullMarked`,或方法可能返回 null 却没有 `@Nullable` 返回类型。这些会藏匿 NPE。先在包级加 `@NullMarked`,再标注真正可空的引用;编译器/分析器会把其余的暴露出来。
2. **可见性过宽**——`public` 的类型和成员,而其包外并无调用方。收窄它们。(当心:一个*确实*被其他模块调用的 `public` 方法是真实契约——别盲目收窄。先确认有无外部调用方;若无法确定,就标记出来而不是贸然破坏。)
3. **缺少 `final`**——从不重新赋值的局部变量、参数、字段。加上 `final`。
4. **使用了 `var`**——逐个替换为显式类型。

按此顺序修,并在可空性改动与可见性改动之间重新构建一次,因为收窄可见性可能暴露出你没预料到的调用点。不要把大规模机械式的 `final`/`var` 清扫,和有风险的可见性收窄,捆进同一个无法审查的改动里——把安全的机械编辑与可能破坏调用方的编辑分开。

## 验证可编译

写完或改完 Java 后,用项目**已经在用**的工具构建——**检测,而非假设**:

- 存在 `pom.xml` → Maven:`mvn -q compile`(若测试在范围内则加 `mvn -q test`)。
- 存在 `build.gradle` / `build.gradle.kts` → Gradle:`./gradlew compileJava`(优先用 wrapper `./gradlew` 而非系统 `gradle`)。
- 两者都没有 → 用 `javac` 编译改动的文件做基本健全性检查,并说明这一点。

编译通过是底线,而非正确性的证明。可空性注解只有在构建中接入了检查器(如 NullAway 或 Checker Framework)时才会真正捕获 bug——若已有,就让它运行并把其结论当真;若没有,这些注解作为"由审查强制执行的文档"仍有价值,所以不要在用户没要求时引入重量级检查器。

## 扫描存量项目

本技能自带一个扫描器,对一整棵 `.java` 文件树扫描**可机器检测**的规范,并生成自包含的 HTML 报告:

```bash
python -m scripts.scan path/to/src --out report.html
# CI 卡点:发现任何违规则以非零退出
python -m scripts.scan path/to/src --fail-on-violations
```

要诚实看待它的覆盖范围——它和上面的编译检查一样,只是*底线*。它仅以机器方式验证**规范 4(禁用 `var`)**和**规范 3(`final` 局部变量与参数)**,通过 Checkstyle 实现。它**不**验证:

- **规范 1(可空性)**——需要 NullAway 接入目标项目自身的构建,无法对散装文件运行。
- **规范 2(可见性)**——需要跨文件调用方分析,才能区分正当的 `public` API 与过宽的可见性。

HTML 报告会在「覆盖矩阵」里把这点写明,因此一次干净的扫描绝不会被误认为完全合规——规范 1 和 2 仍需走[审查与修复存量代码](#审查与修复存量代码)中的人工复核。一个已知边界:字符串字面量里的 `var` 可能误报(罕见)。首次运行时扫描器会把 Checkstyle jar 下载到 `~/.cache/java-safe/`(Checkstyle 13.x 需要 JDK 21+);设置 `CHECKSTYLE_JAR` 可离线复用已有 jar。
