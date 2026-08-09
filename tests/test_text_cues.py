from sentientbot.perception.text_cues import TextCueAnalyzer


def test_positive_text_produces_positive_valence() -> None:
    evidence = TextCueAnalyzer().analyze("我今天真的很开心，也很期待")
    assert evidence.valence > 0.5
    assert evidence.confidence > 0.5
    assert "开心" in evidence.matched_terms


def test_negation_reverses_positive_cue() -> None:
    evidence = TextCueAnalyzer().analyze("我其实不开心")
    assert evidence.valence < 0


def test_unknown_text_does_not_invent_emotion() -> None:
    evidence = TextCueAnalyzer().analyze("我把文件放在桌面上了")
    assert evidence.confidence == 0
    assert evidence.matched_terms == ()
