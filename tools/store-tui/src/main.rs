mod registry;
mod store;
mod ui;
use anyhow::{Result, bail, ensure};
use std::{io::IsTerminal, path::PathBuf};
fn main() -> Result<()> {
    let mut root = std::env::current_dir()?;
    let mut list = false;
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--root" => {
                root = PathBuf::from(
                    args.next()
                        .ok_or_else(|| anyhow::anyhow!("--root needs a directory"))?,
                )
            }
            "--list" => list = true,
            "--help" | "-h" => {
                println!(
                    "Runtipi Store TUI\n\nUsage: runtipi-store-tui [--root STORE] [--list]\n\nRun inside your store checkout. Requires Git and Bun (bun install first).\nKeys: n create, e metadata, u update main image, i select service, o icon, v validate, d diff, c commit applied changes, q quit.\nChanges are previewed before apply; commits run the complete test suite."
                );
                return Ok(());
            }
            _ => bail!("Unknown option {arg}; use --help"),
        }
    }
    let store = store::Store::discover(&root)?;
    if list {
        for app in store.list()? {
            println!(
                "{}\t{}\t{}",
                app.id,
                app.config["version"].as_str().unwrap_or("?"),
                app.config["name"].as_str().unwrap_or("?")
            );
        }
        return Ok(());
    }
    ensure!(
        std::io::stdin().is_terminal() && std::io::stdout().is_terminal(),
        "Interactive mode needs a terminal; use --list for plain output"
    );
    ui::run(store)
}
