mod interpreter;
mod lexer;
mod omega;
mod parser;

use std::env;
use std::fs;
use std::process;

use interpreter::Interpreter;
use lexer::tokenize;
use parser::Parser;

pub fn execute_source(source: &str) -> Result<Interpreter, String> {
    let tokens = tokenize(source)?;
    let mut parser = Parser::new(tokens);
    let program = parser.parse_program()?;
    let mut interpreter = Interpreter::new();
    interpreter.run(&program)?;
    Ok(interpreter)
}

fn print_usage(bin: &str) {
    eprintln!("Witchcraft-Xcript (static runtime)");
    eprintln!("Uso:");
    eprintln!("  {} <arquivo.xcript>", bin);
    eprintln!("  {} -e \"<codigo xcript>\"", bin);
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let bin_name = args.first().map(|s| s.as_str()).unwrap_or("xcript");

    if args.len() < 2 {
        print_usage(bin_name);
        process::exit(1);
    }

    let source = match args[1].as_str() {
        "-h" | "--help" => {
            print_usage(bin_name);
            return;
        }
        "-v" | "--version" => {
            println!("xcript {}", env!("CARGO_PKG_VERSION"));
            return;
        }
        "-e" | "--eval" => {
            if args.len() < 3 {
                eprintln!("Erro: esperado código após '{}'", args[1]);
                process::exit(1);
            }
            args[2..].join(" ")
        }
        file_path => match fs::read_to_string(file_path) {
            Ok(content) => content,
            Err(err) => {
                eprintln!("Erro ao ler arquivo '{}': {}", file_path, err);
                process::exit(1);
            }
        },
    };

    if let Err(err) = execute_source(&source) {
        eprintln!("[xcript runtime error] {}", err);
        process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::omega::Omega;

    #[test]
    fn test_declarations_and_omega_types() {
        let src = r#"
            declare s = "cyberdeck"
            declare arr = [1, 2, "three"]
            declare tbl = table["host", "127.0.0.1"]
            declare empty;
        "#;
        let interp = execute_source(src).expect("should execute declarations");
        assert_eq!(interp.env.get("s"), Some(&Omega::Str("cyberdeck".into())));
        assert_eq!(interp.env.get("empty"), Some(&Omega::Null));
        if let Some(Omega::Table(map)) = interp.env.get("tbl") {
            assert_eq!(map.get("host"), Some(&Omega::Str("127.0.0.1".into())));
        } else {
            panic!("expected Omega::Table");
        }
    }

    #[test]
    fn test_while_until_and_for_loops() {
        let src = r#"
            declare x = 0
            while true until x == 3 {
                x = x + 1
            }

            declare sum = 0
            declare items = [10, 20, 30]
            for item in items {
                sum = sum + item
            }

            declare c = 0
            for c in c++1 until c == 4 {
                echo c
            }

            declare d = 5
            for d in d--1 until d == 2 {
                echo d
            }
        "#;
        let interp = execute_source(src).expect("loops should succeed");
        assert_eq!(interp.env.get("x"), Some(&Omega::Number(3.0)));
        assert_eq!(interp.env.get("sum"), Some(&Omega::Number(60.0)));
        assert_eq!(interp.env.get("c"), Some(&Omega::Number(4.0)));
        assert_eq!(interp.env.get("d"), Some(&Omega::Number(2.0)));
    }

    #[test]
    fn test_conditionals_with_default() {
        let src = r#"
            declare mode = "stealth"
            declare out = ""
            if mode == "loud" {
                out = "loud_mode"
            } elif mode == "passive" {
                out = "passive_mode"
            } default {
                out = "fallback_default"
            }
        "#;
        let interp = execute_source(src).expect("conditionals should succeed");
        assert_eq!(
            interp.env.get("out"),
            Some(&Omega::Str("fallback_default".into()))
        );
    }

    #[test]
    fn test_pattern_analyse() {
        let src = r#"
            declare X = "witchcraft_fex_runner"
            declare res;
            res = analyse X condition "fex"

            declare num = 42
            declare res_num = analyse num condition 42
        "#;
        let interp = execute_source(src).expect("analyse should succeed");
        assert_eq!(interp.env.get("res"), Some(&Omega::Bool(true)));
        assert_eq!(interp.env.get("res_num"), Some(&Omega::Bool(true)));
    }

    #[test]
    fn test_exec_and_warn() {
        let src = r#"
            declare res = table[];
            res = exec "printf 'hello_xcript'"
            warn res
            warn["stdout_msg", "stderr_msg"]
        "#;
        let interp = execute_source(src).expect("exec should succeed");
        if let Some(Omega::Table(map)) = interp.env.get("res") {
            assert_eq!(map.get("val"), Some(&Omega::Str("hello_xcript".into())));
            assert_eq!(map.get("ok"), Some(&Omega::Bool(true)));
        } else {
            panic!("expected table from exec");
        }
    }
}

