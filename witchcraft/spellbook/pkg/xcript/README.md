# Witchcraft-Xcript

Witchcraft Xcript is a standalone, flat scripting language written in Rust that implements a dynamic data structure called the **Omega type** (equivalent to `any`, `list`, or `hashmap` / `table`).

The original objective was to provide an automation configuration file for **WitchcraftFEX**, evolving into a standalone flat scripting language (no `import` system and no structured/modular user-defined functions) compiled as a static binary capable of reading and executing `.xcript` files.

## Language Specification (`scr/define.config`)

- **Output**:
  - `echo <expr>`: Sends evaluated data to `stdout`.
  - `warn[val, err]`: Sends `val` to `stdout` and `err` to `stderr`.
  - `warn <res>`: Sends table `val`/`stdout` to `stdout` and `err`/`stderr` to `stderr`.
- **Declarations & Omega Type**:
  - `declare x = "text"` (String)
  - `declare list = [1, 2, 3]` (List)
  - `declare tbl = table["key", "value"]` or `table[]` (Table / HashMap)
  - `declare res;` (Null / uninitialized Omega)
- **Loops**:
  - `while x until y { ... }`
  - `for x in y { ... }`
  - `for x in x++1 until <cond> { ... }`
  - `for x in x--1 until <cond> { ... }`
- **Conditionals**:
  - `if x { ... } elif y { ... } else { ... } default { ... }` (also supports `end` terminator)
- **Pattern Analysis**:
  - `res = analyse X condition "pattern"` (supports `condition`, `==`, `!=`, `>`, `<`, `>=`, `<=`, `contains`, `starts_with`, `ends_with`, `in`)
- **Command Execution**:
  - `res = exec "command"` (returns an Omega `table` with `val`/`stdout`, `err`/`stderr`, `code`, and `ok`)

## Building & Running

```bash
cargo build --release
./target/release/xcript examples/demo.xcript
```
