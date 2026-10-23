//! DEP-2 夹具：领域 crate 内的 I/O 反例与允许的 time 类型。
use std::fs;
use std::net as net_alias;
use std::time::SystemTime;
use std::time::{Duration, Instant};

const DOC: &str = "字符串里的 std::fs 与 std::net 不报";

// 注释里的 std::fs 与 std::net 也不报。
pub fn metadata_len() -> usize {
    fs::metadata("x").map(|m| m.len() as usize).unwrap_or(0)
}

pub fn connect() -> u16 {
    net_alias::TcpStream::connect("127.0.0.1:1").map(|_| 1).unwrap_or(0)
}

pub fn now() -> SystemTime {
    SystemTime::now()
}

pub fn elapsed() -> Duration {
    Instant::now().elapsed()
}

pub fn qualified() -> std::io::Result<()> {
    std::fs::read("x")?;
    Ok(())
}
