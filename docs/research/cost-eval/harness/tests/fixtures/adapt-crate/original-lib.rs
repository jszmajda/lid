//! The crate before the arm's change: the held-out tests were written against this.

#[derive(Debug, Clone, PartialEq)]
pub struct Kitten {
    pub name: String,
    pub age: u32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mood {
    Calm,
    Hungry,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Litter {
    pub size: u32,
}

#[derive(Debug, Clone, PartialEq)]
pub enum Event {
    Born(String),
    Napped,
    Moved { to: u32 },
}

pub fn greet(k: &Kitten) -> String {
    format!("hello {}", k.name)
}

pub fn wave() -> &'static str {
    "hi"
}

pub fn arrive(name: &str) -> Vec<Event> {
    vec![Event::Born(name.to_string())]
}

pub fn calm() -> Mood {
    Mood::Calm
}

/// A kitten's saved form, as JSON.
pub fn save(k: &Kitten) -> String {
    format!("{{\"name\":\"{}\",\"age\":{}}}", k.name, k.age)
}
