use crate::common::kitten;
use fixture::*;

/// Two saved forms match when every field the first had is the same in the second.
fn same_shape(was: &str, now: &str) -> bool {
    was == now
}

#[test]
fn a_saved_kitten_is_exact() {
    assert_eq!(save(&kitten("Fern")), r#"{"name":"Fern","age":2}"#);
}

#[test]
fn a_resaved_kitten_keeps_its_shape() {
    let was = r#"{"name":"Fern","age":2}"#.to_string();
    let now = save(&kitten("Fern"));
    assert!(
        same_shape(&was, &now),
        "the saved kitten changed: {was} -> {now}"
    );
}
