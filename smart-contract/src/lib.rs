#![cfg_attr(not(test), no_std)]
#![cfg_attr(not(test), no_main)]
extern crate alloc;

pub mod errors;
pub mod events;
pub mod pool;
pub mod types;
pub mod vault;

#[cfg(test)]
mod tests;
