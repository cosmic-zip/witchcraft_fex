use std::collections::HashMap;
use std::io::{self, Write};
use std::process::Command;

use crate::omega::Omega;
use crate::parser::{BinOp, Expr, Stmt};

const MAX_LOOP_ITERATIONS: usize = 100_000;

pub struct Interpreter {
    pub env: HashMap<String, Omega>,
}

impl Interpreter {
    pub fn new() -> Self {
        Self {
            env: HashMap::new(),
        }
    }

    pub fn run(&mut self, stmts: &[Stmt]) -> Result<(), String> {
        for stmt in stmts {
            self.exec_stmt(stmt)?;
        }
        Ok(())
    }

    fn exec_stmt(&mut self, stmt: &Stmt) -> Result<(), String> {
        match stmt {
            Stmt::Echo(expr) => {
                let val = self.eval_expr(expr)?;
                println!("{}", val.as_str_value());
            }
            Stmt::WarnPair(val_expr, err_expr) => {
                let val = self.eval_expr(val_expr)?.as_str_value();
                let err = self.eval_expr(err_expr)?.as_str_value();
                if !val.is_empty() {
                    println!("{}", val);
                    let _ = io::stdout().flush();
                }
                if !err.is_empty() {
                    eprintln!("{}", err);
                    let _ = io::stderr().flush();
                }
            }
            Stmt::Warn(expr) => {
                let val = self.eval_expr(expr)?;
                match &val {
                    Omega::Table(map)
                        if map.contains_key("val")
                            || map.contains_key("stdout")
                            || map.contains_key("err")
                            || map.contains_key("stderr") =>
                    {
                        let out_str = map
                            .get("val")
                            .or_else(|| map.get("stdout"))
                            .map(|v| v.as_str_value())
                            .unwrap_or_default();
                        let err_str = map
                            .get("err")
                            .or_else(|| map.get("stderr"))
                            .map(|v| v.as_str_value())
                            .unwrap_or_default();

                        if !out_str.is_empty() {
                            print!("{}", out_str);
                            if !out_str.ends_with('\n') {
                                println!();
                            }
                            let _ = io::stdout().flush();
                        }
                        if !err_str.is_empty() {
                            eprint!("{}", err_str);
                            if !err_str.ends_with('\n') {
                                eprintln!();
                            }
                            let _ = io::stderr().flush();
                        }
                    }
                    Omega::List(items) if items.len() == 2 => {
                        let out_str = items[0].as_str_value();
                        let err_str = items[1].as_str_value();
                        if !out_str.is_empty() {
                            println!("{}", out_str);
                        }
                        if !err_str.is_empty() {
                            eprintln!("{}", err_str);
                        }
                    }
                    _ => {
                        let s = val.as_str_value();
                        println!("{}", s);
                        eprintln!("{}", s);
                    }
                }
            }
            Stmt::Declare { name, value } => {
                let v = match value {
                    Some(expr) => self.eval_expr(expr)?,
                    None => Omega::Null,
                };
                self.env.insert(name.clone(), v);
            }
            Stmt::Assign { name, index, value } => {
                let evaluated = self.eval_expr(value)?;
                if let Some(idx_expr) = index {
                    let key = self.eval_expr(idx_expr)?;
                    let entry = self
                        .env
                        .entry(name.clone())
                        .or_insert_with(Omega::empty_table);
                    entry.set_index(&key, evaluated);
                } else {
                    self.env.insert(name.clone(), evaluated);
                }
            }
            Stmt::While { cond, until, body } => {
                let mut count = 0;
                while self.eval_expr(cond)?.is_truthy() {
                    if let Some(until_expr) = until {
                        if self.eval_expr(until_expr)?.is_truthy() {
                            break;
                        }
                    }
                    self.run(body)?;
                    count += 1;
                    if count >= MAX_LOOP_ITERATIONS {
                        return Err(
                            "Limite máximo de iterações atingido no laço 'while'".to_string()
                        );
                    }
                }
            }
            Stmt::ForIn {
                var,
                iterable,
                body,
            } => {
                let iter_val = self.eval_expr(iterable)?;
                let elements: Vec<Omega> = match iter_val {
                    Omega::List(items) => items,
                    Omega::Table(map) => {
                        let mut keys: Vec<String> = map.keys().cloned().collect();
                        keys.sort();
                        keys.into_iter().map(Omega::Str).collect()
                    }
                    Omega::Str(s) => s.chars().map(|c| Omega::Str(c.to_string())).collect(),
                    Omega::Number(n) => {
                        let end = n.max(0.0) as usize;
                        (0..end).map(|i| Omega::Number(i as f64)).collect()
                    }
                    other => vec![other],
                };
                for item in elements {
                    self.env.insert(var.clone(), item);
                    self.run(body)?;
                }
            }
            Stmt::ForStep {
                var,
                step,
                until,
                body,
            } => {
                let mut current = self
                    .env
                    .get(var)
                    .and_then(|v| v.as_number())
                    .unwrap_or(0.0);

                if let Some(until_expr) = until {
                    let mut count = 0;
                    loop {
                        self.env.insert(var.clone(), Omega::Number(current));
                        if self.eval_expr(until_expr)?.is_truthy() {
                            break;
                        }
                        self.run(body)?;
                        current = self
                            .env
                            .get(var)
                            .and_then(|v| v.as_number())
                            .unwrap_or(current)
                            + step;
                        self.env.insert(var.clone(), Omega::Number(current));
                        count += 1;
                        if count >= MAX_LOOP_ITERATIONS {
                            return Err(
                                "Limite máximo de iterações atingido no laço 'for'".to_string()
                            );
                        }
                    }
                } else {
                    // Single step execution or bounded countdown/countup when no `until` is given
                    self.run(body)?;
                    current = self
                        .env
                        .get(var)
                        .and_then(|v| v.as_number())
                        .unwrap_or(current)
                        + step;
                    self.env.insert(var.clone(), Omega::Number(current));
                }
            }
            Stmt::If {
                branches,
                else_branch,
                default_branch,
            } => {
                let mut matched = false;
                for (cond, body) in branches {
                    if self.eval_expr(cond)?.is_truthy() {
                        self.run(body)?;
                        matched = true;
                        break;
                    }
                }
                if !matched {
                    if let Some(else_body) = else_branch {
                        self.run(else_body)?;
                    } else if let Some(def_body) = default_branch {
                        self.run(def_body)?;
                    }
                }
            }
        }
        Ok(())
    }

    pub fn eval_expr(&mut self, expr: &Expr) -> Result<Omega, String> {
        match expr {
            Expr::Null => Ok(Omega::Null),
            Expr::Bool(b) => Ok(Omega::Bool(*b)),
            Expr::Number(n) => Ok(Omega::Number(*n)),
            Expr::Str(s) => Ok(Omega::Str(s.clone())),
            Expr::Var(name) => Ok(self.env.get(name).cloned().unwrap_or(Omega::Null)),
            Expr::List(items) => {
                let mut out = Vec::with_capacity(items.len());
                for item in items {
                    out.push(self.eval_expr(item)?);
                }
                Ok(Omega::List(out))
            }
            Expr::Table(entries) => {
                let mut map = HashMap::with_capacity(entries.len());
                for (k_expr, v_expr) in entries {
                    let k = match k_expr {
                        Expr::Var(ident) if !self.env.contains_key(ident) => ident.clone(),
                        _ => self.eval_expr(k_expr)?.as_str_value(),
                    };
                    let v = self.eval_expr(v_expr)?;
                    map.insert(k, v);
                }
                Ok(Omega::Table(map))
            }
            Expr::Index { target, index } => {
                let t = self.eval_expr(target)?;
                let idx = self.eval_expr(index)?;
                Ok(t.get_index(&idx))
            }
            Expr::Binary { left, op, right } => {
                let l = self.eval_expr(left)?;
                let r = self.eval_expr(right)?;
                self.eval_binary(&l, *op, &r)
            }
            Expr::Analyse {
                target,
                condition,
                pattern,
            } => {
                let t = self.eval_expr(target)?;
                let p = self.eval_expr(pattern)?;
                Ok(t.analyse(condition, &p))
            }
            Expr::Exec(cmd_expr) => {
                let cmd_str = self.eval_expr(cmd_expr)?.as_str_value();
                self.exec_command(&cmd_str)
            }
        }
    }

    fn eval_binary(&self, left: &Omega, op: BinOp, right: &Omega) -> Result<Omega, String> {
        match op {
            BinOp::Add => match (left, right) {
                (Omega::Number(a), Omega::Number(b)) => Ok(Omega::Number(a + b)),
                (Omega::List(a), Omega::List(b)) => {
                    let mut combined = a.clone();
                    combined.extend(b.clone());
                    Ok(Omega::List(combined))
                }
                _ => Ok(Omega::Str(format!(
                    "{}{}",
                    left.as_str_value(),
                    right.as_str_value()
                ))),
            },
            BinOp::Sub => {
                let a = left.as_number().unwrap_or(0.0);
                let b = right.as_number().unwrap_or(0.0);
                Ok(Omega::Number(a - b))
            }
            BinOp::Mul => {
                let a = left.as_number().unwrap_or(0.0);
                let b = right.as_number().unwrap_or(0.0);
                Ok(Omega::Number(a * b))
            }
            BinOp::Div => {
                let a = left.as_number().unwrap_or(0.0);
                let b = right.as_number().unwrap_or(0.0);
                if b == 0.0 {
                    Err("Divisão por zero".to_string())
                } else {
                    Ok(Omega::Number(a / b))
                }
            }
            BinOp::Eq => Ok(Omega::Bool(left.equals_loose(right))),
            BinOp::Ne => Ok(Omega::Bool(!left.equals_loose(right))),
            BinOp::Gt => Ok(left.analyse(">", right)),
            BinOp::Lt => Ok(left.analyse("<", right)),
            BinOp::Ge => Ok(left.analyse(">=", right)),
            BinOp::Le => Ok(left.analyse("<=", right)),
        }
    }

    fn exec_command(&self, cmd: &str) -> Result<Omega, String> {
        let output = Command::new("sh")
            .arg("-c")
            .arg(cmd)
            .output()
            .map_err(|e| format!("Falha ao executar comando '{}': {}", cmd, e))?;

        let stdout_str = String::from_utf8_lossy(&output.stdout).trim_end().to_string();
        let stderr_str = String::from_utf8_lossy(&output.stderr).trim_end().to_string();
        let code = output.status.code().unwrap_or(-1) as f64;
        let ok = output.status.success();

        let mut map = HashMap::new();
        map.insert("val".to_string(), Omega::Str(stdout_str.clone()));
        map.insert("stdout".to_string(), Omega::Str(stdout_str));
        map.insert("err".to_string(), Omega::Str(stderr_str.clone()));
        map.insert("stderr".to_string(), Omega::Str(stderr_str));
        map.insert("code".to_string(), Omega::Number(code));
        map.insert("ok".to_string(), Omega::Bool(ok));

        Ok(Omega::Table(map))
    }
}

