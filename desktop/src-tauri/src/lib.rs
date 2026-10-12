use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;
use tauri::{Manager, RunEvent, WindowEvent};
use tauri_plugin_dialog::{DialogExt, MessageDialogButtons, MessageDialogKind};
use tauri_plugin_shell::{process::CommandChild, ShellExt};

struct BackendProcess(Mutex<Option<CommandChild>>);
struct CloseState(AtomicBool);

fn terminate_backend_tree(child: CommandChild) {
    // PyInstaller one-file executables may launch a child process with the same
    // executable name. Killing only the sidecar parent can leave that child alive.
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        let pid = child.pid();
        match std::process::Command::new("taskkill")
            .args(["/PID", &pid.to_string(), "/T", "/F"])
            .creation_flags(CREATE_NO_WINDOW)
            .output()
        {
            Ok(result) if result.status.success() => return,
            Ok(result) => eprintln!(
                "Backend process-tree termination returned {}: {}",
                result.status,
                String::from_utf8_lossy(&result.stderr)
            ),
            Err(error) => eprintln!("Cannot run taskkill for backend PID {pid}: {error}"),
        }
    }
    // Fallback on platforms without taskkill, or when Windows tree termination fails.
    if let Err(error) = child.kill() {
        eprintln!("Could not terminate SentinelLab backend: {error}");
    }
}

fn stop_backend(app: &tauri::AppHandle) {
    let backend_state = app.state::<BackendProcess>();
    let child = backend_state.0.lock()
        .expect("backend mutex poisoned").take();
    if let Some(child) = child {
        terminate_backend_tree(child);
    }
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(BackendProcess(Mutex::new(None)))
        .manage(CloseState(AtomicBool::new(false)))
        .setup(|app| {
            // Do not block the Windows UI thread while starting the Python sidecar.
            let handle = app.handle().clone();
            std::thread::spawn(move || {
                let command = match handle.shell().sidecar("sentinellab-api") {
                    Ok(command) => command,
                    Err(error) => {
                        eprintln!("Cannot prepare SentinelLab backend: {error}");
                        return;
                    }
                };
                match command.spawn() {
                    Ok((_rx, child)) => {
                        let backend_state = handle.state::<BackendProcess>();
                        let mut process = backend_state.0.lock()
                            .expect("backend mutex poisoned");
                        if handle.state::<CloseState>().0.load(Ordering::SeqCst) {
                            terminate_backend_tree(child);
                        } else {
                            *process = Some(child);
                        }
                    }
                    Err(error) => eprintln!("Cannot launch SentinelLab backend: {error}"),
                }
            });
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
