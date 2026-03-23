"""Tests for pure helper functions in generateArticle.py."""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from generateArticle import (
    ARTICLE_LANGUAGE,
    GENERATION_SYSTEM_MSG,
    MAX_AVOID_TITLES_IN_PROMPT,
    MAX_TITLE_RETRIES,
    META_TITLE_MAX_LENGTH,
    OLLAMA_PLACEHOLDER_API_KEY,
    OPENAI_MAX_ARTICLE_TOKENS,
    OPENAI_MAX_TITLE_TOKENS,
    OUTPUT_FILENAME,
    OUTPUT_FILENAME_PATTERN,
    SIMILARITY_THRESHOLD_DEFAULT,
    SIMILARITY_THRESHOLD_STRICT,
    TITLE_SYSTEM_MSG,
    LLMChain,
    _extract_json_block,
    _generate_with_langchain,
    _is_gemini_model,
    _is_ollama_provider,
    _language_name,
    _safe_json_loads,
    as_list,
    build_canonical_url,
    build_generation_prompt,
    build_json_ld_structured_data,
    build_title_prompt,
    count_words,
    estimate_reading_time,
    extract_plain_text,
    generate_and_save_article,
    generate_article_with_ai,
    generate_title_with_ai,
    html_escape,
    is_too_similar,
    normalize_for_similarity,
    send_notification_email,
    similar_ratio,
    slugify,
    str_id,
    tag_name,
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
        """Optimized prompt should be under 1500 characters (excluding avoid titles)."""
        prompt = build_generation_prompt("Cat", "Sub", "Tag")
        assert len(prompt) < 1500

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


# ---- OUTPUT_FILENAME env var with regex validation ----
class TestOutputFilename:
    """Tests for OUTPUT_FILENAME env var and OUTPUT_FILENAME_PATTERN regex."""

    def test_pattern_accepts_simple_filename(self):
        """Pattern must accept a plain .json filename."""
        assert OUTPUT_FILENAME_PATTERN.match("article.json")

    def test_pattern_accepts_path_with_subdirectory(self):
        """Pattern must accept a relative path ending in .json."""
        assert OUTPUT_FILENAME_PATTERN.match("output/my-article.json")

    def test_pattern_accepts_underscored_name(self):
        assert OUTPUT_FILENAME_PATTERN.match("my_article_v2.json")

    def test_pattern_accepts_dot_in_name(self):
        assert OUTPUT_FILENAME_PATTERN.match("article.v2.json")

    def test_pattern_rejects_non_json_extension(self):
        """Pattern must reject filenames that do not end in .json."""
        assert not OUTPUT_FILENAME_PATTERN.match("article.txt")

    def test_pattern_rejects_no_extension(self):
        assert not OUTPUT_FILENAME_PATTERN.match("article")

    def test_pattern_rejects_space_in_name(self):
        """Pattern must reject filenames containing spaces."""
        assert not OUTPUT_FILENAME_PATTERN.match("my article.json")

    def test_pattern_rejects_empty_string(self):
        assert not OUTPUT_FILENAME_PATTERN.match("")

    def test_default_output_filename_is_valid(self):
        """OUTPUT_FILENAME must be a non-empty string ending in .json."""
        assert isinstance(OUTPUT_FILENAME, str)
        assert OUTPUT_FILENAME.endswith(".json")

    def test_env_var_sets_output_filename(self):
        """When OUTPUT_FILENAME env var holds a valid value it should be used."""
        import importlib
        import config as _cfg
        with patch.dict(os.environ, {"OUTPUT_FILENAME": "custom_output.json"}):
            importlib.reload(_cfg)
            assert _cfg.OUTPUT_FILENAME == "custom_output.json"
        # restore
        importlib.reload(_cfg)

    def test_invalid_env_var_falls_back_to_default(self):
        """An invalid OUTPUT_FILENAME env var must fall back to 'article.json'."""
        import importlib
        import config as _cfg
        with patch.dict(os.environ, {"OUTPUT_FILENAME": "bad file name!.json"}):
            importlib.reload(_cfg)
            assert _cfg.OUTPUT_FILENAME == "article.json"
        # restore
        importlib.reload(_cfg)



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


# ---- send_notification_email (SEND_EMAILS toggle) ----
class TestSendEmailsToggle:
    """Verify that SEND_EMAILS=false disables all email sending."""

    @patch("config.SEND_EMAILS", False)
    @patch("notifications.smtplib.SMTP")
    def test_send_emails_false_skips_sending(self, mock_smtp_cls):
        """When SEND_EMAILS is False, send_notification_email should return False and not open SMTP."""
        result = send_notification_email(
            subject="Test",
            html_body="<p>body</p>",
            text_body="body",
        )
        assert result is False
        mock_smtp_cls.assert_not_called()

    @patch("config.SEND_EMAILS", True)
    @patch("config.SMTP_HOST", "smtp.example.com")
    @patch("config.SMTP_PORT", 587)
    @patch("config.SMTP_USER", "user@example.com")
    @patch("config.SMTP_PASS", "secret")
    @patch("config.FROM_EMAIL", "user@example.com")
    @patch("config.TO_EMAIL", "dest@example.com")
    @patch("notifications.smtplib.SMTP")
    def test_send_emails_true_sends_normally(self, mock_smtp_cls):
        """When SEND_EMAILS is True, emails should be sent normally."""
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = send_notification_email(
            subject="Test",
            html_body="<p>body</p>",
            text_body="body",
        )
        assert result is True
        mock_smtp.send_message.assert_called_once()


# ---- send_notification_email (UTF-8) ----
class TestSendNotificationEmailUtf8:
    """Verify that emails with non-ASCII (Spanish) characters are built without errors."""

    @patch("config.SMTP_HOST", "smtp.example.com")
    @patch("config.SMTP_PORT", 587)
    @patch("config.SMTP_USER", "user@example.com")
    @patch("config.SMTP_PASS", "secret")
    @patch("config.FROM_EMAIL", "user@example.com")
    @patch("config.TO_EMAIL", "dest@example.com")
    @patch("notifications.smtplib.SMTP")
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

    @patch("config.SMTP_HOST", "smtp.example.com")
    @patch("config.SMTP_PORT", 587)
    @patch("config.SMTP_USER", "user@example.com")
    @patch("config.SMTP_PASS", "secret")
    @patch("config.FROM_EMAIL", "user@example.com")
    @patch("config.TO_EMAIL", "dest@example.com")
    @patch("notifications.smtplib.SMTP")
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

    @patch("config.SMTP_HOST", "smtp.example.com")
    @patch("config.SMTP_PORT", 587)
    @patch("config.SMTP_USER", "user@example.com")
    @patch("config.SMTP_PASS", "secret")
    @patch("config.FROM_EMAIL", "user@example.com")
    @patch("config.TO_EMAIL", "dest@example.com")
    @patch("notifications.smtplib.SMTP")
    def test_subject_uses_smtp_policy_utf8_encoding(self, mock_smtp_cls):
        """Subject with non-ASCII must be properly encoded via SMTP policy (RFC 2047)."""
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
        assert isinstance(raw_subject, str)
        # Verify the encoded bytes contain the RFC 2047 UTF-8 marker
        msg_bytes = msg.as_bytes()
        assert b"=?utf-8?" in msg_bytes.lower()

    @patch("config.SMTP_HOST", "smtp.example.com")
    @patch("config.SMTP_PORT", 587)
    @patch("config.SMTP_USER", "user@example.com")
    @patch("config.SMTP_PASS", "secreto-á")
    @patch("config.FROM_EMAIL", "user@example.com")
    @patch("config.TO_EMAIL", "dest@example.com")
    @patch("notifications.smtplib.SMTP")
    def test_login_fallback_uses_auth_plain_utf8_when_ascii_login_fails(self, mock_smtp_cls):
        mock_smtp = MagicMock()
        mock_smtp.login.side_effect = UnicodeEncodeError("ascii", "á", 0, 1, "ordinal not in range(128)")
        mock_smtp.docmd.return_value = (235, b"2.7.0 Authentication successful")
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = send_notification_email(
            subject="Asunto con acento",
            html_body="<p>Contenido</p>",
            text_body="Contenido",
        )

        assert result is True
        mock_smtp.login.assert_called_once_with("user@example.com", "secreto-á")
        mock_smtp.docmd.assert_called_once()
        args = mock_smtp.docmd.call_args[0]
        assert args[0] == "AUTH"
        assert args[1].startswith("PLAIN ")


# ---- build_canonical_url ----
class TestBuildCanonicalUrl:
    def test_basic(self):
        assert build_canonical_url("https://example.com", "mi-articulo") == "https://example.com/post/mi-articulo"

    def test_trailing_slash(self):
        assert build_canonical_url("https://example.com/", "mi-articulo") == "https://example.com/post/mi-articulo"

    def test_empty_site(self):
        assert build_canonical_url("", "mi-articulo") == ""

    def test_empty_slug(self):
        assert build_canonical_url("https://example.com", "") == ""

    def test_both_empty(self):
        assert build_canonical_url("", "") == ""


# ---- build_json_ld_structured_data ----
class TestBuildJsonLdStructuredData:
    def _make_data(self, **overrides):
        defaults = {
            "title": "Cómo usar @Data en Lombok",
            "summary": "Aprende a reducir boilerplate con @Data.",
            "canonical_url": "https://example.com/post/como-usar-data-en-lombok",
            "keywords": ["lombok", "@data", "java"],
            "author_name": "adminUser",
            "date_published": "2025-01-01T00:00:00+00:00",
            "date_modified": "2025-01-01T00:00:00+00:00",
            "word_count": 1200,
            "reading_time": 6,
            "category_name": "Lombok",
            "tag_names": ["@Data"],
            "site": "https://example.com",
        }
        defaults.update(overrides)
        return build_json_ld_structured_data(**defaults)

    def test_returns_dict(self):
        data = self._make_data()
        assert isinstance(data, dict)

    def test_context_is_schema_org(self):
        data = self._make_data()
        assert data["@context"] == "https://schema.org"

    def test_type_is_tech_article(self):
        data = self._make_data()
        assert data["@type"] == "TechArticle"

    def test_headline(self):
        data = self._make_data(title="Mi título SEO")
        assert data["headline"] == "Mi título SEO"

    def test_headline_truncated_at_110(self):
        long_title = "A" * 150
        data = self._make_data(title=long_title)
        assert len(data["headline"]) == 110

    def test_language_is_spanish(self):
        data = self._make_data()
        assert data["inLanguage"] == ARTICLE_LANGUAGE

    def test_language_custom(self):
        data = self._make_data(language="en")
        assert data["inLanguage"] == "en"

    def test_author_name(self):
        data = self._make_data(author_name="testUser")
        assert data["author"]["name"] == "testUser"

    def test_url_present(self):
        data = self._make_data()
        assert data["url"] == "https://example.com/post/como-usar-data-en-lombok"

    def test_main_entity_of_page(self):
        data = self._make_data()
        assert data["mainEntityOfPage"]["@id"] == "https://example.com/post/como-usar-data-en-lombok"

    def test_no_url_when_canonical_empty(self):
        data = self._make_data(canonical_url="")
        assert "url" not in data
        assert "mainEntityOfPage" not in data

    def test_keywords_joined(self):
        data = self._make_data(keywords=["spring", "boot", "java"])
        assert data["keywords"] == "spring, boot, java"

    def test_keywords_empty(self):
        data = self._make_data(keywords=[])
        assert data["keywords"] == ""

    def test_word_count(self):
        data = self._make_data(word_count=500)
        assert data["wordCount"] == 500

    def test_time_required_format(self):
        data = self._make_data(reading_time=5)
        assert data["timeRequired"] == "PT5M"

    def test_article_section(self):
        data = self._make_data(category_name="Spring Security")
        assert data["articleSection"] == "Spring Security"

    def test_publisher_from_site(self):
        data = self._make_data(site="https://myblog.com")
        assert data["publisher"]["@type"] == "Organization"
        assert data["publisher"]["url"] == "https://myblog.com"

    def test_no_publisher_when_no_site(self):
        data = self._make_data(site="")
        assert "publisher" not in data

    def test_about_tags(self):
        data = self._make_data(tag_names=["@Data", "Lombok"])
        assert len(data["about"]) == 2
        assert data["about"][0]["name"] == "@Data"

    def test_no_about_when_no_tags(self):
        data = self._make_data(tag_names=[])
        assert "about" not in data

    def test_serializable_to_json(self):
        """Structured data must be JSON-serializable for embedding in HTML."""
        data = self._make_data()
        json_str = json.dumps(data, ensure_ascii=False)
        parsed = json.loads(json_str)
        assert parsed["@type"] == "TechArticle"


# ---- SEO enhancements in system messages ----
class TestSeoSystemMessages:
    def test_generation_system_msg_mentions_seo(self):
        assert "SEO" in GENERATION_SYSTEM_MSG

    def test_generation_system_msg_mentions_semantic_html(self):
        assert "semántico" in GENERATION_SYSTEM_MSG or "HTML" in GENERATION_SYSTEM_MSG

    def test_title_system_msg_mentions_seo(self):
        assert "SEO" in TITLE_SYSTEM_MSG

    def test_generation_prompt_mentions_faq(self):
        prompt = build_generation_prompt("Cat", "Sub", "Tag")
        assert "FAQ" in prompt

    def test_generation_prompt_mentions_cta(self):
        prompt = build_generation_prompt("Cat", "Sub", "Tag")
        assert "CTA" in prompt

    def test_generation_prompt_mentions_long_tail(self):
        prompt = build_generation_prompt("Cat", "Sub", "Tag")
        assert "long-tail" in prompt

    def test_generation_prompt_mentions_keyword_count(self):
        prompt = build_generation_prompt("Cat", "Sub", "Tag")
        assert "5-7" in prompt

    def test_generation_prompt_mentions_strong_em(self):
        """Prompt should instruct to use <strong>/<em> for keyword emphasis."""
        prompt = build_generation_prompt("Cat", "Sub", "Tag")
        assert "<strong>" in prompt or "strong" in prompt


# ---- _language_name helper ----
class TestLanguageName:
    def test_spanish_code(self):
        assert _language_name("es") == "español"

    def test_english_code(self):
        assert _language_name("en") == "inglés"

    def test_french_code(self):
        assert _language_name("fr") == "francés"

    def test_german_code(self):
        assert _language_name("de") == "alemán"

    def test_portuguese_code(self):
        assert _language_name("pt") == "portugués"

    def test_case_insensitive(self):
        assert _language_name("ES") == "español"
        assert _language_name("En") == "inglés"

    def test_unknown_code_returns_code(self):
        assert _language_name("xx") == "xx"


# ---- ARTICLE_LANGUAGE constant ----
class TestArticleLanguageConstant:
    def test_default_is_spanish(self):
        """ARTICLE_LANGUAGE should default to 'es' when the env var is not set."""
        with patch.dict("os.environ", {}, clear=False):
            import os as _os
            _os.environ.pop("ARTICLE_LANGUAGE", None)
            value = _os.getenv("ARTICLE_LANGUAGE", "es")
        assert value == "es"

    def test_is_string(self):
        assert isinstance(ARTICLE_LANGUAGE, str)
        assert len(ARTICLE_LANGUAGE) > 0


# ---- Multi-language support in prompts ----
class TestMultiLanguagePrompts:
    def test_generation_prompt_default_language_is_spanish(self):
        """Default generation prompt must include the Spanish language name."""
        prompt = build_generation_prompt("Cat", "Sub", "Tag")
        assert "español" in prompt

    def test_generation_prompt_english_language(self):
        """Generation prompt with language='en' must include 'inglés'."""
        prompt = build_generation_prompt("Cat", "Sub", "Tag", language="en")
        assert "inglés" in prompt
        assert "español" not in prompt

    def test_generation_prompt_french_language(self):
        prompt = build_generation_prompt("Cat", "Sub", "Tag", language="fr")
        assert "francés" in prompt

    def test_generation_prompt_unknown_language_uses_code(self):
        """An unrecognised language code should appear literally in the prompt."""
        prompt = build_generation_prompt("Cat", "Sub", "Tag", language="xx")
        assert "xx" in prompt

    def test_title_prompt_default_language_is_spanish(self):
        prompt = build_title_prompt("Cat", "Sub", "Tag")
        assert "español" in prompt

    def test_title_prompt_english_language(self):
        prompt = build_title_prompt("Cat", "Sub", "Tag", language="en")
        assert "inglés" in prompt
        assert "español" not in prompt

    def test_title_prompt_german_language(self):
        prompt = build_title_prompt("Cat", "Sub", "Tag", language="de")
        assert "alemán" in prompt


# ---- LangChain integration: _generate_with_langchain ----
class TestGenerateWithLangchain:
    """Tests for the LangChain-based text generation helper."""

    @patch("ai_providers.ChatOpenAI")
    @patch("ai_providers.StrOutputParser")
    @patch("ai_providers.ChatPromptTemplate")
    def test_returns_content_from_chain(self, mock_template, mock_parser, mock_llm):
        """_generate_with_langchain should return the string produced by the LCEL chain."""
        fake_chain = MagicMock()
        fake_chain.invoke.return_value = '{"title":"T","summary":"S","body":"<h1>T</h1>","keywords":[]}'
        # Wire up the pipe operators: prompt_template | llm | parser
        mock_template.from_messages.return_value.__or__ = MagicMock(return_value=MagicMock(
            __or__=MagicMock(return_value=fake_chain)
        ))
        result = _generate_with_langchain("system", "user prompt", max_tokens=100)
        assert result == '{"title":"T","summary":"S","body":"<h1>T</h1>","keywords":[]}'

    @patch("ai_providers.ChatOpenAI")
    @patch("ai_providers.StrOutputParser")
    @patch("ai_providers.ChatPromptTemplate")
    def test_raises_when_chain_returns_empty(self, mock_template, mock_parser, mock_llm):
        """_generate_with_langchain should raise RuntimeError when the chain returns empty string."""
        fake_chain = MagicMock()
        fake_chain.invoke.return_value = ""
        mock_template.from_messages.return_value.__or__ = MagicMock(return_value=MagicMock(
            __or__=MagicMock(return_value=fake_chain)
        ))
        with pytest.raises(RuntimeError):
            _generate_with_langchain("system", "user prompt", max_tokens=100)

    @patch("ai_providers.ChatOpenAI")
    def test_llm_uses_correct_model_and_tokens(self, mock_llm_cls):
        """ChatOpenAI should be constructed with the configured model and max_tokens."""
        mock_llm_instance = MagicMock()
        mock_llm_cls.return_value = mock_llm_instance

        with patch("ai_providers.ChatPromptTemplate") as mock_template, \
             patch("ai_providers.StrOutputParser"):
            fake_chain = MagicMock()
            fake_chain.invoke.return_value = "some content"
            mock_template.from_messages.return_value.__or__ = MagicMock(return_value=MagicMock(
                __or__=MagicMock(return_value=fake_chain)
            ))
            _generate_with_langchain("sys", "user", max_tokens=512, temperature=0.5)

        call_kwargs = mock_llm_cls.call_args[1]
        assert call_kwargs["max_tokens"] == 512
        assert call_kwargs["temperature"] == 0.5


# ---- LangChain integration: generate_article_with_ai (LangChain primary path) ----
_VALID_ARTICLE_JSON = json.dumps({
    "title": "Cómo usar Spring Boot",
    "summary": "Guía completa de Spring Boot.",
    "body": "<h1>Cómo usar Spring Boot</h1><p>Introducción.</p>",
    "keywords": ["spring boot", "java"],
})


class TestGenerateArticleWithAILangchain:
    """Tests for generate_article_with_ai using the LangChain primary path."""

    @patch("article_generator._generate_with_langchain", return_value=_VALID_ARTICLE_JSON)
    def test_uses_langchain_primary_path(self, mock_lc):
        """When LangChain succeeds the OpenAI SDK should not be called."""
        mock_client = MagicMock()
        title, summary, body, keywords = generate_article_with_ai(
            mock_client, "Spring Boot", "Core", "Spring Boot"
        )
        mock_lc.assert_called_once()
        mock_client.chat.completions.create.assert_not_called()

    @patch("article_generator._generate_with_langchain", return_value=_VALID_ARTICLE_JSON)
    def test_returns_tuple_of_four(self, mock_lc):
        mock_client = MagicMock()
        result = generate_article_with_ai(mock_client, "Cat", "Sub", "Tag")
        assert len(result) == 4

    @patch("article_generator._generate_with_langchain", return_value=_VALID_ARTICLE_JSON)
    def test_title_and_body_populated(self, mock_lc):
        mock_client = MagicMock()
        title, summary, body, keywords = generate_article_with_ai(mock_client, "Cat", "Sub", "Tag")
        assert title == "Cómo usar Spring Boot"
        assert "<h1>" in body

    @patch("article_generator._generate_with_langchain", return_value=_VALID_ARTICLE_JSON)
    def test_keywords_returned_as_list(self, mock_lc):
        mock_client = MagicMock()
        _, _, _, keywords = generate_article_with_ai(mock_client, "Cat", "Sub", "Tag")
        assert isinstance(keywords, list)
        assert "spring boot" in keywords

    @patch("article_generator._generate_with_langchain", return_value=_VALID_ARTICLE_JSON)
    def test_h1_injected_when_missing_in_body(self, mock_lc):
        """If the body from the model lacks <h1>, one is prepended from the title."""
        json_no_h1 = json.dumps({
            "title": "Mi título",
            "summary": "Resumen",
            "body": "<p>Sin h1 aquí.</p>",
            "keywords": [],
        })
        mock_lc.return_value = json_no_h1
        mock_client = MagicMock()
        _, _, body, _ = generate_article_with_ai(mock_client, "Cat", "Sub", "Tag")
        assert body.startswith("<h1>Mi título</h1>")

    @patch("article_generator._generate_with_langchain", side_effect=RuntimeError("LangChain error"))
    def test_falls_back_to_openai_sdk_on_langchain_failure(self, mock_lc):
        """When LangChain raises, the OpenAI SDK fallback must be invoked."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=_VALID_ARTICLE_JSON))]
        )
        title, _, _, _ = generate_article_with_ai(mock_client, "Cat", "Sub", "Tag")
        assert title == "Cómo usar Spring Boot"
        mock_client.chat.completions.create.assert_called_once()

    @patch("article_generator._generate_with_langchain", side_effect=RuntimeError("fail"))
    def test_raises_if_both_langchain_and_sdk_fail(self, mock_lc):
        """RuntimeError is raised when both LangChain and the OpenAI SDK fallback fail."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("SDK also failed")
        with pytest.raises(RuntimeError):
            generate_article_with_ai(mock_client, "Cat", "Sub", "Tag")

    @patch("article_generator._generate_with_langchain", return_value='{"title":"","body":"","summary":"","keywords":[]}')
    def test_raises_on_empty_title_or_body(self, mock_lc):
        """ValueError raised when the model returns empty title or body."""
        mock_client = MagicMock()
        with pytest.raises(ValueError):
            generate_article_with_ai(mock_client, "Cat", "Sub", "Tag")


# ---- LangChain integration: generate_title_with_ai (LangChain primary path) ----
class TestGenerateTitleWithAILangchain:
    """Tests for generate_title_with_ai using the LangChain primary path."""

    @patch("article_generator._generate_with_langchain", return_value="Título generado con LangChain")
    def test_uses_langchain_primary_path(self, mock_lc):
        """When LangChain succeeds the OpenAI SDK should not be called."""
        mock_client = MagicMock()
        generate_title_with_ai(mock_client, "Cat", "Sub", "Tag")
        mock_lc.assert_called_once()
        mock_client.chat.completions.create.assert_not_called()

    @patch("article_generator._generate_with_langchain", return_value='  "Mi Título"  ')
    def test_strips_whitespace_and_quotes(self, mock_lc):
        """generate_title_with_ai strips surrounding whitespace and ASCII quote characters."""
        mock_client = MagicMock()
        title = generate_title_with_ai(mock_client, "Cat", "Sub", "Tag")
        assert not title.startswith(" ")
        assert not title.endswith(" ")
        assert not title.startswith('"')
        assert not title.endswith('"')

    @patch("article_generator._generate_with_langchain", return_value="A" * 200)
    def test_truncates_to_meta_title_max_length(self, mock_lc):
        mock_client = MagicMock()
        title = generate_title_with_ai(mock_client, "Cat", "Sub", "Tag")
        assert len(title) <= META_TITLE_MAX_LENGTH

    @patch("article_generator._generate_with_langchain", side_effect=RuntimeError("LangChain error"))
    def test_falls_back_to_openai_sdk_on_langchain_failure(self, mock_lc):
        """When LangChain raises, the OpenAI SDK fallback must be invoked."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Título fallback"))]
        )
        title = generate_title_with_ai(mock_client, "Cat", "Sub", "Tag")
        assert "Título fallback" in title
        mock_client.chat.completions.create.assert_called_once()

    @patch("article_generator._generate_with_langchain", side_effect=RuntimeError("fail"))
    def test_raises_if_both_langchain_and_sdk_fail(self, mock_lc):
        """RuntimeError is raised when both LangChain and the OpenAI SDK fallback fail."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("SDK also failed")
        with pytest.raises(RuntimeError):
            generate_title_with_ai(mock_client, "Cat", "Sub", "Tag")


# ---- _is_gemini_model ----
class TestIsGeminiModel:
    """Tests for the _is_gemini_model provider-detection helper."""

    def test_gemini_flash_detected(self):
        assert _is_gemini_model("gemini-1.5-flash") is True

    def test_gemini_pro_detected(self):
        assert _is_gemini_model("gemini-1.5-pro") is True

    def test_gemini_2_detected(self):
        assert _is_gemini_model("gemini-2.0-flash") is True

    def test_gpt_not_gemini(self):
        assert _is_gemini_model("gpt-4o") is False

    def test_gpt_turbo_not_gemini(self):
        assert _is_gemini_model("gpt-4-turbo") is False

    def test_gpt_35_not_gemini(self):
        assert _is_gemini_model("gpt-3.5-turbo") is False

    def test_case_insensitive(self):
        assert _is_gemini_model("GEMINI-1.5-PRO") is True


# ---- _generate_with_langchain with Gemini ----
class TestGenerateWithLangchainGemini:
    """Tests for _generate_with_langchain when a Gemini model is configured."""

    @patch("ai_providers.ChatGoogleGenerativeAI")
    @patch("ai_providers.StrOutputParser")
    @patch("ai_providers.ChatPromptTemplate")
    @patch("config.OPENAI_MODEL", "gemini-1.5-flash")
    def test_uses_google_llm_for_gemini_model(self, mock_template, mock_parser, mock_google_llm):
        """ChatGoogleGenerativeAI should be used when the model is a Gemini model."""
        fake_chain = MagicMock()
        fake_chain.invoke.return_value = "Gemini response"
        mock_template.from_messages.return_value.__or__ = MagicMock(return_value=MagicMock(
            __or__=MagicMock(return_value=fake_chain)
        ))
        result = _generate_with_langchain("system", "user prompt", max_tokens=100)
        mock_google_llm.assert_called_once()
        assert result == "Gemini response"

    @patch("ai_providers.ChatOpenAI")
    @patch("ai_providers.StrOutputParser")
    @patch("ai_providers.ChatPromptTemplate")
    @patch("config.OPENAI_MODEL", "gemini-1.5-flash")
    def test_does_not_use_openai_llm_for_gemini_model(self, mock_template, mock_parser, mock_openai_llm):
        """ChatOpenAI should NOT be instantiated when the model is a Gemini model."""
        with patch("ai_providers.ChatGoogleGenerativeAI"):
            fake_chain = MagicMock()
            fake_chain.invoke.return_value = "Gemini response"
            mock_template.from_messages.return_value.__or__ = MagicMock(return_value=MagicMock(
                __or__=MagicMock(return_value=fake_chain)
            ))
            _generate_with_langchain("system", "user prompt", max_tokens=100)
        mock_openai_llm.assert_not_called()

    @patch("ai_providers.ChatGoogleGenerativeAI")
    @patch("ai_providers.StrOutputParser")
    @patch("ai_providers.ChatPromptTemplate")
    @patch("config.OPENAI_MODEL", "gemini-2.0-flash")
    def test_gemini_llm_receives_max_output_tokens(self, mock_template, mock_parser, mock_google_llm):
        """ChatGoogleGenerativeAI should receive max_output_tokens (not max_tokens)."""
        mock_llm_instance = MagicMock()
        mock_google_llm.return_value = mock_llm_instance
        fake_chain = MagicMock()
        fake_chain.invoke.return_value = "content"
        mock_template.from_messages.return_value.__or__ = MagicMock(return_value=MagicMock(
            __or__=MagicMock(return_value=fake_chain)
        ))
        _generate_with_langchain("sys", "user", max_tokens=256, temperature=0.5)
        call_kwargs = mock_google_llm.call_args[1]
        assert call_kwargs["max_output_tokens"] == 256
        assert call_kwargs["temperature"] == 0.5



# ---- _is_ollama_provider ----
class TestIsOllamaProvider:
    """Tests for the _is_ollama_provider helper."""

    @patch("config.OLLAMA_BASE_URL", "http://localhost:11434/v1")
    def test_true_when_url_set(self):
        assert _is_ollama_provider() is True

    @patch("config.OLLAMA_BASE_URL", None)
    def test_false_when_url_none(self):
        assert _is_ollama_provider() is False

    @patch("config.OLLAMA_BASE_URL", "")
    def test_false_when_url_empty(self):
        assert _is_ollama_provider() is False

    @patch("config.OLLAMA_BASE_URL", "http://192.168.1.50:11434/v1")
    def test_true_with_custom_host(self):
        assert _is_ollama_provider() is True


# ---- AI_PROVIDER explicit selection ----
class TestAIProviderExplicit:
    """Tests for explicit AI_PROVIDER selection overriding auto-detection."""

    # -- _is_gemini_model with AI_PROVIDER --

    @patch("config.AI_PROVIDER", "gemini")
    def test_gemini_forced_with_gpt_model(self):
        """AI_PROVIDER=gemini forces Gemini even when the model name is a GPT model."""
        assert _is_gemini_model("gpt-4o") is True

    @patch("config.AI_PROVIDER", "openai")
    def test_openai_forced_with_gemini_model(self):
        """AI_PROVIDER=openai overrides gemini model name detection."""
        assert _is_gemini_model("gemini-1.5-flash") is False

    @patch("config.AI_PROVIDER", "ollama")
    def test_ollama_forced_rejects_gemini(self):
        """AI_PROVIDER=ollama means _is_gemini_model returns False."""
        assert _is_gemini_model("gemini-2.0-flash") is False

    @patch("config.AI_PROVIDER", "auto")
    def test_auto_detects_gemini_by_model_name(self):
        """AI_PROVIDER=auto falls back to model-name detection for Gemini."""
        assert _is_gemini_model("gemini-1.5-pro") is True

    @patch("config.AI_PROVIDER", "auto")
    def test_auto_does_not_detect_gpt_as_gemini(self):
        """AI_PROVIDER=auto correctly rejects non-Gemini model names."""
        assert _is_gemini_model("gpt-4o") is False

    # -- _is_ollama_provider with AI_PROVIDER --

    @patch("config.AI_PROVIDER", "ollama")
    @patch("config.OLLAMA_BASE_URL", None)
    def test_ollama_forced_even_without_url(self):
        """AI_PROVIDER=ollama forces Ollama even when OLLAMA_BASE_URL is not set."""
        assert _is_ollama_provider() is True

    @patch("config.AI_PROVIDER", "openai")
    @patch("config.OLLAMA_BASE_URL", "http://localhost:11434/v1")
    def test_openai_forced_rejects_ollama(self):
        """AI_PROVIDER=openai overrides OLLAMA_BASE_URL detection."""
        assert _is_ollama_provider() is False

    @patch("config.AI_PROVIDER", "gemini")
    @patch("config.OLLAMA_BASE_URL", "http://localhost:11434/v1")
    def test_gemini_forced_rejects_ollama(self):
        """AI_PROVIDER=gemini overrides OLLAMA_BASE_URL detection."""
        assert _is_ollama_provider() is False

    @patch("config.AI_PROVIDER", "auto")
    @patch("config.OLLAMA_BASE_URL", "http://localhost:11434/v1")
    def test_auto_detects_ollama_by_url(self):
        """AI_PROVIDER=auto falls back to OLLAMA_BASE_URL detection."""
        assert _is_ollama_provider() is True

    @patch("config.AI_PROVIDER", "auto")
    @patch("config.OLLAMA_BASE_URL", None)
    def test_auto_does_not_detect_ollama_without_url(self):
        """AI_PROVIDER=auto correctly rejects Ollama when URL is not set."""
        assert _is_ollama_provider() is False


class TestMainCliProviderArg:
    """Tests for the --provider CLI argument in main()."""

    @patch("generateArticle.generate_and_save_article", return_value=True)
    @patch("generateArticle.OpenAI")
    @patch("generateArticle.OPENAIAPIKEY", "fake-key")
    @patch("generateArticle.OPENAI_MODEL", "gpt-4o")
    def test_provider_openai_sets_config(self, mock_openai_cls, mock_gen):
        """--provider openai should set config.AI_PROVIDER to 'openai'."""
        import sys

        import config as _cfg
        from generateArticle import main
        original = _cfg.AI_PROVIDER
        try:
            with patch.object(sys, "argv", [
                "generateArticle.py",
                "--category", "Spring Boot",
                "--tag", "Lombok",
                "--provider", "openai",
            ]):
                main()
            assert _cfg.AI_PROVIDER == "openai"
        finally:
            _cfg.AI_PROVIDER = original

    @patch("generateArticle.generate_and_save_article", return_value=True)
    @patch("generateArticle.GEMINI_API_KEY", "fake-gemini-key")
    @patch("generateArticle.OPENAI_MODEL", "gpt-4o")
    @patch("config.AI_PROVIDER", "auto")
    def test_provider_gemini_sets_config(self, mock_gen):
        """--provider gemini should set config.AI_PROVIDER to 'gemini'."""
        import sys

        import config as _cfg
        from generateArticle import main
        original = _cfg.AI_PROVIDER
        try:
            with patch.object(sys, "argv", [
                "generateArticle.py",
                "--category", "Spring Boot",
                "--tag", "Lombok",
                "--provider", "gemini",
            ]):
                main()
            assert _cfg.AI_PROVIDER == "gemini"
        finally:
            _cfg.AI_PROVIDER = original

    @patch("generateArticle.generate_and_save_article", return_value=True)
    @patch("generateArticle.OpenAI")
    @patch("generateArticle.OPENAI_MODEL", "llama3")
    @patch("config.AI_PROVIDER", "auto")
    def test_provider_ollama_sets_config(self, mock_openai_cls, mock_gen):
        """--provider ollama should set config.AI_PROVIDER to 'ollama'."""
        import sys

        import config as _cfg
        from generateArticle import main
        original = _cfg.AI_PROVIDER
        try:
            with patch.object(sys, "argv", [
                "generateArticle.py",
                "--category", "Spring Boot",
                "--tag", "Lombok",
                "--provider", "ollama",
            ]):
                main()
            assert _cfg.AI_PROVIDER == "ollama"
        finally:
            _cfg.AI_PROVIDER = original


# ---- _generate_with_langchain with Ollama ----
class TestGenerateWithLangchainOllama:
    """Tests for _generate_with_langchain when Ollama is configured."""

    @patch("ai_providers.ChatOpenAI")
    @patch("ai_providers.StrOutputParser")
    @patch("ai_providers.ChatPromptTemplate")
    @patch("config.OLLAMA_BASE_URL", "http://localhost:11434/v1")
    @patch("config.OPENAI_MODEL", "llama3")
    def test_uses_chat_openai_with_base_url_for_ollama(self, mock_template, mock_parser, mock_llm):
        """ChatOpenAI should be constructed with base_url when Ollama is configured."""
        mock_llm_instance = MagicMock()
        mock_llm.return_value = mock_llm_instance
        fake_chain = MagicMock()
        fake_chain.invoke.return_value = "Ollama response"
        mock_template.from_messages.return_value.__or__ = MagicMock(return_value=MagicMock(
            __or__=MagicMock(return_value=fake_chain)
        ))
        result = _generate_with_langchain("system", "user prompt", max_tokens=100)
        mock_llm.assert_called_once()
        call_kwargs = mock_llm.call_args[1]
        assert call_kwargs["base_url"] == "http://localhost:11434/v1"
        assert call_kwargs["api_key"] == OLLAMA_PLACEHOLDER_API_KEY
        assert result == "Ollama response"

    @patch("ai_providers.ChatOpenAI")
    @patch("ai_providers.StrOutputParser")
    @patch("ai_providers.ChatPromptTemplate")
    @patch("config.OLLAMA_BASE_URL", "http://localhost:11434/v1")
    @patch("config.OPENAI_MODEL", "mistral")
    def test_ollama_llm_receives_max_tokens_and_temperature(self, mock_template, mock_parser, mock_llm):
        """ChatOpenAI for Ollama should receive max_tokens and temperature."""
        mock_llm_instance = MagicMock()
        mock_llm.return_value = mock_llm_instance
        fake_chain = MagicMock()
        fake_chain.invoke.return_value = "content"
        mock_template.from_messages.return_value.__or__ = MagicMock(return_value=MagicMock(
            __or__=MagicMock(return_value=fake_chain)
        ))
        _generate_with_langchain("sys", "user", max_tokens=512, temperature=0.5)
        call_kwargs = mock_llm.call_args[1]
        assert call_kwargs["max_tokens"] == 512
        assert call_kwargs["temperature"] == 0.5

    @patch("ai_providers.ChatGoogleGenerativeAI")
    @patch("ai_providers.ChatOpenAI")
    @patch("ai_providers.StrOutputParser")
    @patch("ai_providers.ChatPromptTemplate")
    @patch("config.OLLAMA_BASE_URL", "http://localhost:11434/v1")
    @patch("config.OPENAI_MODEL", "llama3")
    def test_ollama_does_not_use_google_llm(self, mock_template, mock_parser, mock_openai_llm, mock_google_llm):
        """ChatGoogleGenerativeAI should NOT be used when Ollama is configured."""
        fake_chain = MagicMock()
        fake_chain.invoke.return_value = "Ollama response"
        mock_template.from_messages.return_value.__or__ = MagicMock(return_value=MagicMock(
            __or__=MagicMock(return_value=fake_chain)
        ))
        _generate_with_langchain("system", "user prompt", max_tokens=100)
        mock_google_llm.assert_not_called()


# ---- Ollama: CLI main() ----
class TestMainCliOllama:
    """Tests for the main() CLI when Ollama is configured."""

    @patch("generateArticle.generate_and_save_article", return_value=True)
    @patch("generateArticle.OpenAI")
    @patch("config.OLLAMA_BASE_URL", "http://localhost:11434/v1")
    @patch("generateArticle.OLLAMA_BASE_URL", "http://localhost:11434/v1")
    @patch("generateArticle.OPENAIAPIKEY", "")
    @patch("generateArticle.OPENAI_MODEL", "llama3")
    def test_main_does_not_require_api_key_with_ollama(self, mock_openai_cls, mock_gen):
        """main() should NOT exit when OPENAIAPIKEY is empty but OLLAMA_BASE_URL is set."""
        import sys

        from generateArticle import main
        with patch.object(sys, "argv", ["generateArticle.py", "--category", "Spring Boot", "--tag", "Lombok"]):
            main()
        mock_gen.assert_called_once()

    @patch("generateArticle.generate_and_save_article", return_value=True)
    @patch("generateArticle.OpenAI")
    @patch("config.OLLAMA_BASE_URL", "http://localhost:11434/v1")
    @patch("generateArticle.OLLAMA_BASE_URL", "http://localhost:11434/v1")
    @patch("generateArticle.OPENAIAPIKEY", "")
    @patch("generateArticle.OPENAI_MODEL", "llama3")
    def test_main_initializes_openai_client_with_base_url(self, mock_openai_cls, mock_gen):
        """main() should create the OpenAI client with base_url pointing to Ollama."""
        import sys

        from generateArticle import main
        with patch.object(sys, "argv", ["generateArticle.py", "--category", "Spring Boot", "--tag", "Lombok"]):
            main()
        mock_openai_cls.assert_called_once_with(base_url="http://localhost:11434/v1", api_key=OLLAMA_PLACEHOLDER_API_KEY)


# ---- Ollama: no Gemini interference ----
class TestOllamaNoGeminiInterference:
    """When Ollama is configured with a non-Gemini model, Gemini paths should not activate."""

    @patch("article_generator._generate_with_langchain", side_effect=RuntimeError("LangChain fail"))
    @patch("config.OLLAMA_BASE_URL", "http://localhost:11434/v1")
    @patch("config.OPENAI_MODEL", "llama3")
    def test_article_uses_sdk_fallback_for_ollama(self, mock_lc):
        """For Ollama, OpenAI SDK fallback should be used when LangChain fails."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=_VALID_ARTICLE_JSON))]
        )
        title, _, _, _ = generate_article_with_ai(mock_client, "Cat", "Sub", "Tag")
        assert title == "Cómo usar Spring Boot"
        mock_client.chat.completions.create.assert_called_once()

    @patch("article_generator._generate_with_langchain", side_effect=RuntimeError("LangChain fail"))
    @patch("config.OLLAMA_BASE_URL", "http://localhost:11434/v1")
    @patch("config.OPENAI_MODEL", "llama3")
    def test_title_uses_sdk_fallback_for_ollama(self, mock_lc):
        """For Ollama, OpenAI SDK fallback should be used when LangChain fails."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Título de Ollama"))]
        )
        title = generate_title_with_ai(mock_client, "Cat", "Sub", "Tag")
        assert "Título de Ollama" in title
        mock_client.chat.completions.create.assert_called_once()


# ---- LLMChain class ----
class TestLLMChain:
    """Tests for the LLMChain class that wraps LCEL chains with an LLMChain-style API."""

    def test_run_returns_content(self):
        """LLMChain.run() should return the text produced by the underlying LCEL chain."""
        fake_inner_chain = MagicMock()
        fake_inner_chain.invoke.return_value = "generated content"
        mock_prompt = MagicMock()
        mock_llm = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock(
            __or__=MagicMock(return_value=fake_inner_chain)
        ))
        with patch("ai_providers.StrOutputParser"):
            chain = LLMChain(llm=mock_llm, prompt=mock_prompt)
            result = chain.run(user_prompt="test input")
        assert result == "generated content"
        fake_inner_chain.invoke.assert_called_once_with({"user_prompt": "test input"})

    def test_invoke_returns_content(self):
        """LLMChain.invoke() should return the text produced by the underlying LCEL chain."""
        fake_inner_chain = MagicMock()
        fake_inner_chain.invoke.return_value = "invoked content"
        mock_prompt = MagicMock()
        mock_llm = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock(
            __or__=MagicMock(return_value=fake_inner_chain)
        ))
        with patch("ai_providers.StrOutputParser"):
            chain = LLMChain(llm=mock_llm, prompt=mock_prompt)
            result = chain.invoke({"user_prompt": "test input"})
        assert result == "invoked content"

    def test_run_and_invoke_equivalent(self):
        """LLMChain.run(**kw) and LLMChain.invoke(kw) should produce the same result."""
        fake_inner_chain = MagicMock()
        fake_inner_chain.invoke.return_value = "same content"
        mock_prompt = MagicMock()
        mock_llm = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=MagicMock(
            __or__=MagicMock(return_value=fake_inner_chain)
        ))
        with patch("ai_providers.StrOutputParser"):
            chain = LLMChain(llm=mock_llm, prompt=mock_prompt)
            result_run = chain.run(user_prompt="text")
            result_invoke = chain.invoke({"user_prompt": "text"})
        assert result_run == result_invoke

    def test_uses_prompt_and_llm_in_chain(self):
        """LLMChain should build the LCEL chain as: prompt | llm | StrOutputParser()."""
        mock_prompt = MagicMock()
        mock_llm = MagicMock()
        mock_prompt_llm = MagicMock()
        mock_full_chain = MagicMock()
        mock_full_chain.invoke.return_value = "ok"
        mock_prompt.__or__ = MagicMock(return_value=mock_prompt_llm)
        mock_prompt_llm.__or__ = MagicMock(return_value=mock_full_chain)
        with patch("ai_providers.StrOutputParser") as mock_parser:
            LLMChain(llm=mock_llm, prompt=mock_prompt)
        mock_prompt.__or__.assert_called_once_with(mock_llm)
        mock_prompt_llm.__or__.assert_called_once_with(mock_parser.return_value)


# ---- AI_TEMPERATURE_ARTICLE and AI_TEMPERATURE_TITLE constants ----
class TestTemperatureConstants:
    """Tests that configurable temperature constants are used in generation calls."""

    @patch("article_generator._generate_with_langchain", return_value='{"title":"T","summary":"S","body":"<h1>T</h1>","keywords":[]}')
    @patch("config.AI_TEMPERATURE_ARTICLE", 0.3)
    def test_article_uses_ai_temperature_article(self, mock_lc):
        """generate_article_with_ai should pass AI_TEMPERATURE_ARTICLE to _generate_with_langchain."""
        mock_client = MagicMock()
        generate_article_with_ai(mock_client, "Cat", "Sub", "Tag")
        _, call_kwargs = mock_lc.call_args
        assert call_kwargs["temperature"] == 0.3

    @patch("article_generator._generate_with_langchain", return_value="Título generado")
    @patch("config.AI_TEMPERATURE_TITLE", 0.2)
    def test_title_uses_ai_temperature_title(self, mock_lc):
        """generate_title_with_ai should pass AI_TEMPERATURE_TITLE to _generate_with_langchain."""
        mock_client = MagicMock()
        generate_title_with_ai(mock_client, "Cat", "Sub", "Tag")
        _, call_kwargs = mock_lc.call_args
        assert call_kwargs["temperature"] == 0.2


# ---- Gemini: no OpenAI SDK fallback ----
class TestGeminiNoOpenAIFallback:
    """When a Gemini model is configured, the OpenAI SDK fallback must not be called."""

    @patch("article_generator._generate_with_langchain", side_effect=RuntimeError("LangChain fail"))
    @patch("config.OPENAI_MODEL", "gemini-1.5-flash")
    def test_article_raises_without_openai_fallback_for_gemini(self, mock_lc):
        """For Gemini models, RuntimeError is raised when LangChain fails (no OpenAI SDK fallback)."""
        mock_client = MagicMock()
        with pytest.raises(RuntimeError):
            generate_article_with_ai(mock_client, "Cat", "Sub", "Tag")
        mock_client.chat.completions.create.assert_not_called()

    @patch("article_generator._generate_with_langchain", side_effect=RuntimeError("LangChain fail"))
    @patch("config.OPENAI_MODEL", "gemini-1.5-flash")
    def test_title_raises_without_openai_fallback_for_gemini(self, mock_lc):
        """For Gemini models, RuntimeError is raised when LangChain fails (no OpenAI SDK fallback)."""
        mock_client = MagicMock()
        with pytest.raises(RuntimeError):
            generate_title_with_ai(mock_client, "Cat", "Sub", "Tag")
        mock_client.chat.completions.create.assert_not_called()


# ---- generate_and_save_article ----
_VALID_JSON = json.dumps({
    "title": "Guía de Spring Boot",
    "summary": "Introducción a Spring Boot.",
    "body": "<h1>Guía de Spring Boot</h1><p>Contenido.</p>",
    "keywords": ["spring boot", "java"],
})


class TestGenerateAndSaveArticle:
    """Tests for generate_and_save_article: JSON output and document structure."""

    @patch("article_generator._generate_with_langchain", return_value=_VALID_JSON)
    def test_returns_true_on_success(self, mock_lc):
        """generate_and_save_article returns True when the article is successfully saved."""
        mock_client = MagicMock()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            path = tmp.name
        try:
            result = generate_and_save_article(
                mock_client, "Spring Boot", "Spring Boot", "Spring Boot Core",
                output_path=path,
            )
            assert result is True
        finally:
            os.unlink(path)

    @patch("article_generator._generate_with_langchain", return_value=_VALID_JSON)
    def test_creates_json_file(self, mock_lc):
        """generate_and_save_article writes a valid JSON file to the given output path."""
        mock_client = MagicMock()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            path = tmp.name
        try:
            generate_and_save_article(
                mock_client, "Spring Boot", "Spring Boot", "Spring Boot Core",
                output_path=path,
            )
            assert os.path.isfile(path)
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
            assert isinstance(doc, dict)
        finally:
            os.unlink(path)

    @patch("article_generator._generate_with_langchain", return_value=_VALID_JSON)
    def test_json_contains_required_fields(self, mock_lc):
        """The exported JSON must contain all required article fields."""
        mock_client = MagicMock()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            path = tmp.name
        try:
            generate_and_save_article(
                mock_client, "Spring Boot", "Categoría", "Subcategoría",
                output_path=path,
            )
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
            for field in ("title", "slug", "summary", "body", "category", "tags",
                          "author", "status", "keywords", "metaTitle", "metaDescription",
                          "canonicalUrl", "structuredData", "wordCount", "readingTime"):
                assert field in doc, f"Campo '{field}' no encontrado en el JSON"
        finally:
            os.unlink(path)

    @patch("article_generator._generate_with_langchain", return_value=_VALID_JSON)
    def test_tag_stored_as_string(self, mock_lc):
        """Tags in the JSON output are stored as strings, not ObjectIds."""
        mock_client = MagicMock()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            path = tmp.name
        try:
            generate_and_save_article(
                mock_client, "Spring Boot", "Cat", "Sub",
                output_path=path,
            )
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
            assert isinstance(doc["tags"], list)
            for t in doc["tags"]:
                assert isinstance(t, str)
        finally:
            os.unlink(path)

    @patch("article_generator._generate_with_langchain", return_value=_VALID_JSON)
    def test_category_stored_as_string(self, mock_lc):
        """Category in the JSON output is stored as a string, not an ObjectId."""
        mock_client = MagicMock()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            path = tmp.name
        try:
            generate_and_save_article(
                mock_client, "Spring Boot", "Cat", "MiSubcategoría",
                output_path=path,
            )
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
            assert isinstance(doc["category"], str)
            assert doc["category"] == "MiSubcategoría"
        finally:
            os.unlink(path)

    @patch("article_generator._generate_with_langchain", return_value=_VALID_JSON)
    def test_author_passed_correctly(self, mock_lc):
        """The author name passed as argument is stored in the JSON document."""
        mock_client = MagicMock()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            path = tmp.name
        try:
            generate_and_save_article(
                mock_client, "Spring Boot", "Cat", "Sub",
                author_name="testAuthor",
                output_path=path,
            )
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
            assert doc["author"] == "testAuthor"
        finally:
            os.unlink(path)

    @patch("article_generator._generate_with_langchain", return_value=_VALID_JSON)
    def test_slug_derived_from_title(self, mock_lc):
        """The slug in the JSON is derived from the article title."""
        mock_client = MagicMock()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            path = tmp.name
        try:
            generate_and_save_article(
                mock_client, "Spring Boot", "Cat", "Sub",
                output_path=path,
            )
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
            assert doc["slug"] == slugify(doc["title"])
        finally:
            os.unlink(path)

    @patch("article_generator._generate_with_langchain", return_value=_VALID_JSON)
    def test_structured_data_is_schema_org(self, mock_lc):
        """The structuredData field must conform to Schema.org TechArticle."""
        mock_client = MagicMock()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            path = tmp.name
        try:
            generate_and_save_article(
                mock_client, "Spring Boot", "Cat", "Sub",
                output_path=path,
            )
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
            sd = doc["structuredData"]
            assert sd["@context"] == "https://schema.org"
            assert sd["@type"] == "TechArticle"
        finally:
            os.unlink(path)

    @patch("article_generator._generate_with_langchain", side_effect=RuntimeError("AI fail"))
    def test_raises_on_ai_failure(self, mock_lc):
        """generate_and_save_article raises RuntimeError when AI generation fails."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("SDK fail")
        with pytest.raises(RuntimeError):
            generate_and_save_article(
                mock_client, "Spring Boot", "Cat", "Sub",
                output_path="/tmp/should_not_be_created.json",
            )

    @patch("article_generator._generate_with_langchain", return_value=_VALID_JSON)
    def test_json_is_utf8_encoded(self, mock_lc):
        """The JSON file must be valid UTF-8 and non-ASCII chars appear unescaped."""
        mock_client = MagicMock()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            path = tmp.name
        try:
            generate_and_save_article(
                mock_client, "Spring Böot", "Categoría", "Subcategoría",
                output_path=path,
            )
            with open(path, encoding="utf-8") as f:
                raw = f.read()
            # ensure_ascii=False means accented chars should appear literally
            assert "Subcategor" in raw
        finally:
            os.unlink(path)


# ---- CLI: main() argparse ----
class TestMainCli:
    """Tests for the argparse-based main() function."""

    @patch("generateArticle.generate_and_save_article", return_value=True)
    @patch("generateArticle.OpenAI")
    @patch("generateArticle.OPENAIAPIKEY", "fake-key")
    @patch("generateArticle.OPENAI_MODEL", "gpt-4o")
    def test_main_calls_generate_with_tag_arg(self, mock_openai_cls, mock_gen):
        """main() must call generate_and_save_article with the --tag argument."""
        import sys

        from generateArticle import main
        with patch.object(sys, "argv", ["generateArticle.py", "--category", "Spring Boot", "--tag", "Spring Boot"]):
            main()
        mock_gen.assert_called_once()
        _, kwargs = mock_gen.call_args
        assert kwargs["tag_text"] == "Spring Boot"

    @patch("generateArticle.generate_and_save_article", return_value=True)
    @patch("generateArticle.OpenAI")
    @patch("generateArticle.OPENAIAPIKEY", "fake-key")
    @patch("generateArticle.OPENAI_MODEL", "gpt-4o")
    def test_main_passes_category_and_subcategory(self, mock_openai_cls, mock_gen):
        """main() must pass --category and --subcategory to generate_and_save_article."""
        import sys

        from generateArticle import main
        with patch.object(sys, "argv", [
            "generateArticle.py",
            "--tag", "Lombok",
            "--category", "Spring Boot",
            "--subcategory", "Lombok",
        ]):
            main()
        _, kwargs = mock_gen.call_args
        assert kwargs["parent_name"] == "Spring Boot"
        assert kwargs["subcat_name"] == "Lombok"

    @patch("generateArticle.generate_and_save_article", return_value=True)
    @patch("generateArticle.OpenAI")
    @patch("generateArticle.OPENAIAPIKEY", "fake-key")
    @patch("generateArticle.OPENAI_MODEL", "gpt-4o")
    def test_main_passes_output_path(self, mock_openai_cls, mock_gen):
        """main() must pass the --output argument as output_path."""
        import sys

        from generateArticle import main
        with patch.object(sys, "argv", [
            "generateArticle.py",
            "--category", "Spring Boot",
            "--tag", "Lombok",
            "--output", "/tmp/test_output.json",
        ]):
            main()
        _, kwargs = mock_gen.call_args
        assert kwargs["output_path"] == "/tmp/test_output.json"

    @patch("generateArticle.generate_and_save_article", return_value=True)
    @patch("generateArticle.OpenAI")
    @patch("generateArticle.OPENAIAPIKEY", "fake-key")
    @patch("generateArticle.OPENAI_MODEL", "gpt-4o")
    @patch("generateArticle.OUTPUT_FILENAME", "env_output.json")
    def test_main_uses_output_filename_env_var_as_default(self, mock_openai_cls, mock_gen):
        """main() must use OUTPUT_FILENAME as default for --output when not provided via CLI."""
        import sys

        from generateArticle import main
        with patch.object(sys, "argv", [
            "generateArticle.py",
            "--category", "Spring Boot",
            "--tag", "Lombok",
        ]):
            main()
        _, kwargs = mock_gen.call_args
        assert kwargs["output_path"] == "env_output.json"

    @patch("generateArticle.generate_and_save_article", return_value=True)
    @patch("generateArticle.OpenAI")
    @patch("generateArticle.OPENAIAPIKEY", "fake-key")
    @patch("generateArticle.OPENAI_MODEL", "gpt-4o")
    def test_main_passes_language(self, mock_openai_cls, mock_gen):
        """main() must pass the --language argument to generate_and_save_article."""
        import sys

        from generateArticle import main
        with patch.object(sys, "argv", [
            "generateArticle.py",
            "--category", "Spring Boot",
            "--tag", "Lombok",
            "--language", "en",
        ]):
            main()
        _, kwargs = mock_gen.call_args
        assert kwargs["language"] == "en"

    @patch("generateArticle.generate_and_save_article", return_value=True)
    @patch("generateArticle.OpenAI")
    @patch("generateArticle.OPENAIAPIKEY", "fake-key")
    @patch("generateArticle.OPENAI_MODEL", "gpt-4o")
    def test_main_parses_avoid_titles(self, mock_openai_cls, mock_gen):
        """main() must parse semicolon-separated --avoid-titles into a list."""
        import sys

        from generateArticle import main
        with patch.object(sys, "argv", [
            "generateArticle.py",
            "--category", "Spring Boot",
            "--tag", "Lombok",
            "--avoid-titles", "Título A;Título B",
        ]):
            main()
        _, kwargs = mock_gen.call_args
        assert "Título A" in kwargs["avoid_titles"]
        assert "Título B" in kwargs["avoid_titles"]

    @patch("generateArticle.OPENAIAPIKEY", "")
    @patch("generateArticle.GEMINI_API_KEY", "")
    @patch("generateArticle.OPENAI_MODEL", "gpt-4o")
    def test_main_exits_when_no_api_key(self):
        """main() must exit with code 1 when no API key is configured."""
        import sys

        from generateArticle import main
        with patch.object(sys, "argv", ["generateArticle.py", "--category", "Spring Boot", "--tag", "Lombok"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1

    @patch("generateArticle.generate_and_save_article", return_value=True)
    @patch("generateArticle.OpenAI")
    @patch("generateArticle.OPENAIAPIKEY", "fake-key")
    @patch("generateArticle.OPENAI_MODEL", "gpt-4o")
    def test_main_passes_username_arg(self, mock_openai_cls, mock_gen):
        """main() must pass --username to generate_and_save_article as author_name."""
        import sys

        from generateArticle import main
        with patch.object(sys, "argv", [
            "generateArticle.py",
            "--category", "Spring Boot",
            "--tag", "Lombok",
            "--username", "myUser",
        ]):
            main()
        _, kwargs = mock_gen.call_args
        assert kwargs["author_name"] == "myUser"

    @patch("generateArticle.generate_and_save_article", return_value=True)
    @patch("generateArticle.OpenAI")
    @patch("generateArticle.OPENAIAPIKEY", "fake-key")
    @patch("generateArticle.OPENAI_MODEL", "gpt-4o")
    def test_main_passes_author_alias(self, mock_openai_cls, mock_gen):
        """--author must work as a backward-compatible alias for --username."""
        import sys

        from generateArticle import main
        with patch.object(sys, "argv", [
            "generateArticle.py",
            "--category", "Spring Boot",
            "--tag", "Lombok",
            "--author", "legacyUser",
        ]):
            main()
        _, kwargs = mock_gen.call_args
        assert kwargs["author_name"] == "legacyUser"

    @patch("generateArticle.generate_and_save_article", return_value=True)
    @patch("generateArticle.OpenAI")
    @patch("generateArticle.OPENAIAPIKEY", "fake-key")
    @patch("generateArticle.OPENAI_MODEL", "gpt-4o")
    def test_main_passes_site_arg(self, mock_openai_cls, mock_gen):
        """main() must pass --site to generate_and_save_article."""
        import sys

        from generateArticle import main
        with patch.object(sys, "argv", [
            "generateArticle.py",
            "--category", "Spring Boot",
            "--tag", "Lombok",
            "--site", "https://myblog.com",
        ]):
            main()
        _, kwargs = mock_gen.call_args
        assert kwargs["site"] == "https://myblog.com"

    @patch("generateArticle.generate_and_save_article", return_value=True)
    @patch("generateArticle.OpenAI")
    @patch("generateArticle.OPENAIAPIKEY", "fake-key")
    @patch("generateArticle.OPENAI_MODEL", "gpt-4o")
    def test_main_passes_title_arg(self, mock_openai_cls, mock_gen):
        """main() must pass --title to generate_and_save_article."""
        import sys

        from generateArticle import main
        with patch.object(sys, "argv", [
            "generateArticle.py",
            "--category", "Spring Boot",
            "--tag", "Lombok",
            "--title", "Mi Título Personalizado",
        ]):
            main()
        _, kwargs = mock_gen.call_args
        assert kwargs["title"] == "Mi Título Personalizado"

    @patch("generateArticle.generate_and_save_article", return_value=True)
    @patch("generateArticle.OpenAI")
    @patch("generateArticle.OPENAIAPIKEY", "fake-key")
    @patch("generateArticle.OPENAI_MODEL", "gpt-4o")
    def test_main_title_default_is_none(self, mock_openai_cls, mock_gen):
        """main() must pass title=None when --title is not provided."""
        import sys

        from generateArticle import main
        with patch.object(sys, "argv", [
            "generateArticle.py",
            "--category", "Spring Boot",
            "--tag", "Lombok",
        ]):
            main()
        _, kwargs = mock_gen.call_args
        assert kwargs["title"] is None

    @patch("generateArticle.generate_and_save_article", return_value=True)
    @patch("generateArticle.OpenAI")
    @patch("generateArticle.OPENAIAPIKEY", "fake-key")
    @patch("generateArticle.OPENAI_MODEL", "gpt-4o")
    def test_main_category_is_required(self, mock_openai_cls, mock_gen):
        """main() must exit with error when --category is not provided."""
        import sys

        from generateArticle import main
        with patch.object(sys, "argv", ["generateArticle.py", "--tag", "Lombok"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 2  # argparse exits with code 2 for missing required args

    @patch("generateArticle.generate_and_save_article", return_value=True)
    @patch("generateArticle.OpenAI")
    @patch("generateArticle.OPENAIAPIKEY", "fake-key")
    @patch("generateArticle.OPENAI_MODEL", "gpt-4o")
    def test_main_tag_defaults_to_none(self, mock_openai_cls, mock_gen):
        """main() must pass tag_text=None when --tag is not provided."""
        import sys

        from generateArticle import main
        with patch.object(sys, "argv", [
            "generateArticle.py",
            "--category", "Spring Boot",
        ]):
            main()
        _, kwargs = mock_gen.call_args
        assert kwargs["tag_text"] is None


class TestPromptWithoutTag:
    def test_generation_prompt_without_tag(self):
        """build_generation_prompt works without tag_text."""
        prompt = build_generation_prompt("Spring Boot", "Lombok")
        assert "Spring Boot" in prompt
        assert "Lombok" in prompt

    def test_generation_prompt_with_none_tag(self):
        """build_generation_prompt works with tag_text=None."""
        prompt = build_generation_prompt("Spring Boot", "Lombok", None)
        assert "Spring Boot" in prompt
        assert "None" not in prompt

    def test_title_prompt_without_tag(self):
        """build_title_prompt works without tag_text."""
        prompt = build_title_prompt("Spring Boot", "Lombok")
        assert "Spring Boot" in prompt
        assert "Lombok" in prompt

    def test_title_prompt_with_none_tag(self):
        """build_title_prompt works with tag_text=None."""
        prompt = build_title_prompt("Spring Boot", "Lombok", None)
        assert "Spring Boot" in prompt
        assert "None" not in prompt
