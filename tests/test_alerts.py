"""Parser cases taken verbatim from @UkraineAlarmSignal, including ones the Vadimkin CSV gets wrong."""

from datetime import UTC, datetime

from ua_alert_forecast.alerts import parse_post

TS = datetime(2026, 10, 1, tzinfo=UTC)


def summary(text: str) -> list[tuple[str, str, str]]:
    return [(e.kind, e.detail, e.oblast) for e in parse_post(text, TS)]


def test_single_place_start():
    assert summary("🔴 Павлоградський район (Дніпропетровська обл.)\nЧервоний рівень тривоги. Прямуйте в укриття!") == [
        ("start", "red", "dnipropetrovska")
    ]


def test_tag_wins_over_place_name():
    # CSV maps these to Volyn ("Луцьк" substring) and Lviv.
    assert summary("🟡 Прилуцький район (Чернігівська обл.)\nЖовтий рівень тривоги.") == [("start", "yellow", "chernihivska")]
    assert summary("🟡 Подільський район (Одеська обл.)\nЖовтий рівень тривоги.") == [("start", "yellow", "odeska")]


def test_list_post_credits_every_oblast():
    text = (
        "🟡 Жовтий рівень тривоги\n• Миколаївський район (Миколаївська обл.)\n"
        "• Богодухівський район (Харківська обл.)\n• Херсонський район (Херсонська обл.)"
    )
    assert [o for *_, o in summary(text)] == ["mykolaivska", "kharkivska", "khersonska"]


def test_mixed_sections():
    text = (
        "🟡 Жовтий рівень тривоги\n• Березівський район (Одеська обл.)\n\n"
        "🟢 Відбій тривоги\n• Нікопольський район (Дніпропетровська обл.)\n• Ізюмський район (Харківська обл.)"
    )
    assert summary(text) == [("start", "yellow", "odeska"), ("end", "", "dnipropetrovska"), ("end", "", "kharkivska")]


def test_kyiv_city_and_threats():
    assert summary("🟡 Київ\nЖовтий рівень тривоги. Прямуйте в укриття!") == [("start", "yellow", "kyiv")]
    assert summary("🛸 Нивки (Київ)\nЗагроза застосування БПЛА.") == [("threat", "drone", "kyiv")]
    assert summary("💥 Харківська обл.\nЗагроза артобстрілу.") == [("threat", "shelling", "kharkivska")]


def test_ignored_posts():
    assert summary("🟡 Харківський район (Харківська обл.)\nВідбій червоної тривоги, жовта тривога ще триває.") == []
    assert summary("Мапа тривог станом на 12:00 – 29 вересня:\n\n🔴 Червона тривога у 28 районах") == []
    assert summary("🛸 Сімферополь (Крим)\nЗагроза застосування БПЛА.") == []


def test_pre_reform_format():
    assert summary("🚨 Харків (Харківська обл.)\nПовітряна тривога. Прямуйте в укриття!") == [("start", "air", "kharkivska")]


def test_pre_reform_list_without_bullets():
    text = "🚨 Повітряна тривога\nБогодухівський район (Харківська обл.)\nЧугуївський район (Харківська обл.)"
    assert summary(text) == [("start", "air", "kharkivska"), ("start", "air", "kharkivska")]
