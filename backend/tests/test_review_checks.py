"""review_checks: the reviewer's code checks (reviewer spec, "Layer 1: code
checks" and Testing; slice 4 spec, reviewer amendment). Pure, so table-driven:
each test loops over its cases inside one function."""
import scripture_refs as sr
from review_checks import MAX_NOTE_CHARS, Note, check_card, check_openings, scripture_book_keys


def texts(notes):
    return [n.text for n in notes]


def test_stock_seasonal_phrases_are_flagged_whatever_their_case():
    cases = [
        ("Gather us in this season of waiting.", ['Stock phrase "in this season of". Say it more naturally.']),
        ("AS WE JOURNEY toward the cross, hold us.", ['Stock phrase "AS WE JOURNEY". Say it more naturally.']),
        ("On this Third Sunday of Easter we praise you.",
         ['Stock phrase "On this Third Sunday". Say it more naturally.']),
        ("on this twenty-first Sunday after Pentecost",
         ['Stock phrase "on this twenty-first Sunday". Say it more naturally.']),
        ("Meet us in this Ordinary Time.", ['Stock phrase "in this Ordinary Time". Say it more naturally.']),
        # Plain seasonal themes and an unadorned "this Sunday" are not stock phrases.
        ("Christ is risen! Easter joy fills us. Easter hope sends us.", []),
        ("We gather on this Sunday morning.", []),
        ("In this season, as we journey together", ['Stock phrase "as we journey". Say it more naturally.']),
    ]
    for text, expected in cases:
        notes = check_card(text)
        assert texts(notes) == expected, text
        assert all(n.tag == "rules" and n.source == "code" for n in notes)


def test_naming_ordinary_time_is_flagged_once_wherever_it_appears():
    cases = [
        ("Through these ordinary time days, keep us.", ["Names Ordinary Time. Leave the season unnamed."]),
        ("Ordinary Time teaches patience. In ORDINARY TIME we grow.",
         ["Names Ordinary Time. Leave the season unnamed."]),
        # Inside the stock phrase only the stock-phrase note shows (one point, one note).
        ("Walk with us in this ordinary time.", ['Stock phrase "in this ordinary time". Say it more naturally.']),
        ("In this ordinary time, and all ordinary time, keep us.",
         ['Stock phrase "In this ordinary time". Say it more naturally.',
          "Names Ordinary Time. Leave the season unnamed."]),
        ("An ordinary day, a quiet time.", []),
    ]
    for text, expected in cases:
        assert texts(check_card(text)) == expected, text
    (note,) = check_card("Ordinary Time is long.")
    assert note == Note("rules", "Names Ordinary Time. Leave the season unnamed.") and note.match == "Ordinary Time"


def test_every_book_name_and_alias_in_scripture_refs_books_is_caught_with_a_chapter():
    keys = scripture_book_keys()
    assert len(keys) == sum(1 + len(b.aliases) for b in sr.BOOKS)   # the one table, no second list
    for key in keys:
        cited = " ".join(word.capitalize() for word in key.split(" ")) + " 3"
        notes = check_card(f"As we read in {cited}, God is near.")
        assert texts(notes) == [f"Cites {cited}. Draw on the reading's themes without naming it."], key
        assert notes[0].match == cited
    cases = [
        ("Like the storm in Mark 4:35-41, calm us.", "Mark 4:35-41"),
        ("Speak, Lord (1 Sam 3:10), for we listen.", "1 Sam 3:10"),
        ("as 1 Sam. 3:10 tells", "1 Sam. 3:10"),
        ("Psalm 1 sings of trees by water.", "Psalm 1"),
        ("Psalm 119:105 is a lamp.", "Psalm 119:105"),
        ("Ps. 23 is a comfort.", "Ps. 23"),
        ("In 1 Corinthians 13 love is patient.", "1 Corinthians 13"),
    ]
    for text, cited in cases:
        assert texts(check_card(text)) == [f"Cites {cited}. Draw on the reading's themes without naming it."], text


def test_no_false_hit_on_ordinary_words():
    for text in (
        "We mark this day with joy.",
        "Mark the moment with silence.",
        "We mark 3 years together.",            # a verb, lower case
        "Write our names in the book of life.",
        "Isaiah's vision fills the temple.",    # a book with no chapter
        "There is 1 God, and Acts of mercy follow.",
        "A song 2 voices can share.",
        "Psalm 200 voices rise.",               # no book has 200 chapters: parse_refs reads no span
        "Remember Mark 4b.",                    # not a chapter number
        "Job 3s and Mark4 are not references.",
    ):
        assert check_card(text) == [], text


def test_a_card_s_notes_follow_the_table_s_order_once_each():
    text = ("Mark 4:35-41 again: as we journey, as we journey, through Ordinary Time, "
            "in this season of hope; Mark 4:35-41.")
    assert texts(check_card(text)) == [
        'Stock phrase "as we journey". Say it more naturally.',
        'Stock phrase "in this season of". Say it more naturally.',
        "Names Ordinary Time. Leave the season unnamed.",
        "Cites Mark 4:35-41. Draw on the reading's themes without naming it.",
    ]
    assert check_card("") == [] and check_card("   ") == []


def test_repeated_openings_across_cards_go_to_the_service_box():
    cards = [
        ("call_to_worship", "Leader: Gracious God, you call us.\nPeople: We come."),
        ("opening_prayer", "Gracious God, we praise you."),
        ("prayer_of_confession", "People: gracious   GOD! we confess."),
        ("prayer_for_illumination", "Holy Spirit, open our ears."),
        ("offertory_prayer", "Holy Spirit; bless these gifts."),
        ("benediction", "Go in peace."),
        ("assurance", "Leader:"),
    ]
    notes = check_openings([text for _section, text in cards])
    assert notes == [
        Note("repetition", 'Several prayers open with "Gracious God".'),
        Note("repetition", 'Several prayers open with "Holy Spirit".'),
    ]
    assert [n.match for n in notes] == ["Gracious God", "Holy Spirit"]
    assert check_openings(["Gracious God, hear us.", "Loving God, hear us."]) == []
    assert check_openings(["God", "God"]) == []              # one word is not an opening pair
    many = [f"Word{i} Two, a" for i in range(4) for _ in range(2)]
    assert len(check_openings(many)) == 4                    # the merge caps the box at 3, not the check


def test_a_giant_word_never_makes_a_note_over_the_cap():
    giant = "a" * 5000
    chain = "’".join(["b" * 30] * 200)                     # one word of 6 199 characters, apostrophes inside
    assert check_card(f"On this {giant} Sunday we gather.") == []   # a word is 1 to 30 characters
    (note,) = check_card("on this Third" + " " * 5000 + "Sunday")    # the spaces still make a stock phrase
    assert len(note.text) <= MAX_NOTE_CHARS and len(note.match) <= MAX_NOTE_CHARS
    notes = check_openings([f"{chain} {chain}, hear us.", f"{chain} {chain}! hear us."])
    assert len(notes) == 1 and len(notes[0].text) <= MAX_NOTE_CHARS and len(notes[0].match) <= MAX_NOTE_CHARS
    # A run of over 30 letters is no word, so the opening is the two words after it.
    assert check_openings([f"{giant} Gracious God, hear.", f"{giant} gracious god! come."]) == [
        Note("repetition", 'Several prayers open with "Gracious God".')]
