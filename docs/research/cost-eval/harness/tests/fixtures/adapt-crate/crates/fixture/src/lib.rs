//! The crate as the arm left it. Against the original: Kitten gained six fields, Moved gained `by`, Event gained
//! Renamed (which arrivals now emit), Litter gained a mood with no Default, and wave became hello.

use std::collections::HashMap;

pub type Ticks = u64;

#[derive(Debug, Clone, PartialEq, Default)]
pub struct Collar {
    pub colour: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Kitten {
    pub name: String,
    pub age: u32,
    /// What the household calls her.
    pub nickname: Option<String>,
    #[doc = "Shown on her card."]
    pub tags: Vec<String>,
    pub collar: Collar,
    pub naps: Ticks,
    pub friends: HashMap<String, u32>,
    pub weight: f32,
    pub indoor: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mood {
    Calm,
    Hungry,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Litter {
    pub size: u32,
    pub mood: Mood,
}

#[derive(Debug, Clone, PartialEq)]
pub enum Event {
    Born(String),
    Napped,
    Moved { to: u32, by: Option<String> },
    Renamed { from: String },
}

pub fn greet(k: &Kitten) -> String {
    format!("hello {}", k.name)
}

pub fn hello() -> &'static str {
    "hi"
}

pub fn arrive(name: &str) -> Vec<Event> {
    vec![Event::Born(name.to_string()), Event::Renamed { from: name.to_string() }]
}

pub fn calm() -> Mood {
    Mood::Calm
}

/// A kitten's saved form, as JSON.
pub fn save(k: &Kitten) -> String {
    let nickname = match &k.nickname {
        Some(n) => format!("\"{n}\""),
        None => "null".to_string(),
    };
    format!("{{\"name\":\"{}\",\"age\":{},\"nickname\":{}}}", k.name, k.age, nickname)
}
