use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;
use tauri::{Manager, RunEvent, WindowEvent};
use tauri_plugin_dialog::{DialogExt, MessageDialogButtons, MessageDialogKind};
use tauri_plugin_shell::{process::CommandChild, ShellExt};

struct BackendProcess(Mutex<Option<CommandChild>>);
struct CloseState(AtomicBool);

fn stop_backend(app: &tauri::AppHandle) {
    if let Some(child) = app.state::<BackendProcess>().0.lock()
        .expect("backend mutex poisoned").take()
    {
        if let Err(error) = child.kill() {
            eprintln!("Could not terminate SentinelLab backend: {error}");
        }
    }
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(BackendProcess(Mutex::new(None)))
        .manage(CloseState(AtomicBool::new(false)))
        .setup(|app| {
            let command = app.shell().sidecar("sentinellab-api")?;
            let (_rx, child) = command.spawn()?;
            *app.state::<BackendProcess>().0.lock().expect("backend mutex poisoned") = Some(child);
            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                let app = window.app_handle();
                if app.state::<CloseState>().0.load(Ordering::SeqCst) {
                    return;
                }
                api.prevent_close();
                let backend_running = app.state::<BackendProcess>().0.lock()
                    .expect("backend mutex poisoned").is_some();
                let detail = if backend_running {
                    "1 managed process is running:\n\n• sentinellab-api.exe — local SentinelLab API\n\nClosing SentinelLab will terminate this process. MongoDB is an independent Windows service and will remain running."
                } else {
                    "No managed SentinelLab backend process is currently running. MongoDB is an independent Windows service and will remain running."
                };
                let message = format!("Do you want to close SentinelLab?\n\n{detail}");
                let window = window.clone();
                app.dialog().message(message)
                    .title("Close SentinelLab?")
                    .kind(MessageDialogKind::Warning)
                    .buttons(MessageDialogButtons::OkCancel)
                    .show(move |confirmed| {
                        if confirmed {
                            let app = window.app_handle().clone();
                            app.state::<CloseState>().0.store(true, Ordering::SeqCst);
                            stop_backend(&app);
                            if let Err(error) = window.close() {
                                eprintln!("Could not close SentinelLab window: {error}");
                                app.state::<CloseState>().0.store(false, Ordering::SeqCst);
                            }
                        }
                    });
            }
        })
        .build(tauri::generate_context!())
        .expect("failed to build SentinelLab desktop")
        .run(|app, event| {
            if let RunEvent::Exit = event {
                stop_backend(app);
            }
        });
}
