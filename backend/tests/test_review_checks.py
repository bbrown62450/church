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
        # Any whitespace run between the words (a line break, double spaces, a no-break space) still
        # makes the phrase, quoted with one space.
        ("Gather us in this\nseason of Advent.", ['Stock phrase "in this season of". Say it more naturally.']),
        ("Gather us in this  season of Lent.", ['Stock phrase "in this season of". Say it more naturally.']),
        ("Leader: on\nthis third Sunday we sing.", ['Stock phrase "on this third Sunday". Say it more naturally.']),
        ("In This Ordinary  Time, keep us.", ['Stock phrase "In This Ordinary Time". Say it more naturally.']),
        ("In\u00a0This Ordinary\u00a0Time, keep us.",
         ['Stock phrase "In This Ordinary Time". Say it more naturally.']),
        ("as\twe \r\n journey", ['Stock phrase "as we journey". Say it more naturally.']),
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
        ("Through these ordinary\ntime days.", ["Names Ordinary Time. Leave the season unnamed."]),
        ("Keep us in ordinary\u00a0\u00a0time.", ["Names Ordinary Time. Leave the season unnamed."]),
    ]
    for text, expected in cases:
        assert texts(check_card(text)) == expected, text
    (note,) = check_card("Ordinary Time is long.")
    assert note == Note("rules", "Names Ordinary Time. Leave the season unnamed.") and note.match == "Ordinary Time"
    (note,) = check_card("Ordinary \n Time is long.")
    assert note.match == "Ordinary Time"
    (note,) = check_card("in this\n\u00a0season of waiting")
    assert note.match == "in this season of"


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
        ("Gen 1–2 tells of creation.", "Gen 1–2"),
        ("Psalm 1-2 open the psalter.", "Psalm 1-2"),
        ("Like Mark\n4:35-41, calm us.", "Mark 4:35-41"),       # quoted with one space
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
    assert check_card(f"On this {giant} Sunday we gather.") == []   # a word is 1 to 30 characters
    for spaces in (" " * 5000, "\n" * 5000, "\u00a0" * 5000):        # any run still makes a stock phrase
        (note,) = check_card("on this Third" + spaces + "Sunday")
        assert note.text == 'Stock phrase "on this Third Sunday". Say it more naturally.'
        assert len(note.text) <= MAX_NOTE_CHARS and len(note.match) <= MAX_NOTE_CHARS
    # The longest stock phrase (four words of 30) and the longest opening pair keep their whole note.
    longest = "on this " + " ".join(["w" * 30] * 4) + " Sunday"
    (note,) = check_card(longest)
    assert note.match == longest and note.text.endswith('". Say it more naturally.')
    assert len(note.text) <= MAX_NOTE_CHARS
    word = "b" * 14 + "’" + "c" * 15                        # 30 characters, an apostrophe inside: one word
    notes = check_openings([f"{word} {word}, hear us.", f"{word} {word}! hear us."])
    assert notes == [Note("repetition", f'Several prayers open with "{word} {word}".')]
    assert len(notes[0].text) <= MAX_NOTE_CHARS and len(notes[0].match) <= MAX_NOTE_CHARS
    # Over 30 characters is no word, letters alone or apostrophe-joined parts, so the opening is the
    # two words after it.
    chain = "’".join(["b" * 30] * 200)                     # 6 199 characters, apostrophes inside
    short_chain = "b" * 15 + "’" + "c" * 15                 # 31 characters
    for long_word in (giant, chain, short_chain):
        assert check_openings([f"{long_word} Gracious God, hear.", f"{long_word} gracious god! come."]) == [
            Note("repetition", 'Several prayers open with "Gracious God".')], long_word[:40]

