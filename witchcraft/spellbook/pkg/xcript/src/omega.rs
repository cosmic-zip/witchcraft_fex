use std::collections::HashMap;
use std::fmt;

/// Omega type: unified dynamic data structure acting as `any`, list, or hashmap (`table[x, y]`).
#[derive(Debug, Clone, PartialEq)]
pub enum Omega {
    Null,
    Bool(bool),
    Number(f64),
    Str(String),
    List(Vec<Omega>),
    Table(HashMap<String, Omega>),
}

impl Omega {
    pub fn empty_table() -> Self {
        Omega::Table(HashMap::new())
    }

    pub fn is_truthy(&self) -> bool {
        match self {
            Omega::Null => false,
            Omega::Bool(b) => *b,
            Omega::Number(n) => *n != 0.0 && !n.is_nan(),
            Omega::Str(s) => !s.is_empty() && s != "false" && s != "0",
            Omega::List(items) => !items.is_empty(),
            Omega::Table(map) => {
                if let Some(ok) = map.get("ok") {
                    return ok.is_truthy();
                }
                !map.is_empty()
            }
        }
    }

    pub fn as_number(&self) -> Option<f64> {
        match self {
            Omega::Number(n) => Some(*n),
            Omega::Bool(b) => Some(if *b { 1.0 } else { 0.0 }),
            Omega::Str(s) => s.trim().parse::<f64>().ok(),
            _ => None,
        }
    }

    pub fn as_str_value(&self) -> String {
        match self {
            Omega::Null => String::new(),
            Omega::Bool(b) => b.to_string(),
            Omega::Number(n) => {
                if n.fract() == 0.0 {
                    format!("{:.0}", n)
                } else {
                    n.to_string()
                }
            }
            Omega::Str(s) => s.clone(),
            Omega::List(items) => {
                let parts: Vec<String> = items.iter().map(|i| i.as_str_value()).collect();
                format!("[{}]", parts.join(", "))
            }
            Omega::Table(map) => {
                let mut pairs: Vec<String> = map
                    .iter()
                    .map(|(k, v)| format!("{}: {}", k, v.as_str_value()))
                    .collect();
                pairs.sort();
                format!("table[{}]", pairs.join(", "))
            }
        }
    }

    pub fn get_index(&self, key: &Omega) -> Omega {
        match self {
            Omega::List(items) => {
                if let Some(n) = key.as_number() {
                    let idx = if n < 0.0 {
                        (items.len() as isize + n as isize) as usize
                    } else {
                        n as usize
                    };
                    items.get(idx).cloned().unwrap_or(Omega::Null)
                } else {
                    Omega::Null
                }
            }
            Omega::Table(map) => {
                let k = key.as_str_value();
                map.get(&k).cloned().unwrap_or(Omega::Null)
            }
            Omega::Str(s) => {
                if let Some(n) = key.as_number() {
                    let idx = n as usize;
                    s.chars()
                        .nth(idx)
                        .map(|c| Omega::Str(c.to_string()))
                        .unwrap_or(Omega::Null)
                } else {
                    Omega::Null
                }
            }
            _ => Omega::Null,
        }
    }

    pub fn set_index(&mut self, key: &Omega, val: Omega) {
        match self {
            Omega::List(items) => {
                if let Some(n) = key.as_number() {
                    let idx = n as usize;
                    if idx < items.len() {
                        items[idx] = val;
                    } else if idx == items.len() {
                        items.push(val);
                    }
                }
            }
            Omega::Table(map) => {
                map.insert(key.as_str_value(), val);
            }
            _ => {}
        }
    }

    /// Evaluates `analyse X <condition> <pattern>` according to `define.config`.
    pub fn analyse(&self, condition: &str, pattern: &Omega) -> Omega {
        let cond = condition.trim().to_ascii_lowercase();
        let matched = match cond.as_str() {
            "==" | "eq" | "is" | "equals" => self.equals_loose(pattern),
            "!=" | "ne" | "not" => !self.equals_loose(pattern),
            ">" | "gt" => match (self.as_number(), pattern.as_number()) {
                (Some(a), Some(b)) => a > b,
                _ => self.as_str_value() > pattern.as_str_value(),
            },
            "<" | "lt" => match (self.as_number(), pattern.as_number()) {
                (Some(a), Some(b)) => a < b,
                _ => self.as_str_value() < pattern.as_str_value(),
            },
            ">=" | "ge" => match (self.as_number(), pattern.as_number()) {
                (Some(a), Some(b)) => a >= b,
                _ => self.as_str_value() >= pattern.as_str_value(),
            },
            "<=" | "le" => match (self.as_number(), pattern.as_number()) {
                (Some(a), Some(b)) => a <= b,
                _ => self.as_str_value() <= pattern.as_str_value(),
            },
            "contains" | "has" | "match" | "matches" => self.contains_pattern(pattern),
            "starts_with" | "startswith" | "prefix" => self
                .as_str_value()
                .starts_with(&pattern.as_str_value()),
            "ends_with" | "endswith" | "suffix" => self
                .as_str_value()
                .ends_with(&pattern.as_str_value()),
            "in" => pattern.contains_pattern(self),
            // Default `condition` keyword in `res = analyse X condition {pattern string or number}`
            "condition" | _ => {
                if self.equals_loose(pattern) {
                    true
                } else {
                    self.contains_pattern(pattern)
                }
            }
        };
        Omega::Bool(matched)
    }

    pub fn equals_loose(&self, other: &Omega) -> bool {
        match (self, other) {
            (Omega::Null, Omega::Null) => true,
            (Omega::Bool(a), Omega::Bool(b)) => a == b,
            (Omega::Number(a), Omega::Number(b)) => (a - b).abs() < f64::EPSILON,
            (Omega::Str(a), Omega::Str(b)) => a == b,
            (Omega::List(a), Omega::List(b)) => a == b,
            (Omega::Table(a), Omega::Table(b)) => a == b,
            _ => {
                if let (Some(a), Some(b)) = (self.as_number(), other.as_number()) {
                    (a - b).abs() < f64::EPSILON
                } else {
                    self.as_str_value() == other.as_str_value()
                }
            }
        }
    }

    pub fn contains_pattern(&self, pattern: &Omega) -> bool {
        match self {
            Omega::Str(s) => s.contains(&pattern.as_str_value()),
            Omega::List(items) => items.iter().any(|item| item.equals_loose(pattern)),
            Omega::Table(map) => {
                let pat_str = pattern.as_str_value();
                map.contains_key(&pat_str) || map.values().any(|v| v.equals_loose(pattern))
            }
            Omega::Number(_) => self.equals_loose(pattern),
            Omega::Bool(_) => self.equals_loose(pattern),
            Omega::Null => matches!(pattern, Omega::Null),
        }
    }
}

impl fmt::Display for Omega {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.as_str_value())
    }
}

