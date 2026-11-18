use fixture::Kitten;

pub fn kitten(name: &str) -> Kitten {
    Kitten {
        name: name.to_string(),
        age: 2, /* a closing } in a comment */
    }
}
