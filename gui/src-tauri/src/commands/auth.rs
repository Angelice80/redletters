//! Keychain access for auth token (ADR-005).
//!
//! Service name: com.redletters.engine
//! Account: auth_token
//! Token prefix: rl_
//! Fallback: ~/.greek2english/.auth_token (0600 perms)

use keyring::Entry;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use thiserror::Error;

/// Service name for keychain storage
const KEYCHAIN_SERVICE: &str = "com.redletters.engine";
/// Account name for auth token
const KEYCHAIN_ACCOUNT: &str = "auth_token";
/// Expected token prefix
const TOKEN_PREFIX: &str = "rl_";

#[derive(Debug, Serialize, Deserialize)]
pub struct AuthToken {
    pub token: String,
    pub source: String,
}

#[derive(Debug, Error)]
pub enum AuthError {
    #[error("Token not found in keychain or file")]
    NotFound,
    #[error("Invalid token format (must start with rl_)")]
    InvalidFormat,
    #[error("Keychain error: {0}")]
    KeychainError(String),
    #[error("File error: {0}")]
    FileError(String),
}

impl Serialize for AuthError {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(&self.to_string())
    }
}

/// Get the fallback token file path: ~/.greek2english/.auth_token
fn get_fallback_path() -> Option<PathBuf> {
    dirs::home_dir().map(|home| home.join(".greek2english").join(".auth_token"))
}

/// Validate token format
fn validate_token(token: &str) -> Result<(), AuthError> {
    if token.starts_with(TOKEN_PREFIX) && token.len() >= 24 {
        Ok(())
    } else {
        Err(AuthError::InvalidFormat)
    }
}

/// Try to get token from OS keychain
fn try_keychain() -> Result<String, AuthError> {
    let entry = Entry::new(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
        .map_err(|e| AuthError::KeychainError(e.to_string()))?;

    entry
        .get_password()
        .map_err(|_| AuthError::NotFound)
}

/// Try to get token from fallback file
fn try_fallback_file() -> Result<String, AuthError> {
    let path = get_fallback_path().ok_or(AuthError::NotFound)?;

    if !path.exists() {
        return Err(AuthError::NotFound);
    }

    // Check permissions on Unix
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let metadata = fs::metadata(&path).map_err(|e| AuthError::FileError(e.to_string()))?;
        let mode = metadata.permissions().mode();
        // Warn but don't fail if permissions are too open
        if mode & 0o077 != 0 {
            eprintln!(
                "Warning: {} has permissions {:o}, should be 0600",
                path.display(),
                mode & 0o777
            );
        }
    }

    fs::read_to_string(&path)
        .map(|s| s.trim().to_string())
        .map_err(|e| AuthError::FileError(e.to_string()))
}

/// Get auth token from keychain or fallback file.
///
/// Tries keychain first, then ~/.greek2english/.auth_token
#[tauri::command]
pub fn get_auth_token() -> Result<AuthToken, AuthError> {
    // Try keychain first
    if let Ok(token) = try_keychain() {
        validate_token(&token)?;
        return Ok(AuthToken {
            token,
            source: "keychain".to_string(),
        });
    }

    // Try fallback file
    if let Ok(token) = try_fallback_file() {
        validate_token(&token)?;
        return Ok(AuthToken {
            token,
            source: "file".to_string(),
        });
    }

    Err(AuthError::NotFound)
}

/// Store auth token in OS keychain.
#[tauri::command]
pub fn set_auth_token(token: String) -> Result<(), AuthError> {
    validate_token(&token)?;

    let entry = Entry::new(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
        .map_err(|e| AuthError::KeychainError(e.to_string()))?;

    entry
        .set_password(&token)
        .map_err(|e| AuthError::KeychainError(e.to_string()))?;

    Ok(())
}

/// Delete auth token from keychain.
#[tauri::command]
pub fn delete_auth_token() -> Result<(), AuthError> {
    let entry = Entry::new(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
        .map_err(|e| AuthError::KeychainError(e.to_string()))?;

    entry
        .delete_password()
        .map_err(|e| AuthError::KeychainError(e.to_string()))?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validate_token() {
        assert!(validate_token("rl_abcdefghij1234567890").is_ok());
        assert!(validate_token("invalid_token").is_err());
        assert!(validate_token("rl_short").is_err());
    }
}
