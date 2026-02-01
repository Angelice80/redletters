//! Engine process management commands.
//!
//! Provides commands for starting/stopping the engine process,
//! including safe mode restart.

use serde::{Deserialize, Serialize};
use std::process::Command;
use thiserror::Error;

#[derive(Debug, Serialize, Deserialize)]
pub struct EngineProcessInfo {
    pub running: bool,
    pub pid: Option<u32>,
    pub port: u16,
}

#[derive(Debug, Error)]
pub enum EngineError {
    #[error("Engine not running")]
    NotRunning,
    #[error("Failed to start engine: {0}")]
    StartFailed(String),
    #[error("Failed to stop engine: {0}")]
    StopFailed(String),
}

impl Serialize for EngineError {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(&self.to_string())
    }
}

/// Check if engine process is running by trying to connect to the port.
#[tauri::command]
pub fn check_engine_running(port: u16) -> EngineProcessInfo {
    // Simple check: try to connect to the port
    let running = std::net::TcpStream::connect(format!("127.0.0.1:{}", port)).is_ok();

    EngineProcessInfo {
        running,
        pid: None, // Would need more complex logic to find PID
        port,
    }
}

/// Start engine in safe mode.
///
/// Note: This spawns a new process. The GUI doesn't manage the engine lifecycle
/// directly - this is just a convenience for restarting in safe mode.
#[tauri::command]
pub fn start_engine_safe_mode(port: u16) -> Result<(), EngineError> {
    // Try to start using the redletters CLI
    let result = Command::new("redletters")
        .args(["engine", "start", "--safe-mode", "--port", &port.to_string()])
        .spawn();

    match result {
        Ok(_child) => Ok(()),
        Err(e) => Err(EngineError::StartFailed(e.to_string())),
    }
}

/// Request engine shutdown via API.
///
/// Note: This is a convenience - the actual shutdown is done via HTTP API.
/// This command just documents that the GUI can request shutdown.
#[tauri::command]
pub fn get_engine_command_hint() -> String {
    "Use API endpoint POST /v1/engine/shutdown to request graceful shutdown".to_string()
}
