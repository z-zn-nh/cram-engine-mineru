#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let sidecar = app.shell().sidecar("cram-backend");
            match sidecar {
                Ok(command) => {
                    let (mut rx, _child) = command
                        .args(["--host", "127.0.0.1", "--port", "8000"])
                        .spawn()
                        .expect("failed to spawn cram-engine backend sidecar");

                    tauri::async_runtime::spawn(async move {
                        while let Some(event) = rx.recv().await {
                            match event {
                                CommandEvent::Stdout(bytes) => {
                                    println!("[cram-backend] {}", String::from_utf8_lossy(&bytes));
                                }
                                CommandEvent::Stderr(bytes) => {
                                    eprintln!("[cram-backend] {}", String::from_utf8_lossy(&bytes));
                                }
                                _ => {}
                            }
                        }
                    });
                }
                Err(error) => {
                    eprintln!("backend sidecar is not available yet: {error}");
                }
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running cram-engine-mineru desktop app");
}
