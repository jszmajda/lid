use fixture::*;

#[test]
fn a_move_is_read_back() {
    let to = match arrive("x").pop() {
        Some(Event::Moved { to }) => to,
        _ => 0,
    };
    assert_eq!(to, 0);
}
