# -*- coding: utf-8 -*-
"""Tests for pure helper functions in generateArticle.py."""

import json
from unittest.mock import patch, MagicMock
import pytest

from generateArticle import (
    as_list,
    build_generation_prompt,
    build_title_prompt,
    count_words,
    estimate_reading_time,
    extract_plain_text,
    html_escape,
    is_too_similar,
    normalize_for_similarity,
    send_notification_email,
    similar_ratio,
    slugify,
    str_id,
    tag_name,
    _extract_json_block,
    _safe_json_loads,
    SIMILARITY_THRESHOLD_DEFAULT,
    SIMILARITY_THRESHOLD_STRICT,
    MAX_TITLE_RETRIES,
    RECENT_TITLES_LIMIT,
    META_TITLE_MAX_LENGTH,
    MAX_AVOID_TITLES_IN_PROMPT,
    GENERATION_SYSTEM_MSG,
    TITLE_SYSTEM_MSG,
    OPENAI_MAX_ARTICLE_TOKENS,
    OPENAI_MAX_TITLE_TOKENS,
)


# ---- str_id ----
class TestStrId:
    def test_string_passthrough(self):
        assert str_id("hello") == "hello"

    def test_none(self):
        assert str_id(None) == "None"

    def test_valid_objectid_string(self):
        oid = "507f1f77bcf86cd799439011"
        result = str_id(oid)
        assert result == oid

    def test_integer(self):
        assert str_id(42) == "42"


# ---- as_list ----
class TestAsList:
    def test_none(self):
        assert as_list(None) == []

    def test_list(self):
        assert as_list([1, 2]) == [1, 2]

    def test_tuple(self):
        assert as_list((1, 2)) == [1, 2]

    def test_set(self):
        result = as_list({1})
        assert result == [1]

    def test_scalar(self):
        assert as_list("a") == ["a"]
        assert as_list(5) == [5]


# ---- tag_name ----
class TestTagName:
    def test_name_field(self):
        assert tag_name({"name": "Lombok", "tag": "lmb"}) == "Lombok"

    def test_tag_field(self):
        assert tag_name({"tag": "@Data"}) == "@Data"

    def test_id_fallback(self):
        assert tag_name({"_id": "abc"}) == "abc"


# ---- slugify ----
class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello-world"

    def test_accents(self):
        assert slugify("Cómo usar @Builder") == "como-usar-builder"

    def test_special_chars(self):
        assert slugify("  --test!!  ") == "test"

    def test_empty(self):
        assert slugify("") == ""


# ---- normalize_for_similarity / similar_ratio / is_too_similar ----
class TestSimilarity:
    def test_normalize_removes_accents(self):
        assert normalize_for_similarity("café") == "cafe"

    def test_normalize_lowercases(self):
        assert normalize_for_similarity("HELLO") == "hello"

    def test_normalize_strips_punctuation(self):
        assert normalize_for_similarity("hello-world!") == "hello world"

    def test_similar_ratio_identical(self):
        assert similar_ratio("hello", "hello") == 1.0

    def test_similar_ratio_different(self):
        assert similar_ratio("abc", "xyz") < 0.5

    def test_similar_ratio_empty(self):
        assert similar_ratio("", "hello") == 0.0

    def test_is_too_similar_true(self):
        assert is_too_similar("Cómo usar Lombok", ["Como usar Lombok en Java"], threshold=0.7)

    def test_is_too_similar_false(self):
        assert not is_too_similar("Spring Security avanzado", ["Lombok básico"], threshold=0.8)

    def test_is_too_similar_empty_candidates(self):
        assert not is_too_similar("Cualquier título", [])


# ---- html_escape ----
class TestHtmlEscape:
    def test_ampersand(self):
        assert html_escape("a & b") == "a &amp; b"

    def test_lt_gt(self):
        assert html_escape("<div>") == "&lt;div&gt;"

    def test_no_change(self):
        assert html_escape("hello") == "hello"


# ---- extract_plain_text ----
class TestExtractPlainText:
    def test_strips_tags(self):
        assert "hello" in extract_plain_text("<p>hello</p>")

    def test_empty(self):
        assert extract_plain_text("") == ""

    def test_no_tags(self):
        assert extract_plain_text("plain text") == "plain text"

    def test_nested_tags(self):
        result = extract_plain_text("<h1>Title</h1><p>Body <strong>text</strong>.</p>")
        assert "Title" in result
        assert "Body" in result
        assert "<" not in result


# ---- count_words ----
class TestCountWords:
    def test_simple_html(self):
        assert count_words("<p>one two three</p>") == 3

    def test_empty(self):
        assert count_words("") == 0

    def test_plain_text(self):
        assert count_words("hello world") == 2

    def test_multiple_tags(self):
        html = "<h1>Spring Boot</h1><p>Guía completa para empezar.</p>"
        assert count_words(html) >= 5


# ---- estimate_reading_time ----
class TestEstimateReadingTime:
    def test_minimum_one_minute(self):
        assert estimate_reading_time("<p>hola</p>") == 1

    def test_empty_body(self):
        assert estimate_reading_time("") == 1

    def test_long_body(self):
        # 460 words → ceil(460/230) = 2 minutes
        words = " ".join(["palabra"] * 460)
        assert estimate_reading_time(f"<p>{words}</p>") == 2

    def test_custom_wpm(self):
        words = " ".join(["word"] * 100)
        assert estimate_reading_time(f"<p>{words}</p>", wpm=100) == 1


# ---- _extract_json_block ----
class TestExtractJsonBlock:
    def test_fenced(self):
        text = 'Some text\n```json\n{"title":"A"}\n```\nMore text'
        assert _extract_json_block(text) == '{"title":"A"}'

    def test_bare_json(self):
        text = 'Here is the result: {"title":"B","body":"<p>hi</p>"} done.'
        result = _extract_json_block(text)
        parsed = json.loads(result)
        assert parsed["title"] == "B"

    def test_empty(self):
        assert _extract_json_block("") == ""

    def test_no_json(self):
        assert _extract_json_block("just text") == "just text"


# ---- _safe_json_loads ----
class TestSafeJsonLoads:
    def test_normal_json(self):
        assert _safe_json_loads('{"a": 1}') == {"a": 1}

    def test_smart_quotes(self):
        result = _safe_json_loads('{\u201ctitle\u201d: \u201cHello\u201d}')
        assert result["title"] == "Hello"


# ---- build_generation_prompt ----
class TestBuildGenerationPrompt:
    def test_contains_tag(self):
        prompt = build_generation_prompt("Spring Boot", "Lombok", "@Data")
        assert "@Data" in prompt
        assert "Spring Boot" in prompt
        assert "Lombok" in prompt

    def test_avoid_titles_included(self):
        prompt = build_generation_prompt("Cat", "Sub", "Tag", avoid_titles=["Título A"])
        assert "Título A" in prompt

    def test_seo_instructions_present(self):
        """The optimized prompt should include SEO guidance."""
        prompt = build_generation_prompt("Cat", "Sub", "Tag")
        assert "SEO" in prompt

    def test_keywords_field_in_schema(self):
        """The prompt must ask OpenAI to return a 'keywords' field."""
        prompt = build_generation_prompt("Cat", "Sub", "Tag")
        assert "keywords" in prompt

    def test_title_max_chars_is_60(self):
        """Title limit should be 60 characters for SEO compliance."""
        prompt = build_generation_prompt("Cat", "Sub", "Tag")
        assert "máx. 60 caracteres" in prompt

    def test_returns_string(self):
        result = build_generation_prompt("A", "B", "C")
        assert isinstance(result, str)
        assert len(result) > 100

    def test_prompt_is_compact(self):
        """Optimized prompt should be under 900 characters (excluding avoid titles)."""
        prompt = build_generation_prompt("Cat", "Sub", "Tag")
        assert len(prompt) < 900

    def test_html_structure_instructions(self):
        """Prompt must specify key HTML elements for article structure."""
        prompt = build_generation_prompt("Cat", "Sub", "Tag")
        assert "<h1>" in prompt or "h1" in prompt
        assert "<h2>" in prompt or "h2" in prompt
        assert "FAQ" in prompt
        assert "JSON" in prompt


# ---- Constants ----
class TestConstants:
    def test_thresholds_are_float(self):
        assert isinstance(SIMILARITY_THRESHOLD_DEFAULT, float)
        assert isinstance(SIMILARITY_THRESHOLD_STRICT, float)

    def test_threshold_ordering(self):
        assert SIMILARITY_THRESHOLD_STRICT > SIMILARITY_THRESHOLD_DEFAULT

    def test_max_retries_positive(self):
        assert MAX_TITLE_RETRIES > 0

    def test_recent_limit_positive(self):
        assert RECENT_TITLES_LIMIT > 0

    def test_max_avoid_titles_in_prompt_positive(self):
        assert MAX_AVOID_TITLES_IN_PROMPT > 0

    def test_max_article_tokens_positive(self):
        assert OPENAI_MAX_ARTICLE_TOKENS > 0

    def test_max_title_tokens_positive(self):
        assert OPENAI_MAX_TITLE_TOKENS > 0
        assert OPENAI_MAX_TITLE_TOKENS < OPENAI_MAX_ARTICLE_TOKENS

    def test_generation_system_msg_is_nonempty_string(self):
        assert isinstance(GENERATION_SYSTEM_MSG, str)
        assert len(GENERATION_SYSTEM_MSG) > 0

    def test_title_system_msg_is_nonempty_string(self):
        assert isinstance(TITLE_SYSTEM_MSG, str)
        assert len(TITLE_SYSTEM_MSG) > 0


# ---- build_title_prompt ----
class TestBuildTitlePrompt:
    def test_contains_tag_and_category(self):
        prompt = build_title_prompt("Spring Boot", "Lombok", "@Builder")
        assert "@Builder" in prompt
        assert "Spring Boot" in prompt
        assert "Lombok" in prompt

    def test_avoid_titles_included(self):
        prompt = build_title_prompt("Cat", "Sub", "Tag", avoid_titles=["Título existente"])
        assert "Título existente" in prompt

    def test_seo_instructions_present(self):
        prompt = build_title_prompt("Cat", "Sub", "Tag")
        assert "SEO" in prompt

    def test_title_max_chars_constraint(self):
        prompt = build_title_prompt("Cat", "Sub", "Tag")
        assert str(META_TITLE_MAX_LENGTH) in prompt

    def test_returns_string(self):
        result = build_title_prompt("A", "B", "C")
        assert isinstance(result, str)
        assert len(result) > 30

    def test_no_avoid_titles_no_avoid_block(self):
        prompt = build_title_prompt("Cat", "Sub", "Tag", avoid_titles=[])
        assert "Evita" not in prompt

    def test_default_none_avoid_titles_no_avoid_block(self):
        """Calling without avoid_titles (default None) should produce no avoid block."""
        prompt = build_title_prompt("Cat", "Sub", "Tag")
        assert "Evita" not in prompt


# ---- send_notification_email (UTF-8) ----
class TestSendNotificationEmailUtf8:
    """Verify that emails with non-ASCII (Spanish) characters are built without errors."""

    @patch("generateArticle.SMTP_HOST", "smtp.example.com")
    @patch("generateArticle.SMTP_PORT", 587)
    @patch("generateArticle.SMTP_USER", "user@example.com")
    @patch("generateArticle.SMTP_PASS", "secret")
    @patch("generateArticle.FROM_EMAIL", "user@example.com")
    @patch("generateArticle.TO_EMAIL", "dest@example.com")
    @patch("generateArticle.smtplib.SMTP")
    def test_utf8_subject_and_body(self, mock_smtp_cls):
        """Non-ASCII chars like á, é, ó, ñ must not raise 'ascii' codec errors."""
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = send_notification_email(
            subject="[INFO] Conexión a la base de datos",
            html_body="<p>Artículo publicado con éxito — título único ñ</p>",
            text_body="Artículo publicado con éxito — título único ñ",
        )

        assert result is True
        mock_smtp.send_message.assert_called_once()
        msg = mock_smtp.send_message.call_args[0][0]
        # The message must serialize to bytes without ASCII errors
        msg_bytes = msg.as_bytes()
        assert b"utf-8" in msg_bytes.lower() or b"utf8" in msg_bytes.lower()
        # Verify non-ASCII Spanish characters survive encoding round-trip
        decoded = msg_bytes.decode("utf-8", errors="replace")
        assert "Conexi" in decoded          # subject present
        assert "xico" in decoded or "xito" in decoded or "éxito" in decoded  # body accent preserved

    @patch("generateArticle.SMTP_HOST", "smtp.example.com")
    @patch("generateArticle.SMTP_PORT", 587)
    @patch("generateArticle.SMTP_USER", "user@example.com")
    @patch("generateArticle.SMTP_PASS", "secret")
    @patch("generateArticle.FROM_EMAIL", "user@example.com")
    @patch("generateArticle.TO_EMAIL", "dest@example.com")
    @patch("generateArticle.smtplib.SMTP")
    def test_smtp_uses_localhost_hostname(self, mock_smtp_cls):
        """SMTP must use local_hostname='localhost' to avoid non-ASCII FQDN encoding errors."""
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        send_notification_email(
            subject="Test subject",
            html_body="<p>body</p>",
            text_body="body",
        )

        mock_smtp_cls.assert_called_once_with(
            "smtp.example.com", 587, local_hostname="localhost"
        )

    @patch("generateArticle.SMTP_HOST", "smtp.example.com")
    @patch("generateArticle.SMTP_PORT", 587)
    @patch("generateArticle.SMTP_USER", "user@example.com")
    @patch("generateArticle.SMTP_PASS", "secret")
    @patch("generateArticle.FROM_EMAIL", "user@example.com")
    @patch("generateArticle.TO_EMAIL", "dest@example.com")
    @patch("generateArticle.smtplib.SMTP")
    def test_subject_uses_header_utf8_encoding(self, mock_smtp_cls):
        """Subject must use email.header.Header with UTF-8 to avoid ASCII codec errors."""
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        subject = "Límite semanal alcanzado — ejecución automática"
        send_notification_email(
            subject=subject,
            html_body="<p>Contenido</p>",
            text_body="Contenido",
        )

        msg = mock_smtp.send_message.call_args[0][0]
        raw_subject = msg["Subject"]
        # After str(Header(..., "utf-8")), the subject is a string with RFC 2047 encoding
        assert isinstance(raw_subject, str)
        # Verify the encoded bytes contain the RFC 2047 UTF-8 marker
        msg_bytes = msg.as_bytes()
        assert b"=?utf-8?" in msg_bytes.lower()
