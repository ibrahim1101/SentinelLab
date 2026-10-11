use std::sync::Mutex;
use tauri::{Manager, RunEvent};
use tauri_plugin_shell::{process::CommandChild, ShellExt};

struct BackendProcess(Mutex<Option<CommandChild>>);

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendProcess(Mutex::new(None)))
        .setup(|app| {
            let command = app.shell().sidecar("sentinellab-api")?;
            let (_rx, child) = command.spawn()?;
            *app.state::<BackendProcess>().0.lock().expect("backend mutex poisoned") = Some(child);
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("failed to build SentinelLab desktop")
        .run(|app, event| {
            if let RunEvent::Exit = event {
                if let Some(child) = app.state::<BackendProcess>().0.lock().expect("backend mutex poisoned").take() {
                    let _ = child.kill();
                }
            }
        });
}
