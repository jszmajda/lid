use fixture::*;

#[test]
fn a_litter_has_a_size() {
    let l = Litter { size: 3 };
    assert_eq!(l.size, 3);
    assert_eq!(calm(), Mood::Calm);
}
