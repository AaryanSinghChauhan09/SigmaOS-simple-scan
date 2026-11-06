//! SigmaOS-simple-scan: Document scanner library
//!
//! Provides scanner device discovery, image acquisition,
//! and document export functionality for SigmaOS.


/// Initialize the scanning subsystem
pub fn init() {
    // TODO: initialize SANE backend
}

pub mod document;
pub mod format;
