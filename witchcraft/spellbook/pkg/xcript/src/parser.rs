use crate::lexer::{SpannedToken, Token};

#[derive(Debug, Clone)]
pub enum Expr {
    Null,
    Bool(bool),
    Number(f64),
    Str(String),
    Var(String),
    List(Vec<Expr>),
    Table(Vec<(Expr, Expr)>),
    Index {
        target: Box<Expr>,
        index: Box<Expr>,
    },
    Binary {
        left: Box<Expr>,
        op: BinOp,
        right: Box<Expr>,
    },
    Analyse {
        target: Box<Expr>,
        condition: String,
        pattern: Box<Expr>,
    },
    Exec(Box<Expr>),
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum BinOp {
    Add,
    Sub,
    Mul,
    Div,
    Eq,
    Ne,
    Gt,
    Lt,
    Ge,
    Le,
}

#[derive(Debug, Clone)]
pub enum Stmt {
    Echo(Expr),
    Warn(Expr),
    WarnPair(Expr, Expr),
    Declare {
        name: String,
        value: Option<Expr>,
    },
    Assign {
        name: String,
        index: Option<Expr>,
        value: Expr,
    },
    While {
        cond: Expr,
        until: Option<Expr>,
        body: Vec<Stmt>,
    },
    ForIn {
        var: String,
        iterable: Expr,
        body: Vec<Stmt>,
    },
    ForStep {
        var: String,
        step: f64,
        until: Option<Expr>,
        body: Vec<Stmt>,
    },
    If {
        branches: Vec<(Expr, Vec<Stmt>)>,
        else_branch: Option<Vec<Stmt>>,
        default_branch: Option<Vec<Stmt>>,
    },
}

pub struct Parser {
    tokens: Vec<SpannedToken>,
    pos: usize,
}

impl Parser {
    pub fn new(tokens: Vec<SpannedToken>) -> Self {
        Self { tokens, pos: 0 }
    }

    fn peek(&self) -> &Token {
        self.tokens
            .get(self.pos)
            .map(|t| &t.token)
            .unwrap_or(&Token::Eof)
    }

    fn peek_at(&self, offset: usize) -> &Token {
        self.tokens
            .get(self.pos + offset)
            .map(|t| &t.token)
            .unwrap_or(&Token::Eof)
    }

    fn line(&self) -> usize {
        self.tokens.get(self.pos).map(|t| t.line).unwrap_or(0)
    }

    fn advance(&mut self) -> Token {
        let tok = self.peek().clone();
        if self.pos < self.tokens.len() {
            self.pos += 1;
        }
        tok
    }

    fn skip_separators(&mut self) {
        while matches!(self.peek(), Token::Newline | Token::Semicolon) {
            self.advance();
        }
    }

    fn skip_stmt_end(&mut self) {
        while matches!(self.peek(), Token::Newline | Token::Semicolon) {
            self.advance();
        }
    }

    pub fn parse_program(&mut self) -> Result<Vec<Stmt>, String> {
        let mut stmts = Vec::new();
        self.skip_separators();
        while !matches!(self.peek(), Token::Eof) {
            stmts.push(self.parse_stmt()?);
            self.skip_separators();
        }
        Ok(stmts)
    }

    fn parse_stmt(&mut self) -> Result<Stmt, String> {
        self.skip_separators();
        match self.peek().clone() {
            Token::Echo => {
                self.advance();
                let expr = self.parse_expr()?;
                self.skip_stmt_end();
                Ok(Stmt::Echo(expr))
            }
            Token::Warn => {
                self.advance();
                if matches!(self.peek(), Token::LBracket) {
                    self.advance(); // consume '['
                    let val = self.parse_expr()?;
                    if matches!(self.peek(), Token::Comma) {
                        self.advance();
                        let err = self.parse_expr()?;
                        if !matches!(self.peek(), Token::RBracket) {
                            return Err(format!(
                                "Linha {}: esperado ']' após warn[val, err]",
                                self.line()
                            ));
                        }
                        self.advance();
                        self.skip_stmt_end();
                        Ok(Stmt::WarnPair(val, err))
                    } else {
                        if !matches!(self.peek(), Token::RBracket) {
                            return Err(format!(
                                "Linha {}: esperado ']' após warn[val]",
                                self.line()
                            ));
                        }
                        self.advance();
                        self.skip_stmt_end();
                        Ok(Stmt::Warn(val))
                    }
                } else {
                    let expr = self.parse_expr()?;
                    self.skip_stmt_end();
                    Ok(Stmt::Warn(expr))
                }
            }
            Token::Declare => {
                self.advance();
                let name = self.expect_ident("nome de variável após 'declare'")?;
                if matches!(self.peek(), Token::Assign) {
                    self.advance();
                    let val = self.parse_expr()?;
                    self.skip_stmt_end();
                    Ok(Stmt::Declare {
                        name,
                        value: Some(val),
                    })
                } else {
                    self.skip_stmt_end();
                    Ok(Stmt::Declare { name, value: None })
                }
            }
            Token::While => {
                self.advance();
                let cond = self.parse_expr()?;
                let until = if matches!(self.peek(), Token::Until) {
                    self.advance();
                    Some(self.parse_expr()?)
                } else {
                    None
                };
                let body = self.parse_block(&[Token::End])?;
                if matches!(self.peek(), Token::End) {
                    self.advance();
                }
                self.skip_stmt_end();
                Ok(Stmt::While { cond, until, body })
            }
            Token::For => {
                self.advance();
                let var = self.expect_ident("variável de iteração após 'for'")?;
                if !matches!(self.peek(), Token::In) {
                    return Err(format!(
                        "Linha {}: esperado 'in' após 'for {}'",
                        self.line(),
                        var
                    ));
                }
                self.advance();

                // Check for `for x in x++1` or `for x in x--1`
                if let Token::Ident(next_id) = self.peek().clone() {
                    if next_id == var
                        && matches!(self.peek_at(1), Token::PlusPlus | Token::MinusMinus)
                    {
                        self.advance(); // consume ident
                        let sign = match self.advance() {
                            Token::PlusPlus => 1.0,
                            Token::MinusMinus => -1.0,
                            _ => 1.0,
                        };
                        let mag = match self.peek().clone() {
                            Token::Number(n) => {
                                self.advance();
                                n
                            }
                            _ => 1.0,
                        };
                        let until = if matches!(self.peek(), Token::Until) {
                            self.advance();
                            Some(self.parse_expr()?)
                        } else {
                            None
                        };
                        let body = self.parse_block(&[Token::End])?;
                        if matches!(self.peek(), Token::End) {
                            self.advance();
                        }
                        self.skip_stmt_end();
                        return Ok(Stmt::ForStep {
                            var,
                            step: sign * mag,
                            until,
                            body,
                        });
                    }
                }

                let iterable = self.parse_expr()?;
                let body = self.parse_block(&[Token::End])?;
                if matches!(self.peek(), Token::End) {
                    self.advance();
                }
                self.skip_stmt_end();
                Ok(Stmt::ForIn {
                    var,
                    iterable,
                    body,
                })
            }
            Token::If => {
                self.advance();
                let cond = self.parse_expr()?;
                let first_body = self.parse_block(&[
                    Token::Elif,
                    Token::Else,
                    Token::Default,
                    Token::End,
                ])?;
                let mut branches = vec![(cond, first_body)];
                let mut else_branch = None;
                let mut default_branch = None;

                self.skip_separators();
                while matches!(self.peek(), Token::Elif) {
                    self.advance();
                    let elif_cond = self.parse_expr()?;
                    let elif_body = self.parse_block(&[
                        Token::Elif,
                        Token::Else,
                        Token::Default,
                        Token::End,
                    ])?;
                    branches.push((elif_cond, elif_body));
                    self.skip_separators();
                }

                if matches!(self.peek(), Token::Else) {
                    self.advance();
                    let body = self.parse_block(&[Token::Default, Token::End])?;
                    else_branch = Some(body);
                    self.skip_separators();
                }

                if matches!(self.peek(), Token::Default) {
                    self.advance();
                    let body = self.parse_block(&[Token::End])?;
                    default_branch = Some(body);
                    self.skip_separators();
                }

                if matches!(self.peek(), Token::End) {
                    self.advance();
                }
                self.skip_stmt_end();

                Ok(Stmt::If {
                    branches,
                    else_branch,
                    default_branch,
                })
            }
            Token::Ident(name) => {
                self.advance();
                let index = if matches!(self.peek(), Token::LBracket) {
                    self.advance();
                    let idx_expr = self.parse_expr()?;
                    if !matches!(self.peek(), Token::RBracket) {
                        return Err(format!(
                            "Linha {}: esperado ']' após índice de '{}'",
                            self.line(),
                            name
                        ));
                    }
                    self.advance();
                    Some(idx_expr)
                } else {
                    None
                };

                if matches!(self.peek(), Token::Assign) {
                    self.advance();
                    let value = self.parse_expr()?;
                    self.skip_stmt_end();
                    Ok(Stmt::Assign { name, index, value })
                } else if matches!(self.peek(), Token::PlusPlus) {
                    self.advance();
                    let step = match self.peek().clone() {
                        Token::Number(n) => {
                            self.advance();
                            n
                        }
                        _ => 1.0,
                    };
                    self.skip_stmt_end();
                    Ok(Stmt::Assign {
                        name: name.clone(),
                        index: None,
                        value: Expr::Binary {
                            left: Box::new(Expr::Var(name)),
                            op: BinOp::Add,
                            right: Box::new(Expr::Number(step)),
                        },
                    })
                } else if matches!(self.peek(), Token::MinusMinus) {
                    self.advance();
                    let step = match self.peek().clone() {
                        Token::Number(n) => {
                            self.advance();
                            n
                        }
                        _ => 1.0,
                    };
                    self.skip_stmt_end();
                    Ok(Stmt::Assign {
                        name: name.clone(),
                        index: None,
                        value: Expr::Binary {
                            left: Box::new(Expr::Var(name)),
                            op: BinOp::Sub,
                            right: Box::new(Expr::Number(step)),
                        },
                    })
                } else {
                    Err(format!(
                        "Linha {}: instrução inválida após identificador '{}'",
                        self.line(),
                        name
                    ))
                }
            }
            other => Err(format!(
                "Linha {}: token inesperado no início da instrução: {:?}",
                self.line(),
                other
            )),
        }
    }

    fn parse_block(&mut self, stop_tokens: &[Token]) -> Result<Vec<Stmt>, String> {
        self.skip_separators();
        if matches!(self.peek(), Token::LBrace) {
            self.advance(); // consume '{'
            let mut stmts = Vec::new();
            self.skip_separators();
            while !matches!(self.peek(), Token::RBrace | Token::Eof) {
                stmts.push(self.parse_stmt()?);
                self.skip_separators();
            }
            if !matches!(self.peek(), Token::RBrace) {
                return Err(format!("Linha {}: esperado '}}' para fechar bloco", self.line()));
            }
            self.advance(); // consume '}'
            Ok(stmts)
        } else {
            let mut stmts = Vec::new();
            self.skip_separators();
            while !matches!(self.peek(), Token::Eof)
                && !stop_tokens.iter().any(|t| t == self.peek())
            {
                stmts.push(self.parse_stmt()?);
                self.skip_separators();
            }
            Ok(stmts)
        }
    }

    fn expect_ident(&mut self, context: &str) -> Result<String, String> {
        match self.peek().clone() {
            Token::Ident(name) => {
                self.advance();
                Ok(name)
            }
            other => Err(format!(
                "Linha {}: esperado {}, encontrado {:?}",
                self.line(),
                context,
                other
            )),
        }
    }

    fn parse_expr(&mut self) -> Result<Expr, String> {
        if matches!(self.peek(), Token::Analyse) {
            self.advance();
            let target = self.parse_primary()?;
            let condition = match self.peek().clone() {
                Token::Ident(s) => {
                    self.advance();
                    s
                }
                Token::Eq => {
                    self.advance();
                    "==".to_string()
                }
                Token::Ne => {
                    self.advance();
                    "!=".to_string()
                }
                Token::Gt => {
                    self.advance();
                    ">".to_string()
                }
                Token::Lt => {
                    self.advance();
                    "<".to_string()
                }
                Token::Ge => {
                    self.advance();
                    ">=".to_string()
                }
                Token::Le => {
                    self.advance();
                    "<=".to_string()
                }
                Token::In => {
                    self.advance();
                    "in".to_string()
                }
                _ => "condition".to_string(),
            };
            let pattern = self.parse_comparison()?;
            return Ok(Expr::Analyse {
                target: Box::new(target),
                condition,
                pattern: Box::new(pattern),
            });
        }

        if matches!(self.peek(), Token::Exec) {
            self.advance();
            let cmd = self.parse_comparison()?;
            return Ok(Expr::Exec(Box::new(cmd)));
        }

        self.parse_comparison()
    }

    fn parse_comparison(&mut self) -> Result<Expr, String> {
        let mut left = self.parse_additive()?;
        loop {
            let op = match self.peek() {
                Token::Eq => Some(BinOp::Eq),
                Token::Ne => Some(BinOp::Ne),
                Token::Gt => Some(BinOp::Gt),
                Token::Lt => Some(BinOp::Lt),
                Token::Ge => Some(BinOp::Ge),
                Token::Le => Some(BinOp::Le),
                _ => None,
            };
            if let Some(op) = op {
                self.advance();
                let right = self.parse_additive()?;
                left = Expr::Binary {
                    left: Box::new(left),
                    op,
                    right: Box::new(right),
                };
            } else {
                break;
            }
        }
        Ok(left)
    }

    fn parse_additive(&mut self) -> Result<Expr, String> {
        let mut left = self.parse_multiplicative()?;
        loop {
            let op = match self.peek() {
                Token::Plus => Some(BinOp::Add),
                Token::Minus => Some(BinOp::Sub),
                _ => None,
            };
            if let Some(op) = op {
                self.advance();
                let right = self.parse_multiplicative()?;
                left = Expr::Binary {
                    left: Box::new(left),
                    op,
                    right: Box::new(right),
                };
            } else {
                break;
            }
        }
        Ok(left)
    }

    fn parse_multiplicative(&mut self) -> Result<Expr, String> {
        let mut left = self.parse_postfix()?;
        loop {
            let op = match self.peek() {
                Token::Star => Some(BinOp::Mul),
                Token::Slash => Some(BinOp::Div),
                _ => None,
            };
            if let Some(op) = op {
                self.advance();
                let right = self.parse_postfix()?;
                left = Expr::Binary {
                    left: Box::new(left),
                    op,
                    right: Box::new(right),
                };
            } else {
                break;
            }
        }
        Ok(left)
    }

    fn parse_postfix(&mut self) -> Result<Expr, String> {
        let mut expr = self.parse_primary()?;
        while matches!(self.peek(), Token::LBracket) {
            self.advance();
            let index = self.parse_expr()?;
            if !matches!(self.peek(), Token::RBracket) {
                return Err(format!("Linha {}: esperado ']'", self.line()));
            }
            self.advance();
            expr = Expr::Index {
                target: Box::new(expr),
                index: Box::new(index),
            };
        }
        Ok(expr)
    }

    fn parse_primary(&mut self) -> Result<Expr, String> {
        match self.peek().clone() {
            Token::Null => {
                self.advance();
                Ok(Expr::Null)
            }
            Token::True => {
                self.advance();
                Ok(Expr::Bool(true))
            }
            Token::False => {
                self.advance();
                Ok(Expr::Bool(false))
            }
            Token::Number(n) => {
                self.advance();
                Ok(Expr::Number(n))
            }
            Token::Minus => {
                self.advance();
                let inner = self.parse_primary()?;
                Ok(Expr::Binary {
                    left: Box::new(Expr::Number(0.0)),
                    op: BinOp::Sub,
                    right: Box::new(inner),
                })
            }
            Token::Str(s) => {
                self.advance();
                Ok(Expr::Str(s))
            }
            Token::Ident(name) => {
                self.advance();
                Ok(Expr::Var(name))
            }
            Token::LParen => {
                self.advance();
                let expr = self.parse_expr()?;
                if !matches!(self.peek(), Token::RParen) {
                    return Err(format!("Linha {}: esperado ')'", self.line()));
                }
                self.advance();
                Ok(expr)
            }
            Token::LBracket => {
                self.advance();
                let mut items = Vec::new();
                while !matches!(self.peek(), Token::RBracket | Token::Eof) {
                    items.push(self.parse_expr()?);
                    if matches!(self.peek(), Token::Comma) {
                        self.advance();
                    } else {
                        break;
                    }
                }
                if !matches!(self.peek(), Token::RBracket) {
                    return Err(format!("Linha {}: esperado ']'", self.line()));
                }
                self.advance();
                Ok(Expr::List(items))
            }
            Token::Table => {
                self.advance();
                if !matches!(self.peek(), Token::LBracket) {
                    return Err(format!(
                        "Linha {}: esperado '[' após 'table'",
                        self.line()
                    ));
                }
                self.advance();
                let mut entries = Vec::new();
                while !matches!(self.peek(), Token::RBracket | Token::Eof) {
                    let key = match self.peek().clone() {
                        Token::Ident(k) if matches!(self.peek_at(1), Token::Colon | Token::Assign) => {
                            self.advance();
                            Expr::Str(k)
                        }
                        _ => self.parse_expr()?,
                    };

                    if matches!(self.peek(), Token::Colon | Token::Assign) {
                        self.advance();
                        let val = self.parse_expr()?;
                        entries.push((key, val));
                    } else if matches!(self.peek(), Token::Comma) {
                        // Support `table[x, y]` pair syntax from define.config line 3
                        self.advance();
                        if matches!(self.peek(), Token::RBracket) {
                            entries.push((Expr::Str("0".to_string()), key));
                            break;
                        }
                        let val = self.parse_expr()?;
                        entries.push((key, val));
                    } else {
                        entries.push((Expr::Str(entries.len().to_string()), key));
                    }

                    if matches!(self.peek(), Token::Comma) {
                        self.advance();
                    }
                }
                if !matches!(self.peek(), Token::RBracket) {
                    return Err(format!("Linha {}: esperado ']' após table[...]", self.line()));
                }
                self.advance();
                Ok(Expr::Table(entries))
            }
            other => Err(format!(
                "Linha {}: expressão inesperada {:?}",
                self.line(),
                other
            )),
        }
    }
}

