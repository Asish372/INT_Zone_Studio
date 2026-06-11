use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;

use tauri::Manager;
use tauri::path::BaseDirectory;
use tauri_plugin_opener::OpenerExt;

struct SidecarState(Mutex<Option<Child>>);
struct EngineStartup(Mutex<Option<String>>);

fn project_root() -> PathBuf {
    if cfg!(debug_assertions) {
        let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        return manifest
            .parent()
            .unwrap()
            .parent()
            .unwrap()
            .parent()
            .unwrap()
            .to_path_buf();
    }

    if let Ok(exe) = std::env::current_exe() {
        let mut dir = exe.parent().map(|p| p.to_path_buf()).unwrap_or_default();
        for _ in 0..8 {
            if dir.join("scripts").join("run_polygon_workspace.py").exists() {
                return dir;
            }
            if !dir.pop() {
                break;
            }
        }
        if let Some(parent) = exe.parent() {
            return parent.to_path_buf();
        }
    }

    PathBuf::from(".")
}

fn install_dir() -> Option<PathBuf> {
    std::env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|d| d.to_path_buf()))
}

fn seed_app_data(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    let data_dir = app.path().app_data_dir().map_err(|e| e.to_string())?;
    std::fs::create_dir_all(&data_dir).map_err(|e| e.to_string())?;

    for name in [
        "config.yaml",
        "PILOT_FEEDBACK.md",
        "pilot_metrics_template.csv",
    ] {
        let dest = data_dir.join(name);
        if dest.exists() {
            continue;
        }

        let mut copied = false;
        if let Ok(src) = app.path().resolve(name, BaseDirectory::Resource) {
            if src.exists() {
                copied = std::fs::copy(&src, &dest).is_ok();
            }
        }
        if copied {
            continue;
        }
        if let Some(install) = install_dir() {
            let src = install.join(name);
            if src.exists() {
                let _ = std::fs::copy(&src, &dest);
            }
        }
    }

    Ok(data_dir)
}

fn bundled_engine_exe(app: &tauri::AppHandle) -> Option<PathBuf> {
    let resource_candidates = [
        "engine/int-zone-engine/int-zone-engine.exe",
        "int-zone-engine/int-zone-engine.exe",
    ];
    for rel in resource_candidates {
        if let Ok(path) = app.path().resolve(rel, BaseDirectory::Resource) {
            if path.exists() {
                return Some(path);
            }
        }
    }

    let install_candidates = install_dir().into_iter().flat_map(|exe_dir| {
        [
            exe_dir
                .join("engine")
                .join("int-zone-engine")
                .join("int-zone-engine.exe"),
            exe_dir
                .join("resources")
                .join("engine")
                .join("int-zone-engine")
                .join("int-zone-engine.exe"),
            exe_dir
                .join("int-zone-engine")
                .join("int-zone-engine.exe"),
        ]
    });

    for path in install_candidates {
        if path.exists() {
            return Some(path);
        }
    }

    None
}

fn wait_for_engine(child: &mut Child) -> Result<(), String> {
    use std::net::{SocketAddr, TcpStream};

    let addr: SocketAddr = "127.0.0.1:8765".parse().expect("engine port");
    for _ in 0..60 {
        if let Ok(Some(status)) = child.try_wait() {
            return Err(format!(
                "Detection engine stopped unexpectedly ({status}). Close all INT Zone Studio windows, reopen from Start Menu, and try again."
            ));
        }
        if TcpStream::connect_timeout(&addr, Duration::from_millis(300)).is_ok() {
            return Ok(());
        }
        std::thread::sleep(Duration::from_millis(500));
    }
    Err(
        "Detection engine did not start in time. Close INT Zone Studio completely, reopen from Start Menu, and wait a few seconds."
            .into(),
    )
}

fn spawn_python_sidecar() -> Option<Child> {
    let root = project_root();
    let script = root.join("scripts").join("run_polygon_workspace.py");
    let python = if cfg!(windows) { "python" } else { "python3" };

    Command::new(python)
        .arg(script)
        .current_dir(&root)
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .ok()
}

fn bundled_oda_exe(app: &tauri::AppHandle) -> Option<PathBuf> {
    if let Ok(path) = app
        .path()
        .resolve("oda/ODAFileConverter.exe", BaseDirectory::Resource)
    {
        if path.exists() {
            return Some(path);
        }
    }

    let candidates = install_dir().into_iter().flat_map(|exe_dir| {
        [
            exe_dir.join("oda").join("ODAFileConverter.exe"),
            exe_dir
                .join("resources")
                .join("oda")
                .join("ODAFileConverter.exe"),
            exe_dir
                .join("engine")
                .join("oda")
                .join("ODAFileConverter.exe"),
        ]
    });

    for path in candidates {
        if path.exists() {
            return Some(path);
        }
    }

    None
}

fn apply_oda_env(cmd: &mut Command, oda: &PathBuf) {
    cmd.env("INT_ZONE_ODA_PATH", oda);
    if let Some(oda_dir) = oda.parent() {
        let path = std::env::var("PATH").unwrap_or_default();
        cmd.env(
            "PATH",
            format!("{};{}", oda_dir.to_string_lossy(), path),
        );
    }
}

fn spawn_bundled_sidecar(app: &tauri::AppHandle) -> Result<Child, String> {
    let engine_exe = bundled_engine_exe(app).ok_or_else(|| {
        "Detection engine files are missing from this installation. Reinstall INT Zone Studio."
            .to_string()
    })?;
    let engine_dir = engine_exe
        .parent()
        .ok_or_else(|| "Invalid engine install path.".to_string())?
        .to_path_buf();
    let data_dir = seed_app_data(app).map_err(|e| format!("Could not prepare app data: {e}"))?;

    let mut cmd = Command::new(&engine_exe);
    cmd.current_dir(&engine_dir)
        .env("INT_ZONE_DATA_DIR", &data_dir)
        .stdout(Stdio::null())
        .stderr(Stdio::null());

    if let Some(oda) = bundled_oda_exe(app) {
        apply_oda_env(&mut cmd, &oda);
    }

    let mut child = cmd
        .spawn()
        .map_err(|e| format!("Could not start detection engine: {e}"))?;

    wait_for_engine(&mut child)?;
    Ok(child)
}

#[tauri::command]
fn engine_startup_error(state: tauri::State<EngineStartup>) -> Option<String> {
    state.0.lock().ok().and_then(|guard| guard.clone())
}

#[tauri::command]
fn open_pilot_feedback_template(app: tauri::AppHandle) -> Result<String, String> {
    let path = if cfg!(debug_assertions) {
        project_root().join("PILOT_FEEDBACK.md")
    } else {
        let data_dir = app.path().app_data_dir().map_err(|e| e.to_string())?;
        data_dir.join("PILOT_FEEDBACK.md")
    };
    if !path.exists() {
        return Err(format!(
            "PILOT_FEEDBACK.md not found at {}",
            path.display()
        ));
    }
    let path_str = path.to_string_lossy().into_owned();
    app.opener()
        .open_path(&path_str, None::<&str>)
        .map_err(|e| e.to_string())?;
    Ok(path_str)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            open_pilot_feedback_template,
            engine_startup_error
        ])
        .setup(|app| {
            let mut startup_error = None;
            let child = if cfg!(debug_assertions) {
                spawn_python_sidecar()
            } else {
                match spawn_bundled_sidecar(app.handle()) {
                    Ok(child) => Some(child),
                    Err(err) => {
                        startup_error = Some(err);
                        None
                    }
                }
            };
            app.manage(EngineStartup(Mutex::new(startup_error)));
            app.manage(SidecarState(Mutex::new(child)));
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                if let Some(state) = window.app_handle().try_state::<SidecarState>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(mut child) = guard.take() {
                            let _ = child.kill();
                        }
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
