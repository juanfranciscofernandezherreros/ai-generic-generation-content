# -*- coding: utf-8 -*-
"""Tests for pure helper functions in generateArticle.py."""

import json
import os
import tempfile
from unittest.mock import patch, MagicMock
import pytest

from generateArticle import (
    as_list,
    build_canonical_url,
    build_generation_prompt,
    build_json_ld_structured_data,
    build_title_prompt,
    count_words,
    estimate_reading_time,
    extract_plain_text,
    generate_and_save_article,
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
    _language_name,
    _generate_with_langchain,
    _is_gemini_model,
    generate_article_with_ai,
    generate_title_with_ai,
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
    ARTICLE_LANGUAGE,
    AI_TEMPERATURE_ARTICLE,
    AI_TEMPERATURE_TITLE,
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

    @patch("generateArticle.ChatOpenAI")
    @patch("generateArticle.StrOutputParser")
    @patch("generateArticle.ChatPromptTemplate")
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

    @patch("generateArticle.ChatOpenAI")
    @patch("generateArticle.StrOutputParser")
    @patch("generateArticle.ChatPromptTemplate")
    def test_raises_when_chain_returns_empty(self, mock_template, mock_parser, mock_llm):
        """_generate_with_langchain should raise RuntimeError when the chain returns empty string."""
        fake_chain = MagicMock()
        fake_chain.invoke.return_value = ""
        mock_template.from_messages.return_value.__or__ = MagicMock(return_value=MagicMock(
            __or__=MagicMock(return_value=fake_chain)
        ))
        with pytest.raises(RuntimeError):
            _generate_with_langchain("system", "user prompt", max_tokens=100)

    @patch("generateArticle.ChatOpenAI")
    def test_llm_uses_correct_model_and_tokens(self, mock_llm_cls):
        """ChatOpenAI should be constructed with the configured model and max_tokens."""
        import generateArticle
        mock_llm_instance = MagicMock()
        mock_llm_cls.return_value = mock_llm_instance

        with patch("generateArticle.ChatPromptTemplate") as mock_template, \
             patch("generateArticle.StrOutputParser") as mock_parser:
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

    @patch("generateArticle._generate_with_langchain", return_value=_VALID_ARTICLE_JSON)
    def test_uses_langchain_primary_path(self, mock_lc):
        """When LangChain succeeds the OpenAI SDK should not be called."""
        mock_client = MagicMock()
        title, summary, body, keywords = generate_article_with_ai(
            mock_client, "Spring Boot", "Core", "Spring Boot"
        )
        mock_lc.assert_called_once()
        mock_client.chat.completions.create.assert_not_called()

    @patch("generateArticle._generate_with_langchain", return_value=_VALID_ARTICLE_JSON)
    def test_returns_tuple_of_four(self, mock_lc):
        mock_client = MagicMock()
        result = generate_article_with_ai(mock_client, "Cat", "Sub", "Tag")
        assert len(result) == 4

    @patch("generateArticle._generate_with_langchain", return_value=_VALID_ARTICLE_JSON)
    def test_title_and_body_populated(self, mock_lc):
        mock_client = MagicMock()
        title, summary, body, keywords = generate_article_with_ai(mock_client, "Cat", "Sub", "Tag")
        assert title == "Cómo usar Spring Boot"
        assert "<h1>" in body

    @patch("generateArticle._generate_with_langchain", return_value=_VALID_ARTICLE_JSON)
    def test_keywords_returned_as_list(self, mock_lc):
        mock_client = MagicMock()
        _, _, _, keywords = generate_article_with_ai(mock_client, "Cat", "Sub", "Tag")
        assert isinstance(keywords, list)
        assert "spring boot" in keywords

    @patch("generateArticle._generate_with_langchain", return_value=_VALID_ARTICLE_JSON)
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

    @patch("generateArticle._generate_with_langchain", side_effect=RuntimeError("LangChain error"))
    def test_falls_back_to_openai_sdk_on_langchain_failure(self, mock_lc):
        """When LangChain raises, the OpenAI SDK fallback must be invoked."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=_VALID_ARTICLE_JSON))]
        )
        title, _, _, _ = generate_article_with_ai(mock_client, "Cat", "Sub", "Tag")
        assert title == "Cómo usar Spring Boot"
        mock_client.chat.completions.create.assert_called_once()

    @patch("generateArticle._generate_with_langchain", side_effect=RuntimeError("fail"))
    def test_raises_if_both_langchain_and_sdk_fail(self, mock_lc):
        """RuntimeError is raised when both LangChain and the OpenAI SDK fallback fail."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("SDK also failed")
        with pytest.raises(RuntimeError):
            generate_article_with_ai(mock_client, "Cat", "Sub", "Tag")

    @patch("generateArticle._generate_with_langchain", return_value='{"title":"","body":"","summary":"","keywords":[]}')
    def test_raises_on_empty_title_or_body(self, mock_lc):
        """ValueError raised when the model returns empty title or body."""
        mock_client = MagicMock()
        with pytest.raises(ValueError):
            generate_article_with_ai(mock_client, "Cat", "Sub", "Tag")


# ---- LangChain integration: generate_title_with_ai (LangChain primary path) ----
class TestGenerateTitleWithAILangchain:
    """Tests for generate_title_with_ai using the LangChain primary path."""

    @patch("generateArticle._generate_with_langchain", return_value="Título generado con LangChain")
    def test_uses_langchain_primary_path(self, mock_lc):
        """When LangChain succeeds the OpenAI SDK should not be called."""
        mock_client = MagicMock()
        title = generate_title_with_ai(mock_client, "Cat", "Sub", "Tag")
        mock_lc.assert_called_once()
        mock_client.chat.completions.create.assert_not_called()

    @patch("generateArticle._generate_with_langchain", return_value='  "Mi Título"  ')
    def test_strips_whitespace_and_quotes(self, mock_lc):
        """generate_title_with_ai strips surrounding whitespace and ASCII quote characters."""
        mock_client = MagicMock()
        title = generate_title_with_ai(mock_client, "Cat", "Sub", "Tag")
        assert not title.startswith(" ")
        assert not title.endswith(" ")
        assert not title.startswith('"')
        assert not title.endswith('"')

    @patch("generateArticle._generate_with_langchain", return_value="A" * 200)
    def test_truncates_to_meta_title_max_length(self, mock_lc):
        mock_client = MagicMock()
        title = generate_title_with_ai(mock_client, "Cat", "Sub", "Tag")
        assert len(title) <= META_TITLE_MAX_LENGTH

    @patch("generateArticle._generate_with_langchain", side_effect=RuntimeError("LangChain error"))
    def test_falls_back_to_openai_sdk_on_langchain_failure(self, mock_lc):
        """When LangChain raises, the OpenAI SDK fallback must be invoked."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Título fallback"))]
        )
        title = generate_title_with_ai(mock_client, "Cat", "Sub", "Tag")
        assert "Título fallback" in title
        mock_client.chat.completions.create.assert_called_once()

    @patch("generateArticle._generate_with_langchain", side_effect=RuntimeError("fail"))
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

    @patch("generateArticle.ChatGoogleGenerativeAI")
    @patch("generateArticle.StrOutputParser")
    @patch("generateArticle.ChatPromptTemplate")
    @patch("generateArticle.OPENAI_MODEL", "gemini-1.5-flash")
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

    @patch("generateArticle.ChatOpenAI")
    @patch("generateArticle.StrOutputParser")
    @patch("generateArticle.ChatPromptTemplate")
    @patch("generateArticle.OPENAI_MODEL", "gemini-1.5-flash")
    def test_does_not_use_openai_llm_for_gemini_model(self, mock_template, mock_parser, mock_openai_llm):
        """ChatOpenAI should NOT be instantiated when the model is a Gemini model."""
        with patch("generateArticle.ChatGoogleGenerativeAI") as mock_google_llm:
            fake_chain = MagicMock()
            fake_chain.invoke.return_value = "Gemini response"
            mock_template.from_messages.return_value.__or__ = MagicMock(return_value=MagicMock(
                __or__=MagicMock(return_value=fake_chain)
            ))
            _generate_with_langchain("system", "user prompt", max_tokens=100)
        mock_openai_llm.assert_not_called()

    @patch("generateArticle.ChatGoogleGenerativeAI")
    @patch("generateArticle.StrOutputParser")
    @patch("generateArticle.ChatPromptTemplate")
    @patch("generateArticle.OPENAI_MODEL", "gemini-2.0-flash")
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


# ---- AI_TEMPERATURE_ARTICLE and AI_TEMPERATURE_TITLE constants ----
class TestTemperatureConstants:
    """Tests that configurable temperature constants are used in generation calls."""

    @patch("generateArticle._generate_with_langchain", return_value='{"title":"T","summary":"S","body":"<h1>T</h1>","keywords":[]}')
    @patch("generateArticle.AI_TEMPERATURE_ARTICLE", 0.3)
    def test_article_uses_ai_temperature_article(self, mock_lc):
        """generate_article_with_ai should pass AI_TEMPERATURE_ARTICLE to _generate_with_langchain."""
        mock_client = MagicMock()
        generate_article_with_ai(mock_client, "Cat", "Sub", "Tag")
        _, call_kwargs = mock_lc.call_args
        assert call_kwargs["temperature"] == 0.3

    @patch("generateArticle._generate_with_langchain", return_value="Título generado")
    @patch("generateArticle.AI_TEMPERATURE_TITLE", 0.2)
    def test_title_uses_ai_temperature_title(self, mock_lc):
        """generate_title_with_ai should pass AI_TEMPERATURE_TITLE to _generate_with_langchain."""
        mock_client = MagicMock()
        generate_title_with_ai(mock_client, "Cat", "Sub", "Tag")
        _, call_kwargs = mock_lc.call_args
        assert call_kwargs["temperature"] == 0.2


# ---- Gemini: no OpenAI SDK fallback ----
class TestGeminiNoOpenAIFallback:
    """When a Gemini model is configured, the OpenAI SDK fallback must not be called."""

    @patch("generateArticle._generate_with_langchain", side_effect=RuntimeError("LangChain fail"))
    @patch("generateArticle.OPENAI_MODEL", "gemini-1.5-flash")
    def test_article_raises_without_openai_fallback_for_gemini(self, mock_lc):
        """For Gemini models, RuntimeError is raised when LangChain fails (no OpenAI SDK fallback)."""
        mock_client = MagicMock()
        with pytest.raises(RuntimeError):
            generate_article_with_ai(mock_client, "Cat", "Sub", "Tag")
        mock_client.chat.completions.create.assert_not_called()

    @patch("generateArticle._generate_with_langchain", side_effect=RuntimeError("LangChain fail"))
    @patch("generateArticle.OPENAI_MODEL", "gemini-1.5-flash")
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

    @patch("generateArticle._generate_with_langchain", return_value=_VALID_JSON)
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

    @patch("generateArticle._generate_with_langchain", return_value=_VALID_JSON)
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

    @patch("generateArticle._generate_with_langchain", return_value=_VALID_JSON)
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

    @patch("generateArticle._generate_with_langchain", return_value=_VALID_JSON)
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

    @patch("generateArticle._generate_with_langchain", return_value=_VALID_JSON)
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

    @patch("generateArticle._generate_with_langchain", return_value=_VALID_JSON)
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

    @patch("generateArticle._generate_with_langchain", return_value=_VALID_JSON)
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

    @patch("generateArticle._generate_with_langchain", return_value=_VALID_JSON)
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

    @patch("generateArticle._generate_with_langchain", side_effect=RuntimeError("AI fail"))
    def test_raises_on_ai_failure(self, mock_lc):
        """generate_and_save_article raises RuntimeError when AI generation fails."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("SDK fail")
        with pytest.raises(RuntimeError):
            generate_and_save_article(
                mock_client, "Spring Boot", "Cat", "Sub",
                output_path="/tmp/should_not_be_created.json",
            )

    @patch("generateArticle._generate_with_langchain", return_value=_VALID_JSON)
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
        with patch.object(sys, "argv", ["generateArticle.py", "--tag", "Spring Boot"]):
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
    def test_main_passes_language(self, mock_openai_cls, mock_gen):
        """main() must pass the --language argument to generate_and_save_article."""
        import sys
        from generateArticle import main
        with patch.object(sys, "argv", [
            "generateArticle.py",
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
        with patch.object(sys, "argv", ["generateArticle.py", "--tag", "Lombok"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1
