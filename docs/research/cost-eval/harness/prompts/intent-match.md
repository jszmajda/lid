You are checking rules that someone wrote down about a software system against the system's intended behaviour.

The intended behaviour is a list of items. Current items hold now. Retired items held once and have since been dropped or replaced, so they no longer hold.

{ITEMS}

The rules to check:

{RULES}

Map every rule to exactly one of these:

- **agrees:** a system following the rule would behave as one or more current items say, in the cases the rule covers, and nothing in the rule conflicts with them. Wording, names, and level of detail may differ. List every current item the rule agrees with. Set `extent` to `whole` when the rule states all of an item's behaviour, and `part` when it states some of it.
- **contradicts:** a system following the rule would behave against a current item in a case that item covers. List the current items it contradicts.
- **stale:** the rule states retired intent: behaviour a retired item describes that the current items no longer hold. List the retired items. A rule that states retired intent is stale even when it also conflicts with a current item. A rule stating something a retired item said that a current item still says (because the current intent kept that part) agrees; it isn't stale.
- **incidental:** no item states or rules out what the rule says. Details of an interface or implementation that no item mentions (names of operations or fields, error codes, formats, limits, internal structure) are incidental.

When a rule fits more than one, the first that fits wins in this order: stale, contradicts, agrees, incidental. A rule that agrees with one item and contradicts another contradicts.

For each rule give:

- `rule`: its number (the number after R);
- `classification`;
- `items`: the item IDs it maps to, empty for incidental;
- `extent`: `whole` or `part` for agrees, `none` otherwise;
- `rule_quote`: words copied exactly from the rule that decide the mapping;
- `item_quotes`: for each listed item, words copied exactly from that item's text, empty for incidental;
- `reason`: one or two full sentences, at least ten words, saying why the rule maps as it does, for an easy agreement as much as a hard case.

Judge each rule by its content alone, against the items as written.
