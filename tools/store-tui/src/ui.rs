use crate::{
    registry,
    store::{App, Applied, Draft, Store},
};
use anyhow::{Context, Result};
use crossterm::event::{self, Event, KeyCode, KeyEvent, KeyEventKind, KeyModifiers};
use ratatui::{
    Frame,
    layout::{Constraint, Direction, Layout},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, ListState, Paragraph, Wrap},
};
use std::{
    sync::mpsc::{self, Receiver},
    time::Duration,
};

#[derive(Clone)]
enum FormKind {
    New,
    Metadata(String),
    Icon(String),
    Tag { id: String, old: String },
}
#[derive(Clone)]
struct Form {
    kind: FormKind,
    fields: Vec<(String, String)>,
    selected: usize,
}
enum Screen {
    Browse,
    Services {
        app: App,
        selected: usize,
    },
    Tags {
        id: String,
        old: String,
        tags: Vec<String>,
        selected: usize,
    },
    Form(Form),
    Review(Draft),
    Output(String),
}
enum Outcome {
    Tags {
        id: String,
        old: String,
        tags: Vec<String>,
    },
    Draft(Draft),
    Applied(Applied),
    Output(String),
    Committed(String),
}
struct Ui {
    store: Store,
    apps: Vec<App>,
    selected: usize,
    filter: String,
    searching: bool,
    screen: Screen,
    status: String,
    scroll: u16,
    job: Option<Receiver<Result<Outcome>>>,
    applied: Option<Applied>,
}
struct TerminalGuard;
impl Drop for TerminalGuard {
    fn drop(&mut self) {
        ratatui::restore();
    }
}
pub fn run(store: Store) -> Result<()> {
    let apps = store.list()?;
    let mut ui = Ui {
        store,
        apps,
        selected: 0,
        filter: String::new(),
        searching: false,
        screen: Screen::Browse,
        status: "Ready · public Docker Hub and GHCR registries".into(),
        scroll: 0,
        job: None,
        applied: None,
    };
    let mut terminal = ratatui::init();
    let _guard = TerminalGuard;
    let mut redraw = true;
    loop {
        redraw |= ui.collect();
        if redraw {
            terminal.draw(|frame| ui.render(frame))?;
            redraw = false;
        }
        if event::poll(Duration::from_millis(100))? {
            match event::read()? {
                Event::Key(key) if key.kind != KeyEventKind::Release => {
                    if ui.job.is_some() {
                        continue;
                    }
                    match ui.key(key) {
                        Ok(true) => break,
                        Ok(false) => {}
                        Err(error) => ui.status = format!("Error: {error:#}"),
                    }
                    redraw = true;
                }
                Event::Resize(_, _) => redraw = true,
                _ => {}
            }
        }
    }
    Ok(())
}
impl Ui {
    fn launch(
        &mut self,
        label: &str,
        work: impl FnOnce(Store) -> Result<Outcome> + Send + 'static,
    ) {
        let (tx, rx) = mpsc::channel();
        let store = self.store.clone();
        self.status = label.into();
        self.job = Some(rx);
        std::thread::spawn(move || {
            let _ = tx.send(work(store));
        });
    }
    fn collect(&mut self) -> bool {
        let Some(receiver) = &self.job else {
            return false;
        };
        let result = match receiver.try_recv() {
            Ok(r) => r,
            Err(mpsc::TryRecvError::Empty) => return false,
            Err(_) => Err(anyhow::anyhow!("Background operation stopped")),
        };
        self.job = None;
        self.scroll = 0;
        match result {
            Err(e) => self.status = format!("Error: {e:#}"),
            Ok(outcome) => {
                self.status = "Ready".into();
                self.screen = match outcome {
                    Outcome::Tags { id, old, tags } => Screen::Tags {
                        id,
                        old,
                        tags,
                        selected: 0,
                    },
                    Outcome::Draft(draft) => Screen::Review(draft),
                    Outcome::Applied(applied) => {
                        self.applied = Some(applied);
                        self.reload();
                        Screen::Output("Changes applied and README regenerated.\n\nPress c to run all tests and commit ONLY these files.\nPress d to review the working diff.\nPress Esc to return to the app list.\nQuitting leaves the changes uncommitted.".into())
                    }
                    Outcome::Output(text) => Screen::Output(text),
                    Outcome::Committed(text) => {
                        self.applied = None;
                        self.reload();
                        Screen::Output(text)
                    }
                };
            }
        }
        true
    }
    fn visible(&self) -> Vec<&App> {
        self.apps
            .iter()
            .filter(|app| {
                self.filter.is_empty()
                    || app.id.to_lowercase().contains(&self.filter)
                    || app.config["name"]
                        .as_str()
                        .unwrap_or("")
                        .to_lowercase()
                        .contains(&self.filter)
            })
            .collect()
    }
    fn reload(&mut self) {
        if let Ok(apps) = self.store.list() {
            self.apps = apps;
            self.selected = self.selected.min(self.visible().len().saturating_sub(1));
        }
    }
    fn selected_id(&self) -> Result<String> {
        Ok(self
            .visible()
            .get(self.selected)
            .context("No app selected")?
            .id
            .clone())
    }
    fn fetch_tags(&mut self, id: String, old: String) {
        self.launch(
            "Fetching public image tags (up to 100 recent Docker Hub tags)…",
            move |_| {
                let tags = registry::tags(&old)?;
                Ok(Outcome::Tags { id, old, tags })
            },
        );
    }
    fn submit(&mut self, form: Form) {
        let values = form.fields.into_iter().map(|(_, v)| v).collect::<Vec<_>>();
        self.launch(
            "Preparing draft, verifying image/icon and validating schemas…",
            move |store| {
                Ok(Outcome::Draft(match form.kind {
                    FormKind::New => store.new_app(&values)?,
                    FormKind::Metadata(id) => store.metadata(&id, &values)?,
                    FormKind::Icon(id) => store.replace_icon(&id, &values[0])?,
                    FormKind::Tag { id, old } => store.update(&id, &old, &values[0])?,
                }))
            },
        );
    }
    fn key(&mut self, key: KeyEvent) -> Result<bool> {
        if key.modifiers.contains(KeyModifiers::CONTROL) && key.code == KeyCode::Char('c') {
            return Ok(true);
        }
        if self.searching {
            match key.code {
                KeyCode::Enter => self.searching = false,
                KeyCode::Esc => {
                    self.searching = false;
                    self.filter.clear();
                }
                KeyCode::Backspace => {
                    self.filter.pop();
                }
                KeyCode::Char(c) => self.filter.extend(c.to_lowercase()),
                _ => {}
            }
            self.selected = 0;
            return Ok(false);
        }
        if matches!(key.code, KeyCode::Esc) {
            self.screen = Screen::Browse;
            self.scroll = 0;
            return Ok(false);
        }
        match &mut self.screen {
            Screen::Form(form) => {
                match key.code {
                    KeyCode::Tab | KeyCode::Down => {
                        form.selected = (form.selected + 1) % form.fields.len()
                    }
                    KeyCode::BackTab | KeyCode::Up => {
                        form.selected = (form.selected + form.fields.len() - 1) % form.fields.len()
                    }
                    KeyCode::Backspace => {
                        form.fields[form.selected].1.pop();
                    }
                    KeyCode::Char('u') if key.modifiers.contains(KeyModifiers::CONTROL) => {
                        form.fields[form.selected].1.clear()
                    }
                    KeyCode::Char(c) if !key.modifiers.contains(KeyModifiers::CONTROL) => {
                        form.fields[form.selected].1.push(c)
                    }
                    KeyCode::Enter => {
                        let form = form.clone();
                        self.submit(form);
                    }
                    _ => {}
                }
                return Ok(false);
            }
            Screen::Services { app, selected } => {
                match key.code {
                    KeyCode::Down | KeyCode::Char('j') => {
                        *selected = (*selected + 1).min(app.images.len().saturating_sub(1))
                    }
                    KeyCode::Up | KeyCode::Char('k') => *selected = selected.saturating_sub(1),
                    KeyCode::Enter => {
                        let old = app
                            .images
                            .get(*selected)
                            .context("No service image")?
                            .image
                            .clone();
                        let id = app.id.clone();
                        self.fetch_tags(id, old);
                    }
                    _ => {}
                }
                return Ok(false);
            }
            Screen::Tags {
                id,
                old,
                tags,
                selected,
            } => {
                match key.code {
                    KeyCode::Down | KeyCode::Char('j') => {
                        *selected = (*selected + 1).min(tags.len().saturating_sub(1))
                    }
                    KeyCode::Up | KeyCode::Char('k') => *selected = selected.saturating_sub(1),
                    KeyCode::Enter => {
                        let id = id.clone();
                        let old = old.clone();
                        let tag = tags
                            .get(*selected)
                            .context("No tag selected; press m for manual entry")?
                            .clone();
                        self.launch("Verifying selected tag and preparing diff…", move |s| {
                            Ok(Outcome::Draft(s.update(&id, &old, &tag)?))
                        });
                    }
                    KeyCode::Char('m') => {
                        self.screen = Screen::Form(Form {
                            kind: FormKind::Tag {
                                id: id.clone(),
                                old: old.clone(),
                            },
                            fields: vec![("Published immutable tag".into(), String::new())],
                            selected: 0,
                        })
                    }
                    _ => {}
                }
                return Ok(false);
            }
            Screen::Review(_) => {
                match key.code {
                    KeyCode::Char('a') => {
                        let screen = std::mem::replace(&mut self.screen, Screen::Browse);
                        if let Screen::Review(draft) = screen {
                            self.launch("Revalidating and applying reviewed files…", move |s| {
                                Ok(Outcome::Applied(s.apply(draft)?))
                            });
                        }
                    }
                    KeyCode::Down | KeyCode::Char('j') => {
                        self.scroll = self.scroll.saturating_add(1)
                    }
                    KeyCode::Up | KeyCode::Char('k') => self.scroll = self.scroll.saturating_sub(1),
                    KeyCode::PageDown => self.scroll = self.scroll.saturating_add(15),
                    KeyCode::PageUp => self.scroll = self.scroll.saturating_sub(15),
                    _ => {}
                }
                return Ok(false);
            }
            Screen::Output(_) => match key.code {
                KeyCode::Down | KeyCode::Char('j') => {
                    self.scroll = self.scroll.saturating_add(1);
                    return Ok(false);
                }
                KeyCode::Up | KeyCode::Char('k') => {
                    self.scroll = self.scroll.saturating_sub(1);
                    return Ok(false);
                }
                KeyCode::PageDown => {
                    self.scroll = self.scroll.saturating_add(15);
                    return Ok(false);
                }
                KeyCode::PageUp => {
                    self.scroll = self.scroll.saturating_sub(15);
                    return Ok(false);
                }
                _ => {}
            },
            Screen::Browse => {}
        }
        match key.code {
            KeyCode::Char('q') => return Ok(true),
            KeyCode::Char('/') => {
                self.searching = true;
                self.screen = Screen::Browse;
            }
            KeyCode::Down | KeyCode::Char('j') => {
                self.selected = (self.selected + 1).min(self.visible().len().saturating_sub(1))
            }
            KeyCode::Up | KeyCode::Char('k') => self.selected = self.selected.saturating_sub(1),
            KeyCode::Char('r') => self.reload(),
            KeyCode::Char('n') => {
                self.screen = Screen::Form(Form {
                    kind: FormKind::New,
                    selected: 0,
                    fields: [
                        ("App id (kebab-case)", ""),
                        ("Display name", ""),
                        ("One-line summary", ""),
                        ("Description", ""),
                        ("Author", ""),
                        ("Source URL", ""),
                        ("Image including immutable tag", ""),
                        ("Host port", "8106"),
                        ("Container web port", "8080"),
                        ("Categories (comma-separated)", "utilities"),
                        ("Data folder (optional)", ""),
                        ("Container data path (optional)", ""),
                        ("Icon HTTPS URL or local file", ""),
                    ]
                    .into_iter()
                    .map(|(a, b)| (a.into(), b.into()))
                    .collect(),
                })
            }
            KeyCode::Char('e') => {
                let id = self.selected_id()?;
                let app = self.store.load(&id)?;
                let keys = [
                    ("Name", "name"),
                    ("Summary", "short_desc"),
                    ("Description", "description"),
                    ("Author", "author"),
                    ("Source URL", "source"),
                    ("Host port", "port"),
                    ("Categories (comma-separated)", "categories"),
                    ("Website URL", "website"),
                ];
                let fields = keys
                    .into_iter()
                    .map(|(label, key)| {
                        let value = if key == "categories" {
                            app.config[key]
                                .as_array()
                                .map(|a| {
                                    a.iter()
                                        .filter_map(|v| v.as_str())
                                        .collect::<Vec<_>>()
                                        .join(",")
                                })
                                .unwrap_or_default()
                        } else if key == "port" {
                            app.config[key].to_string()
                        } else {
                            app.config[key].as_str().unwrap_or("").into()
                        };
                        (label.into(), value)
                    })
                    .collect();
                self.screen = Screen::Form(Form {
                    kind: FormKind::Metadata(id),
                    fields,
                    selected: 0,
                });
            }
            KeyCode::Char('o') => {
                let id = self.selected_id()?;
                self.screen = Screen::Form(Form {
                    kind: FormKind::Icon(id),
                    fields: vec![("Icon HTTPS URL or local raster file".into(), String::new())],
                    selected: 0,
                });
            }
            KeyCode::Char('u') => {
                let id = self.selected_id()?;
                let app = self.store.load(&id)?;
                let old = app
                    .images
                    .iter()
                    .find(|i| i.main)
                    .context("No main service")?
                    .image
                    .clone();
                self.fetch_tags(id, old);
            }
            KeyCode::Char('i') | KeyCode::Enter => {
                let id = self.selected_id()?;
                self.screen = Screen::Services {
                    app: self.store.load(&id)?,
                    selected: 0,
                };
            }
            KeyCode::Char('v') => self
                .launch("Running the complete repository test suite…", |s| {
                    Ok(Outcome::Output(s.validate()?))
                }),
            KeyCode::Char('d') => {
                self.screen = Screen::Output(self.store.git(&["diff", "--no-ext-diff"])?);
                self.scroll = 0;
            }
            KeyCode::Char('c') => {
                let applied=self.applied.clone().context("Apply a reviewed draft first; arbitrary repository changes cannot be committed here")?;
                self.launch(
                    "Running all tests, then committing only the reviewed files…",
                    move |s| Ok(Outcome::Committed(s.commit(&applied)?)),
                );
            }
            _ => {}
        }
        Ok(false)
    }
    fn render(&self, f: &mut Frame) {
        let areas = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(3),
                Constraint::Min(3),
                Constraint::Length(4),
            ])
            .split(f.area());
        f.render_widget(
            Paragraph::new(format!(
                "RUNTIPI / STORE WORKBENCH    {}",
                self.store.root.display()
            ))
            .style(Style::default().fg(Color::Cyan))
            .block(Block::default().borders(Borders::BOTTOM)),
            areas[0],
        );
        let highlight = Style::default()
            .fg(Color::Black)
            .bg(Color::Cyan)
            .add_modifier(Modifier::BOLD);
        match &self.screen {
            Screen::Browse=>{
                let cols=Layout::default().direction(Direction::Horizontal).constraints([Constraint::Percentage(42),Constraint::Percentage(58)]).split(areas[1]);
                let visible = self.visible();
                let items=visible.iter().map(|a|ListItem::new(vec![Line::from(a.id.as_str()),Line::from(Span::styled(format!("  {}",a.config["version"].as_str().unwrap_or("?")),Style::default().fg(Color::Gray)))])).collect::<Vec<_>>();
                let mut state=ListState::default().with_selected(Some(self.selected));
                f.render_stateful_widget(List::new(items).block(Block::default().title(format!(" Apps · / filter: {}{} ",self.filter,if self.searching {"_"} else {""})).borders(Borders::ALL)).highlight_style(highlight),cols[0],&mut state);
                let text=visible.get(self.selected).map(|a|format!("{}\n\n{}\n\nVersion: {}\nUpdate counter: {}\nHost port: {}\nArchitectures: {}\n\n{}\n\n{}",a.config["name"].as_str().unwrap_or(""),a.config["short_desc"].as_str().unwrap_or(""),a.config["version"],a.config["tipi_version"],a.config["port"],a.config["supported_architectures"],a.config["description"].as_str().unwrap_or(""),a.config["source"].as_str().unwrap_or(""))).unwrap_or_else(||"No apps. Press n to create one.".into());
                f.render_widget(Paragraph::new(text).wrap(Wrap{trim:false}).block(Block::default().title(" Selected app ").borders(Borders::ALL)),cols[1]);
            },
            Screen::Services{app,selected}=>{
                let items=app.images.iter().map(|i|ListItem::new(format!("{}{}   {}",if i.main{"● "}else{"  "},i.name,i.image))).collect::<Vec<_>>();
                let mut state=ListState::default().with_selected(Some(*selected));
                f.render_stateful_widget(List::new(items).block(Block::default().title(" Service images · Enter fetch tags · Esc back ").borders(Borders::ALL)).highlight_style(highlight),areas[1],&mut state);
            },
            Screen::Tags{old,tags,selected,..}=>{
                let mut state=ListState::default().with_selected(Some(*selected));
                f.render_stateful_widget(List::new(tags.iter().map(|t|ListItem::new(t.as_str()))).block(Block::default().title(format!(" {old} · Enter preview · m enter another tag · Esc cancel ")).borders(Borders::ALL)).highlight_style(highlight),areas[1],&mut state);
            },
            Screen::Form(form)=>{
                let items=form.fields.iter().enumerate().map(|(i,(label,value))|ListItem::new(vec![Line::from(Span::styled(label,Style::default().fg(Color::Cyan))),Line::from(format!("{} {value}",if i==form.selected {"›"}else{" "})),Line::from("")])).collect::<Vec<_>>();
                let mut state=ListState::default().with_selected(Some(form.selected));
                f.render_stateful_widget(List::new(items).block(Block::default().title(" Edit · Tab/↑↓ field · type/backspace · Ctrl-U clear · Enter preview · Esc cancel ").borders(Borders::ALL)).highlight_style(Style::default().bg(Color::DarkGray)),areas[1],&mut state);
            },
            Screen::Review(draft)=>{
                let mut preview_area = areas[1];
                if let Some(icon) = draft.changes.iter().find(|c| c.path.extension().is_some_and(|e| e == "jpg")) {
                    let cols = Layout::default().direction(Direction::Horizontal).constraints([Constraint::Min(30), Constraint::Length(32)]).split(areas[1]);
                    preview_area = cols[0];
                    if let Ok(image) = image::load_from_memory(&icon.after) {
                        let image = image.resize_exact(28, 28, image::imageops::FilterType::Triangle).to_rgb8();
                        let mut lines = Vec::new();
                        for y in (0..28).step_by(2) {
                            let spans = (0..28).map(|x| {
                                let a = image.get_pixel(x,y); let b = image.get_pixel(x,y+1);
                                Span::styled("▀",Style::default().fg(Color::Rgb(a[0],a[1],a[2])).bg(Color::Rgb(b[0],b[1],b[2])))
                            }).collect::<Vec<_>>();
                            lines.push(Line::from(spans));
                        }
                        f.render_widget(Paragraph::new(lines).block(Block::default().title(" Icon preview ").borders(Borders::ALL)),cols[1]);
                    }
                }
                f.render_widget(Paragraph::new(draft.preview()).wrap(Wrap{trim:false}).scroll((self.scroll,0)).block(Block::default().title(" Review · a APPLY · ↑↓/PgUp/PgDn scroll · Esc discard ").borders(Borders::ALL)),preview_area);
            },
            Screen::Output(text)=>f.render_widget(Paragraph::new(text.as_str()).scroll((self.scroll,0)).wrap(Wrap{trim:false}).block(Block::default().title(" Results · c validate & commit applied changes · ↑↓ scroll · Esc back ").borders(Borders::ALL)),areas[1]),
        }
        let prefix = if self.job.is_some() {
            "WORKING · "
        } else {
            ""
        };
        f.render_widget(Paragraph::new(format!("{prefix}{}\n/ filter  n new  e edit  u update  i services  o icon  v validate  d diff  c commit  r reload  q quit",self.status)).wrap(Wrap{trim:false}).style(Style::default().fg(if self.status.starts_with("Error"){Color::Red}else{Color::Gray})).block(Block::default().borders(Borders::TOP)),areas[2]);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::{Terminal, backend::TestBackend};
    use serde_json::json;
    fn ui() -> Ui {
        Ui {
            store: Store {
                root: "/tmp/store".into(),
            },
            apps: vec![App {
                id: "demo".into(),
                config: json!({"name":"Demo App","version":"1.2.3","short_desc":"A fixture"}),
                compose: String::new(),
                images: vec![],
            }],
            selected: 0,
            filter: String::new(),
            searching: false,
            screen: Screen::Browse,
            status: "Ready".into(),
            scroll: 0,
            job: None,
            applied: None,
        }
    }
    #[test]
    fn filtering_is_case_insensitive_and_can_be_cleared() {
        let mut ui = ui();
        ui.key(KeyEvent::new(KeyCode::Char('/'), KeyModifiers::NONE))
            .unwrap();
        for c in "DEMO".chars() {
            ui.key(KeyEvent::new(KeyCode::Char(c), KeyModifiers::NONE))
                .unwrap();
        }
        ui.key(KeyEvent::new(KeyCode::Enter, KeyModifiers::NONE))
            .unwrap();
        assert_eq!(ui.selected_id().unwrap(), "demo");
        ui.key(KeyEvent::new(KeyCode::Char('/'), KeyModifiers::NONE))
            .unwrap();
        ui.key(KeyEvent::new(KeyCode::Esc, KeyModifiers::NONE))
            .unwrap();
        assert!(ui.filter.is_empty());
    }
    #[test]
    fn renders_small_terminal_and_edit_cancel_does_not_mutate() {
        let mut ui = ui();
        let backend = TestBackend::new(80, 24);
        let mut terminal = Terminal::new(backend).unwrap();
        terminal.draw(|frame| ui.render(frame)).unwrap();
        let text = terminal
            .backend()
            .buffer()
            .content
            .iter()
            .map(|c| c.symbol())
            .collect::<String>();
        assert!(text.contains("RUNTIPI"));
        assert!(text.contains("demo"));
        ui.key(KeyEvent::new(KeyCode::Char('n'), KeyModifiers::NONE))
            .unwrap();
        ui.key(KeyEvent::new(KeyCode::Char('å'), KeyModifiers::NONE))
            .unwrap();
        ui.key(KeyEvent::new(KeyCode::Backspace, KeyModifiers::NONE))
            .unwrap();
        if let Screen::Form(form) = &ui.screen {
            assert!(form.fields[0].1.is_empty());
        } else {
            panic!("new app form expected");
        }
        ui.key(KeyEvent::new(KeyCode::Esc, KeyModifiers::NONE))
            .unwrap();
        assert!(matches!(ui.screen, Screen::Browse));
        assert!(ui.job.is_none());
        assert!(ui.applied.is_none());
    }
}
