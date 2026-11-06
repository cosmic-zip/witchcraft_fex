#[derive(Debug, Clone, PartialEq)]
pub enum Token {
    // Keywords
    Echo,
    Warn,
    Declare,
    Table,
    While,
    Until,
    For,
    In,
    If,
    Elif,
    Else,
    Default,
    End,
    Analyse,
    Exec,
    True,
    False,
    Null,

    // Literals & Identifiers
    Ident(String),
    Str(String),
    Number(f64),

    // Operators & Punctuation
    Assign,     // =
    Eq,         // ==
    Ne,         // !=
    Gt,         // >
    Lt,         // <
    Ge,         // >=
    Le,         // <=
    PlusPlus,   // ++
    MinusMinus, // --
    Plus,       // +
    Minus,      // -
    Star,       // *
    Slash,      // /
    LBracket,   // [
    RBracket,   // ]
    LBrace,     // {
    RBrace,     // }
    LParen,     // (
    RParen,     // )
    Comma,      // ,
    Colon,      // :
    Semicolon,  // ;
    Newline,
    Eof,
}

#[derive(Debug, Clone)]
pub struct SpannedToken {
    pub token: Token,
    pub line: usize,
}

pub fn tokenize(source: &str) -> Result<Vec<SpannedToken>, String> {
    let mut tokens = Vec::new();
    let chars: Vec<char> = source.chars().collect();
    let mut i = 0;
    let mut line = 1;

    while i < chars.len() {
        let c = chars[i];

        match c {
            ' ' | '\t' | '\r' => {
                i += 1;
            }
            '\n' => {
                tokens.push(SpannedToken {
                    token: Token::Newline,
                    line,
                });
                line += 1;
                i += 1;
            }
            '#' => {
                while i < chars.len() && chars[i] != '\n' {
                    i += 1;
                }
            }
            ';' => {
                tokens.push(SpannedToken {
                    token: Token::Semicolon,
                    line,
                });
                i += 1;
            }
            ',' => {
                tokens.push(SpannedToken {
                    token: Token::Comma,
                    line,
                });
                i += 1;
            }
            ':' => {
                tokens.push(SpannedToken {
                    token: Token::Colon,
                    line,
                });
                i += 1;
            }
            '[' => {
                tokens.push(SpannedToken {
                    token: Token::LBracket,
                    line,
                });
                i += 1;
            }
            ']' => {
                tokens.push(SpannedToken {
                    token: Token::RBracket,
                    line,
                });
                i += 1;
            }
            '{' => {
                tokens.push(SpannedToken {
                    token: Token::LBrace,
                    line,
                });
                i += 1;
            }
            '}' => {
                tokens.push(SpannedToken {
                    token: Token::RBrace,
                    line,
                });
                i += 1;
            }
            '(' => {
                tokens.push(SpannedToken {
                    token: Token::LParen,
                    line,
                });
                i += 1;
            }
            ')' => {
                tokens.push(SpannedToken {
                    token: Token::RParen,
                    line,
                });
                i += 1;
            }
            '=' => {
                if i + 1 < chars.len() && chars[i + 1] == '=' {
                    tokens.push(SpannedToken {
                        token: Token::Eq,
                        line,
                    });
                    i += 2;
                } else {
                    tokens.push(SpannedToken {
                        token: Token::Assign,
                        line,
                    });
                    i += 1;
                }
            }
            '!' => {
                if i + 1 < chars.len() && chars[i + 1] == '=' {
                    tokens.push(SpannedToken {
                        token: Token::Ne,
                        line,
                    });
                    i += 2;
                } else {
                    return Err(format!("Linha {}: caractere inesperado '!'", line));
                }
            }
            '>' => {
                if i + 1 < chars.len() && chars[i + 1] == '=' {
                    tokens.push(SpannedToken {
                        token: Token::Ge,
                        line,
                    });
                    i += 2;
                } else {
                    tokens.push(SpannedToken {
                        token: Token::Gt,
                        line,
                    });
                    i += 1;
                }
            }
            '<' => {
                if i + 1 < chars.len() && chars[i + 1] == '=' {
                    tokens.push(SpannedToken {
                        token: Token::Le,
                        line,
                    });
                    i += 2;
                } else {
                    tokens.push(SpannedToken {
                        token: Token::Lt,
                        line,
                    });
                    i += 1;
                }
            }
            '+' => {
                if i + 1 < chars.len() && chars[i + 1] == '+' {
                    tokens.push(SpannedToken {
                        token: Token::PlusPlus,
                        line,
                    });
                    i += 2;
                } else {
                    tokens.push(SpannedToken {
                        token: Token::Plus,
                        line,
                    });
                    i += 1;
                }
            }
            '-' => {
                if i + 1 < chars.len() && chars[i + 1] == '-' {
                    tokens.push(SpannedToken {
                        token: Token::MinusMinus,
                        line,
                    });
                    i += 2;
                } else {
                    tokens.push(SpannedToken {
                        token: Token::Minus,
                        line,
                    });
                    i += 1;
                }
            }
            '*' => {
                tokens.push(SpannedToken {
                    token: Token::Star,
                    line,
                });
                i += 1;
            }
            '/' => {
                tokens.push(SpannedToken {
                    token: Token::Slash,
                    line,
                });
                i += 1;
            }
            '"' | '\'' => {
                let quote = c;
                let start_line = line;
                i += 1;
                let mut s = String::new();
                while i < chars.len() && chars[i] != quote {
                    if chars[i] == '\n' {
                        line += 1;
                    }
                    if chars[i] == '\\' && i + 1 < chars.len() {
                        i += 1;
                        match chars[i] {
                            'n' => s.push('\n'),
                            't' => s.push('\t'),
                            'r' => s.push('\r'),
                            '\\' => s.push('\\'),
                            '"' => s.push('"'),
                            '\'' => s.push('\''),
                            other => {
                                s.push('\\');
                                s.push(other);
                            }
                        }
                    } else {
                        s.push(chars[i]);
                    }
                    i += 1;
                }
                if i >= chars.len() {
                    return Err(format!("Linha {}: string não fechada", start_line));
                }
                i += 1; // consume closing quote
                tokens.push(SpannedToken {
                    token: Token::Str(s),
                    line: start_line,
                });
            }
            d if d.is_ascii_digit() => {
                let start = i;
                while i < chars.len() && (chars[i].is_ascii_digit() || chars[i] == '.') {
                    i += 1;
                }
                let num_str: String = chars[start..i].iter().collect();
                let num = num_str.parse::<f64>().map_err(|_| {
                    format!("Linha {}: número inválido '{}'", line, num_str)
                })?;
                tokens.push(SpannedToken {
                    token: Token::Number(num),
                    line,
                });
            }
            a if a.is_ascii_alphabetic() || a == '_' => {
                let start = i;
                while i < chars.len()
                    && (chars[i].is_ascii_alphanumeric() || chars[i] == '_')
                {
                    i += 1;
                }
                let ident: String = chars[start..i].iter().collect();
                let tok = match ident.as_str() {
                    "echo" => Token::Echo,
                    "warn" => Token::Warn,
                    "declare" => Token::Declare,
                    "table" => Token::Table,
                    "while" => Token::While,
                    "until" => Token::Until,
                    "for" => Token::For,
                    "in" => Token::In,
                    "if" => Token::If,
                    "elif" => Token::Elif,
                    "else" => Token::Else,
                    "default" => Token::Default,
                    "end" => Token::End,
                    "analyse" => Token::Analyse,
                    "exec" => Token::Exec,
                    "true" => Token::True,
                    "false" => Token::False,
                    "null" => Token::Null,
                    _ => Token::Ident(ident),
                };
                tokens.push(SpannedToken { token: tok, line });
            }
            other => {
                return Err(format!(
                    "Linha {}: caractere inesperado '{}'",
                    line, other
                ));
            }
        }
    }

    tokens.push(SpannedToken {
        token: Token::Eof,
        line,
    });
    Ok(tokens)
}

