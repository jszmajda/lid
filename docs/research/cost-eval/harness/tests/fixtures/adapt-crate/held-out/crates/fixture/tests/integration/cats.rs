use crate::common::kitten;
use fixture::*;

fn describe(e: &Event) -> &'static str {
    match e {
        Event::Born(_) => "born", // a brace { in a comment
        Event::Napped => "napped",
        Event::Moved { .. } => "moved"
    }
}

#[test]
fn a_kitten_is_greeted() {
    let k = Kitten { name: "Moss {".to_string(), age: 1 };
    assert_eq!(greet(&k), "hello Moss {");
    assert_eq!(describe(&Event::Napped), "napped");
}

#[test]
fn a_helper_kitten_is_two() {
    assert_eq!(kitten("Fern").age, 2);
}

#[test]
fn every_arrival_is_described() {
    let k = kitten("Fern");
    for e in arrive(&k.name) {
        match e {
            Event::Born(_) => {}
            Event::Napped => {
                panic!("no naps on arrival")
            }
            Event::Moved { .. } => {}
        }
    }
}
