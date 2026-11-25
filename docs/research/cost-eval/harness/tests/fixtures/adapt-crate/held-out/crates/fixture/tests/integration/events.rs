use fixture::*;

#[test]
fn a_move_has_a_destination() {
    let e = Event::Moved { to: 3 };
    assert!(matches!(e, Event::Moved { to: 3, .. }));
}
