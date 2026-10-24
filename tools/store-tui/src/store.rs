use crate::registry;
use anyhow::{Context, Result, bail, ensure};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use similar::TextDiff;
use std::{
    collections::BTreeMap,
    fs,
    io::Write,
    path::{Path, PathBuf},
    process::{Command, Stdio},
    time::{SystemTime, UNIX_EPOCH},
};

const FILES: [&str; 4] = [
    "config.json",
    "docker-compose.yml",
    "metadata/description.md",
    "metadata/logo.jpg",
];
pub const CATEGORIES: &str = "network,media,development,automation,social,utilities,photography,security,featured,books,data,music,finance,gaming,ai";
#[derive(Clone, Debug)]
pub struct Store {
    pub root: PathBuf,
}
#[derive(Clone, Debug)]
pub struct App {
    pub id: String,
    pub config: Value,
    pub compose: String,
    pub images: Vec<ServiceImage>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ServiceImage {
    pub name: String,
    pub image: String,
    pub main: bool,
}
#[derive(Clone, Debug)]
pub struct Change {
    pub path: PathBuf,
    pub before: Option<Vec<u8>>,
    pub after: Vec<u8>,
}
#[derive(Clone, Debug)]
pub struct Draft {
    pub id: String,
    pub changes: Vec<Change>,
    pub readme: Vec<u8>,
    pub summary: String,
}
#[derive(Clone, Debug)]
pub struct Applied {
    pub changes: Vec<Change>,
    pub summary: String,
}
fn now() -> Result<u64> {
    Ok(SystemTime::now().duration_since(UNIX_EPOCH)?.as_millis() as u64 - 1)
}
pub fn valid_id(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= 80
        && id.split('-').all(|p| {
            !p.is_empty()
                && p.bytes()
                    .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit())
        })
}
fn output(command: &mut Command) -> Result<String> {
    let result = command
        .output()
        .context("Could not launch required command")?;
    let text = format!(
        "{}{}",
        String::from_utf8_lossy(&result.stdout),
        String::from_utf8_lossy(&result.stderr)
    );
    ensure!(result.status.success(), "Command failed:\n{text}");
    Ok(text)
}
impl Store {
    pub fn discover(start: &Path) -> Result<Self> {
        let mut root = start.canonicalize()?;
        while !root.join("apps/app-info-schema.json").is_file()
            || !root.join("scripts/compose.ts").is_file()
        {
            ensure!(
                root.pop(),
                "No Runtipi app-store checkout found; pass its directory with --root"
            );
        }
        ensure!(root.join(".git").exists(), "Store must be a Git checkout");
        Ok(Self { root })
    }
    pub fn git(&self, args: &[&str]) -> Result<String> {
        output(Command::new("git").current_dir(&self.root).args(args))
    }
    fn clean(&self) -> Result<()> {
        ensure!(
            self.git(&["status", "--porcelain"])?.is_empty(),
            "Commit or stash existing changes before planning edits. The TUI never includes pre-existing changes in its commits."
        );
        Ok(())
    }
    fn app_dir(&self, id: &str) -> Result<PathBuf> {
        ensure!(valid_id(id), "Use a kebab-case app id");
        let apps = self.root.join("apps");
        ensure!(
            !fs::symlink_metadata(&apps)?.file_type().is_symlink(),
            "apps must not be a symlink"
        );
        let dir = apps.join(id);
        if dir.exists() {
            self.no_symlinks(&dir)?;
        }
        Ok(dir)
    }
    fn no_symlinks(&self, path: &Path) -> Result<()> {
        let relative = path.strip_prefix(&self.root)?;
        let mut current = self.root.clone();
        for part in relative.components() {
            current.push(part);
            if let Ok(meta) = fs::symlink_metadata(&current) {
                ensure!(
                    !meta.file_type().is_symlink(),
                    "Refusing symlink: {}",
                    current.display()
                );
            }
        }
        Ok(())
    }
    pub fn list(&self) -> Result<Vec<App>> {
        let mut apps = Vec::new();
        for entry in fs::read_dir(self.root.join("apps"))? {
            let entry = entry?;
            if !entry.file_type()?.is_dir() {
                continue;
            }
            let id = entry.file_name().to_string_lossy().to_string();
            let config_path = entry.path().join("config.json");
            if !config_path.is_file() {
                continue;
            }
            let config = serde_json::from_slice(&fs::read(config_path)?)
                .with_context(|| format!("Invalid config for {id}"))?;
            // Parse the selected app on demand so a broken Compose does not hide the list.
            apps.push(App {
                id,
                config,
                compose: String::new(),
                images: vec![],
            });
        }
        apps.sort_by(|a, b| a.id.cmp(&b.id));
        Ok(apps)
    }
    pub fn load(&self, id: &str) -> Result<App> {
        let dir = self.app_dir(id)?;
        let names = ["docker-compose.json", "docker-compose.yml"]
            .into_iter()
            .filter(|f| dir.join(f).exists())
            .collect::<Vec<_>>();
        ensure!(
            names.len() == 1,
            "Expected exactly one Compose source for {id}"
        );
        let compose = names[0].to_string();
        self.no_symlinks(&dir.join(&compose))?;
        let text = fs::read_to_string(dir.join(&compose))?;
        let images = serde_json::from_value(
            self.bridge(json!({"action":"images","filename":compose,"text":text}))?,
        )?;
        Ok(App {
            id: id.into(),
            config: serde_json::from_slice(&fs::read(dir.join("config.json"))?)?,
            compose,
            images,
        })
    }
    pub fn bridge(&self, input: Value) -> Result<Value> {
        let mut child = Command::new("bun")
            .args(["--eval", include_str!("../bridge.ts")])
            .current_dir(&self.root)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .context("Bun is required; run bun install in the store first")?;
        child
            .stdin
            .take()
            .context("No stdin")?
            .write_all(&serde_json::to_vec(&input)?)?;
        let out = child.wait_with_output()?;
        ensure!(
            out.status.success(),
            "{}",
            String::from_utf8_lossy(&out.stderr)
        );
        Ok(serde_json::from_slice(&out.stdout)?)
    }
    fn change(&self, id: &str, name: &str, after: Vec<u8>) -> Result<Change> {
        let path = PathBuf::from("apps").join(id).join(name);
        self.no_symlinks(&self.root.join(&path))?;
        let before = match fs::read(self.root.join(&path)) {
            Ok(b) => Some(b),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => None,
            Err(e) => return Err(e.into()),
        };
        Ok(Change {
            path,
            before,
            after,
        })
    }
    fn draft(&self, id: &str, changes: Vec<Change>, summary: String) -> Result<Draft> {
        let changes = changes
            .into_iter()
            .filter(|c| c.before.as_ref() != Some(&c.after))
            .collect::<Vec<_>>();
        ensure!(!changes.is_empty(), "Nothing changed");
        let draft = Draft {
            id: id.into(),
            changes,
            readme: fs::read(self.root.join("README.md"))?,
            summary,
        };
        self.validate_draft(&draft)?;
        Ok(draft)
    }
    fn bump(config: &mut Value) -> Result<()> {
        config["tipi_version"] = json!(
            config["tipi_version"]
                .as_u64()
                .context("Invalid tipi_version")?
                .checked_add(1)
                .context("tipi_version overflow")?
        );
        config["updated_at"] = json!(now()?);
        Ok(())
    }
    pub fn update(&self, id: &str, old: &str, tag: &str) -> Result<Draft> {
        self.clean()?;
        ensure!(
            !["coder-dev", "mlflow", "omnigent"].contains(&id),
            "This app has a maintained template/packager. Use its scripts instead of editing generated Compose."
        );
        let app = self.load(id)?;
        ensure!(
            app.images.iter().any(|i| i.image == old),
            "Selected image disappeared"
        );
        let image = registry::ImageRef::parse(old)?.with_tag(tag)?;
        ensure!(old != image, "Tag is already installed");
        let mut verified = BTreeMap::new();
        for service in &app.images {
            let reference = if service.image == old {
                &image
            } else {
                &service.image
            };
            if !verified.contains_key(reference) {
                verified.insert(reference.clone(), registry::verify(reference)?);
            }
        }
        let arches = ["amd64", "arm64"]
            .into_iter()
            .filter(|a| verified.values().all(|v| v.iter().any(|b| b == a)))
            .map(String::from)
            .collect::<Vec<_>>();
        ensure!(
            !arches.is_empty(),
            "Service images have no shared supported architecture"
        );
        self.update_verified(app, old, tag, &image, &arches)
    }
    fn update_verified(
        &self,
        app: App,
        old: &str,
        tag: &str,
        image: &str,
        arches: &[String],
    ) -> Result<Draft> {
        let id = app.id.as_str();
        let text = fs::read_to_string(self.app_dir(id)?.join(&app.compose))?;
        let patched=self.bridge(json!({"action":"replace","filename":app.compose,"text":text,"old":old,"image":image}))?.as_str().context("Invalid Compose output")?.to_string();
        let mut config = app.config.clone();
        if app.images.iter().any(|i| i.main && i.image == old) {
            config["version"] = json!(tag);
        }
        config["supported_architectures"] = json!(arches);
        Self::bump(&mut config)?;
        self.draft(
            id,
            vec![
                self.change(id, "config.json", pretty(&config)?)?,
                self.change(id, &app.compose, patched.into_bytes())?,
            ],
            format!("chore({id}): update image to {tag}"),
        )
    }
    pub fn metadata(&self, id: &str, values: &[String]) -> Result<Draft> {
        self.clean()?;
        let mut config = self.load(id)?.config;
        let old_port = config["port"].as_u64();
        ensure!(values.len() == 8, "Invalid metadata fields");
        for (key, value) in [
            "name",
            "short_desc",
            "description",
            "author",
            "source",
            "port",
            "categories",
            "website",
        ]
        .into_iter()
        .zip(values)
        {
            config[key] = match key {
                "port" => json!(value.parse::<u16>().context("Host port must be 1–65535")?),
                "categories" => categories(value)?,
                _ => json!(value),
            };
        }
        if config["port"].as_u64() != old_port {
            self.port_free(config["port"].as_u64().unwrap_or(0), Some(id))?;
        }
        Self::bump(&mut config)?;
        self.draft(
            id,
            vec![self.change(id, "config.json", pretty(&config)?)?],
            format!("chore({id}): update metadata"),
        )
    }
    fn port_free(&self, port: u64, except: Option<&str>) -> Result<()> {
        ensure!(port > 0 && port <= 65535, "Host port must be 1–65535");
        for app in self.list()? {
            if Some(app.id.as_str()) != except && app.config["port"].as_u64() == Some(port) {
                bail!("Port {port} is already assigned to {}", app.id);
            }
        }
        Ok(())
    }
    pub fn new_app(&self, v: &[String]) -> Result<Draft> {
        self.clean()?;
        ensure!(v.len() == 13, "Invalid new-app fields");
        let id = &v[0];
        let dir = self.app_dir(id)?;
        ensure!(!dir.exists(), "App directory already exists");
        let host = v[7].parse::<u16>().context("Invalid host port")?;
        self.port_free(u64::from(host), None)?;
        let internal = v[8].parse::<u16>().context("Invalid internal port")?;
        ensure!(internal > 0, "Internal port must be positive");
        let image = registry::ImageRef::parse(&v[6])?;
        image.with_tag(&image.tag)?;
        let arches = registry::verify(&v[6])?;
        let icon = registry::icon(&v[12])?;
        self.new_verified(v, arches, icon)
    }
    fn new_verified(&self, v: &[String], arches: Vec<String>, icon: Vec<u8>) -> Result<Draft> {
        let id = &v[0];
        let image = registry::ImageRef::parse(&v[6])?;
        let host = v[7].parse::<u16>()?;
        let internal = v[8].parse::<u16>()?;
        let config = json!({"id":id,"name":v[1],"short_desc":v[2],"description":v[3],"author":v[4],"source":v[5],"website":v[5],"port":host,"categories":categories(&v[9])?,"available":true,"exposable":true,"dynamic_config":true,"min_tipi_version":"4.10.1","version":image.tag,"tipi_version":1,"supported_architectures":arches,"created_at":now()?,"updated_at":now()?,"form_fields":[]});
        let mut service =
            json!({"image":v[6],"x-runtipi":{"is_main":true,"internal_port":internal}});
        if !v[10].is_empty() || !v[11].is_empty() {
            ensure!(
                !v[10].is_empty()
                    && v[11].starts_with('/')
                    && !v[11].contains(':')
                    && valid_id(&v[10]),
                "Provide both a kebab-case data folder and absolute container data path (without colon)"
            );
            service["volumes"] = json!([format!("${{APP_DATA_DIR}}/{}:{}", v[10], v[11])]);
        }
        let compose = json!({"x-runtipi":{"schema_version":2},"services":{id:service}});
        // JSON is a valid YAML subset; stringify scalars safely, then let the shared YAML library format it.
        let yaml = self
            .bridge(json!({"action":"format","value":compose}))?
            .as_str()
            .context("Cannot format Compose")?
            .to_string();
        let contents = [
            pretty(&config)?,
            yaml.into_bytes(),
            format!("# {}\n\n{}\n\nSource: {}\n", v[1], v[3], v[5]).into_bytes(),
            icon,
        ];
        let changes = FILES
            .into_iter()
            .zip(contents)
            .map(|(name, data)| self.change(id, name, data))
            .collect::<Result<_>>()?;
        self.draft(id, changes, format!("feat({id}): add Runtipi app"))
    }
    pub fn replace_icon(&self, id: &str, source: &str) -> Result<Draft> {
        self.clean()?;
        let data = registry::icon(source)?;
        let mut config = self.load(id)?.config;
        Self::bump(&mut config)?;
        self.draft(
            id,
            vec![
                self.change(id, "metadata/logo.jpg", data)?,
                self.change(id, "config.json", pretty(&config)?)?,
            ],
            format!("chore({id}): update icon"),
        )
    }
    pub fn validate_draft(&self, draft: &Draft) -> Result<()> {
        let temp = tempfile::tempdir()?;
        let dir = temp.path().join(&draft.id);
        fs::create_dir_all(dir.join("metadata"))?;
        for name in [
            "config.json",
            "docker-compose.yml",
            "docker-compose.json",
            "metadata/description.md",
            "metadata/logo.jpg",
        ] {
            let p = self.app_dir(&draft.id)?.join(name);
            self.no_symlinks(&p)?;
            if p.is_file() {
                fs::copy(p, dir.join(name))?;
            }
        }
        for c in &draft.changes {
            let relative = c.path.strip_prefix(PathBuf::from("apps").join(&draft.id))?;
            fs::write(dir.join(relative), &c.after)?;
        }
        self.bridge(json!({"action":"validate","directory":dir,"id":draft.id}))?;
        let logo = fs::read(dir.join("metadata/logo.jpg"))?;
        ensure!(
            image::guess_format(&logo)? == image::ImageFormat::Jpeg,
            "Logo must really be a JPEG"
        );
        Ok(())
    }
    pub fn validate(&self) -> Result<String> {
        output(
            Command::new("bun")
                .args(["run", "test"])
                .current_dir(&self.root),
        )
    }
    pub fn apply(&self, draft: Draft) -> Result<Applied> {
        self.clean()?;
        self.validate_draft(&draft)?;
        ensure!(
            fs::read(self.root.join("README.md"))? == draft.readme,
            "README changed since preview"
        );
        for c in &draft.changes {
            self.check_before(c)?;
        }
        let result = (|| -> Result<Vec<Change>> {
            for c in &draft.changes {
                let path = self.root.join(&c.path);
                fs::create_dir_all(path.parent().context("No parent")?)?;
                atomic_write(&path, &c.after)?;
            }
            output(
                Command::new("bun")
                    .arg(".github/scripts/readme-generator.ts")
                    .current_dir(&self.root),
            )?;
            let mut changes = draft.changes.clone();
            let after = fs::read(self.root.join("README.md"))?;
            if after != draft.readme {
                changes.push(Change {
                    path: "README.md".into(),
                    before: Some(draft.readme.clone()),
                    after,
                });
            }
            Ok(changes)
        })();
        match result {
            Ok(changes) => Ok(Applied {
                changes,
                summary: draft.summary,
            }),
            Err(error) => {
                for c in draft.changes.iter().rev() {
                    let path = self.root.join(&c.path);
                    match &c.before {
                        Some(data) => {
                            atomic_write(&path, data)?;
                        }
                        None => {
                            if path.exists() {
                                fs::remove_file(&path)?;
                            }
                        }
                    }
                }
                atomic_write(&self.root.join("README.md"), &draft.readme)?;
                // Remove only empty directories created for a new app.
                let dir = self.app_dir(&draft.id)?;
                let _ = fs::remove_dir(dir.join("metadata"));
                let _ = fs::remove_dir(dir);
                Err(error.context("Apply failed; restored original files"))
            }
        }
    }
    fn check_before(&self, c: &Change) -> Result<()> {
        let p = self.root.join(&c.path);
        self.no_symlinks(&p)?;
        let current = fs::read(p).ok();
        ensure!(
            current == c.before,
            "{} changed since preview",
            c.path.display()
        );
        Ok(())
    }
    pub fn commit(&self, applied: &Applied) -> Result<String> {
        ensure!(
            self.git(&["diff", "--cached", "--name-only"])?.is_empty(),
            "Index already contains staged changes; commit them separately"
        );
        for c in &applied.changes {
            self.no_symlinks(&self.root.join(&c.path))?;
            ensure!(
                fs::read(self.root.join(&c.path))? == c.after,
                "{} changed after apply",
                c.path.display()
            );
        }
        // Revalidate the current entire store immediately before committing.
        self.validate()?;
        // Validators may run generators. Never stage bytes that were not reviewed.
        for c in &applied.changes {
            ensure!(
                fs::read(self.root.join(&c.path))? == c.after,
                "{} changed during validation",
                c.path.display()
            );
        }
        let paths = applied
            .changes
            .iter()
            .map(|c| c.path.to_string_lossy().to_string())
            .collect::<Vec<_>>();
        let mut args = vec!["add", "--"];
        args.extend(paths.iter().map(String::as_str));
        self.git(&args)?;
        // --only avoids including unrelated files a concurrent process may have staged.
        let mut args = vec!["commit", "--only", "-m", applied.summary.as_str(), "--"];
        args.extend(paths.iter().map(String::as_str));
        let result = self.git(&args);
        if result.is_err() {
            let mut reset = vec!["reset", "--quiet", "HEAD", "--"];
            reset.extend(paths.iter().map(String::as_str));
            self.git(&reset)
                .context("Commit failed and staging cleanup also failed; inspect git status")?;
        }
        result
    }
}
fn atomic_write(path: &Path, data: &[u8]) -> Result<()> {
    let mut file = tempfile::NamedTempFile::new_in(path.parent().context("No parent")?)?;
    if let Ok(meta) = fs::metadata(path) {
        file.as_file().set_permissions(meta.permissions())?;
    }
    file.write_all(data)?;
    file.as_file().sync_all()?;
    file.persist(path)?;
    Ok(())
}
fn categories(value: &str) -> Result<Value> {
    let values = value
        .split(',')
        .map(str::trim)
        .filter(|v| !v.is_empty())
        .collect::<Vec<_>>();
    ensure!(
        !values.is_empty()
            && values
                .iter()
                .all(|v| CATEGORIES.split(',').any(|c| c == *v)),
        "Choose categories from: {CATEGORIES}"
    );
    Ok(json!(values))
}
fn pretty(value: &Value) -> Result<Vec<u8>> {
    Ok(format!("{}\n", serde_json::to_string_pretty(value)?).into_bytes())
}
impl Draft {
    pub fn preview(&self) -> String {
        let mut out = format!(
            "{}\n\nSchema validation passed. Apply writes files and regenerates README.\nCommit is separate and requires the full test suite to pass.\n\n",
            self.summary
        );
        for c in &self.changes {
            if c.path.extension().is_some_and(|x| x == "jpg") {
                out += &format!(
                    "{}: JPEG {} -> {} bytes (460x460 for imported icons)\n",
                    c.path.display(),
                    c.before.as_ref().map_or(0, Vec::len),
                    c.after.len()
                );
                continue;
            }
            let old = c.before.as_deref().unwrap_or_default();
            out += &TextDiff::from_lines(
                &String::from_utf8_lossy(old),
                &String::from_utf8_lossy(&c.after),
            )
            .unified_diff()
            .header(
                &format!("a/{}", c.path.display()),
                &format!("b/{}", c.path.display()),
            )
            .to_string();
        }
        out
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn reject_traversal_and_invalid_categories() {
        for s in ["../evil", "/tmp/x", "a--b", "A", "", "a/b"] {
            assert!(!valid_id(s));
        }
        assert!(valid_id("billharbor-dev"));
        assert!(categories("finance, automation").is_ok());
        assert!(categories("productivity").is_err());
    }
    #[test]
    fn optimistic_guard_refuses_changed_file() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path().to_path_buf();
        fs::write(root.join("x"), b"new").unwrap();
        let store = Store { root };
        let c = Change {
            path: "x".into(),
            before: Some(b"old".to_vec()),
            after: b"candidate".to_vec(),
        };
        assert!(store.check_before(&c).is_err());
    }
    #[test]
    fn atomic_write_preserves_bytes() {
        let temp = tempfile::tempdir().unwrap();
        let p = temp.path().join("x");
        atomic_write(&p, b"hello").unwrap();
        atomic_write(&p, b"world").unwrap();
        assert_eq!(fs::read(p).unwrap(), b"world");
    }
}

#[cfg(test)]
mod workflow_tests {
    use super::*;
    fn fixture(legacy: bool) -> (tempfile::TempDir, Store) {
        let temp = tempfile::tempdir().unwrap();
        let store = Store {
            root: temp.path().to_path_buf(),
        };
        let source = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
        fs::create_dir_all(store.root.join("apps/demo/metadata")).unwrap();
        fs::create_dir_all(store.root.join("scripts")).unwrap();
        fs::copy(
            source.join("scripts/compose.ts"),
            store.root.join("scripts/compose.ts"),
        )
        .unwrap();
        for name in [
            "app-info-schema.json",
            "compose-yaml-schema.json",
            "dynamic-compose-schema.json",
        ] {
            fs::copy(
                source.join("apps").join(name),
                store.root.join("apps").join(name),
            )
            .unwrap();
        }
        #[cfg(unix)]
        std::os::unix::fs::symlink(
            source.join("node_modules").canonicalize().unwrap(),
            store.root.join("node_modules"),
        )
        .unwrap();
        #[cfg(windows)]
        std::os::windows::fs::symlink_dir(
            source.join("node_modules").canonicalize().unwrap(),
            store.root.join("node_modules"),
        )
        .unwrap();
        fs::write(store.root.join(".gitignore"), "node_modules/\n").unwrap();
        fs::create_dir_all(store.root.join(".github/scripts")).unwrap();
        fs::copy(
            source.join(".github/scripts/readme-generator.ts"),
            store.root.join(".github/scripts/readme-generator.ts"),
        )
        .unwrap();
        fs::write(store.root.join("README.md"),"# Fixture\n<!-- APPS:START - generated by .github/scripts/readme-generator.ts, do not edit by hand -->\n<!-- APPS:END -->\n").unwrap();
        let mut config: Value =
            serde_json::from_slice(&fs::read(source.join("apps/billharbor/config.json")).unwrap())
                .unwrap();
        config["id"] = json!("demo");
        config["version"] = json!("1.2.3");
        config["tipi_version"] = json!(1);
        fs::write(
            store.root.join("apps/demo/config.json"),
            pretty(&config).unwrap(),
        )
        .unwrap();
        fs::copy(
            source.join("apps/billharbor/metadata/logo.jpg"),
            store.root.join("apps/demo/metadata/logo.jpg"),
        )
        .unwrap();
        fs::write(
            store.root.join("apps/demo/metadata/description.md"),
            "# Demo\n\nFixture.",
        )
        .unwrap();
        if legacy {
            fs::write(store.root.join("apps/demo/docker-compose.json"),pretty(&json!({"schemaVersion":2,"$schema":"https://schemas.runtipi.io/v2/dynamic-compose.json","services":[{"name":"main","image":"owner/demo:1.2.3","isMain":true,"internalPort":8080,"environment":[{"key":"DATA","value":"${APP_DATA_DIR}"}]},{"name":"init","image":"owner/demo:1.2.3"}]})).unwrap()).unwrap();
        } else {
            fs::write(store.root.join("apps/demo/docker-compose.yml"),"# retain this deployment note\nx-runtipi:\n  schema_version: 2\nservices:\n  main:\n    image: owner/demo:1.2.3 # main pin\n    environment:\n      DATA: ${APP_DATA_DIR}\n    x-runtipi:\n      is_main: true\n      internal_port: 8080\n  init:\n    image: owner/demo:1.2.3\n").unwrap();
        }
        fs::write(
            store.root.join("package.json"),
            r#"{"scripts":{"test":"bun -e 'process.exit(0)'"}}"#,
        )
        .unwrap();
        store.git(&["init", "-q"]).unwrap();
        store.git(&["config", "user.name", "TUI Test"]).unwrap();
        store
            .git(&["config", "user.email", "tui@example.invalid"])
            .unwrap();
        store.git(&["config", "commit.gpgsign", "false"]).unwrap();
        store
            .git(&["config", "core.hooksPath", "/dev/null"])
            .unwrap();
        store.git(&["add", "."]).unwrap();
        store.git(&["commit", "-qm", "fixture"]).unwrap();
        (temp, store)
    }
    #[test]
    fn linked_update_preserves_yaml_and_commits_only_reviewed_paths() {
        let (_temp, store) = fixture(false);
        let app = store.load("demo").unwrap();
        let draft = store
            .update_verified(
                app,
                "owner/demo:1.2.3",
                "1.2.4",
                "owner/demo:1.2.4",
                &["amd64".into(), "arm64".into()],
            )
            .unwrap();
        let text = String::from_utf8(
            draft
                .changes
                .iter()
                .find(|c| c.path.extension().is_some_and(|e| e == "yml"))
                .unwrap()
                .after
                .clone(),
        )
        .unwrap();
        assert!(text.contains("# retain this deployment note"));
        assert!(text.contains("# main pin"));
        assert!(text.contains("${APP_DATA_DIR}"));
        assert_eq!(text.matches("owner/demo:1.2.4").count(), 2);
        let applied = store.apply(draft).unwrap();
        let config = store.load("demo").unwrap().config;
        assert_eq!(config["version"], "1.2.4");
        assert_eq!(config["tipi_version"], 2);
        fs::write(store.root.join("unrelated.txt"), "leave this alone").unwrap();
        store.commit(&applied).unwrap();
        assert_eq!(
            store.git(&["status", "--porcelain"]).unwrap(),
            "?? unrelated.txt\n"
        );
    }
    #[test]
    fn legacy_update_preserves_environment_array() {
        let (_temp, store) = fixture(true);
        let draft = store
            .update_verified(
                store.load("demo").unwrap(),
                "owner/demo:1.2.3",
                "1.2.4",
                "owner/demo:1.2.4",
                &["amd64".into()],
            )
            .unwrap();
        store.apply(draft).unwrap();
        let c: Value = serde_json::from_slice(
            &fs::read(store.root.join("apps/demo/docker-compose.json")).unwrap(),
        )
        .unwrap();
        assert!(c["services"][0]["environment"].is_array());
        assert_eq!(c["services"][1]["image"], "owner/demo:1.2.4");
    }
    #[test]
    fn external_edit_and_invalid_draft_never_overwrite_files() {
        let (_temp, store) = fixture(false);
        let mut draft = store
            .update_verified(
                store.load("demo").unwrap(),
                "owner/demo:1.2.3",
                "1.2.4",
                "owner/demo:1.2.4",
                &["amd64".into()],
            )
            .unwrap();
        let path = store.root.join("apps/demo/config.json");
        let original = fs::read(&path).unwrap();
        draft
            .changes
            .iter_mut()
            .find(|c| c.path.ends_with("config.json"))
            .unwrap()
            .after = b"{}".to_vec();
        assert!(store.apply(draft).is_err());
        assert_eq!(fs::read(&path).unwrap(), original);
        let draft = store
            .update_verified(
                store.load("demo").unwrap(),
                "owner/demo:1.2.3",
                "1.2.4",
                "owner/demo:1.2.4",
                &["amd64".into()],
            )
            .unwrap();
        fs::write(&path, "external edit").unwrap();
        assert!(store.apply(draft).is_err());
        assert_eq!(fs::read(path).unwrap(), b"external edit");
    }
    #[test]
    fn failed_generator_rolls_back_files() {
        let (_temp, store) = fixture(false);
        fs::write(
            store.root.join(".github/scripts/readme-generator.ts"),
            "process.exit(1)",
        )
        .unwrap();
        store.git(&["add", "."]).unwrap();
        store
            .git(&["commit", "-qm", "broken generator fixture"])
            .unwrap();
        let before = fs::read(store.root.join("apps/demo/config.json")).unwrap();
        let draft = store
            .update_verified(
                store.load("demo").unwrap(),
                "owner/demo:1.2.3",
                "1.2.4",
                "owner/demo:1.2.4",
                &["amd64".into()],
            )
            .unwrap();
        assert!(store.apply(draft).is_err());
        assert_eq!(
            fs::read(store.root.join("apps/demo/config.json")).unwrap(),
            before
        );
        assert!(store.git(&["status", "--porcelain"]).unwrap().is_empty());
    }
    #[test]
    fn schema_valid_new_app_contains_one_main_service_and_no_duplicate_port() {
        let (_temp, store) = fixture(false);
        let values = [
            "new-demo",
            "New demo",
            "A guided app",
            "App description",
            "Upstream",
            "https://example.com/project",
            "owner/demo:1.2.3",
            "8106",
            "8080",
            "utilities",
            "data",
            "/data",
            "unused",
        ]
        .map(String::from);
        let icon = fs::read(store.root.join("apps/demo/metadata/logo.jpg")).unwrap();
        let draft = store
            .new_verified(&values, vec!["amd64".into()], icon)
            .unwrap();
        store.apply(draft).unwrap();
        let app = store.load("new-demo").unwrap();
        assert_eq!(app.images.len(), 1);
        assert_eq!(app.images[0].name, "new-demo");
        assert!(app.images[0].main);
        assert!(store.port_free(8106, None).is_err());
        let text = fs::read_to_string(store.root.join("apps/new-demo/docker-compose.yml")).unwrap();
        assert!(text.contains("${APP_DATA_DIR}/data:/data"));
        assert!(!text.contains("ports:"));
    }
    #[test]
    fn failed_tests_and_existing_index_block_commit() {
        let (_temp, store) = fixture(false);
        let draft = store
            .update_verified(
                store.load("demo").unwrap(),
                "owner/demo:1.2.3",
                "1.2.4",
                "owner/demo:1.2.4",
                &["amd64".into()],
            )
            .unwrap();
        let applied = store.apply(draft).unwrap();
        fs::write(
            store.root.join("package.json"),
            r#"{"scripts":{"test":"bun -e 'process.exit(1)'"}}"#,
        )
        .unwrap();
        assert!(store.commit(&applied).is_err());
        assert!(
            store
                .git(&["diff", "--cached", "--name-only"])
                .unwrap()
                .is_empty()
        );
        store.git(&["add", "package.json"]).unwrap();
        assert!(store.commit(&applied).is_err());
    }
    #[test]
    fn commit_hook_failure_unstages_only_this_sessions_paths() {
        let (_temp, store) = fixture(false);
        let draft = store
            .update_verified(
                store.load("demo").unwrap(),
                "owner/demo:1.2.3",
                "1.2.4",
                "owner/demo:1.2.4",
                &["amd64".into()],
            )
            .unwrap();
        let applied = store.apply(draft).unwrap();
        // An invalid signing executable simulates a Git commit failure after staging.
        store.git(&["config", "commit.gpgsign", "true"]).unwrap();
        store
            .git(&["config", "gpg.program", "/definitely/no/such/program"])
            .unwrap();
        assert!(store.commit(&applied).is_err());
        assert!(
            store
                .git(&["diff", "--cached", "--name-only"])
                .unwrap()
                .is_empty()
        );
        store.git(&["config", "commit.gpgsign", "false"]).unwrap();
        store.commit(&applied).unwrap();
    }
    #[cfg(unix)]
    #[test]
    fn symlink_metadata_is_refused() {
        use std::os::unix::fs::symlink;
        let (_temp, store) = fixture(false);
        let dir = store.root.join("apps/demo/metadata");
        fs::remove_file(dir.join("logo.jpg")).unwrap();
        symlink("/etc/hosts", dir.join("logo.jpg")).unwrap();
        assert!(
            store
                .change("demo", "metadata/logo.jpg", b"bytes".to_vec())
                .is_err()
        );
    }
}
