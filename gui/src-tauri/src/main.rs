//! Red Letters Desktop GUI - Tauri backend entry point.
//!
//! This is a minimal Tauri app that provides:
//! - Keychain access for auth tokens (ADR-005)
//! - Engine process management helpers
//!
//! The actual API communication happens in the React frontend.

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

mod commands;

use commands::{
    check_engine_running, delete_auth_token, get_auth_token, get_engine_command_hint,
    set_auth_token, start_engine_safe_mode,
};
use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            get_auth_token,
            set_auth_token,
            delete_auth_token,
            check_engine_running,
            start_engine_safe_mode,
            get_engine_command_hint,
        ])
        .setup(|app| {
            #[cfg(debug_assertions)]
            {
                // Open devtools in debug builds
                if let Some(w) = app.get_webview_window("main") {
                    w.open_devtools();
                }
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
