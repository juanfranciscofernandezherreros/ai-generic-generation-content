# -*- coding: utf-8 -*-
import os
import sys
import unittest

# Establecer variables de entorno mínimas antes de importar el módulo
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "testdb")
os.environ.setdefault("CATEGORY_COLL", "categories")
os.environ.setdefault("TAGS_COLL", "tags")
os.environ.setdefault("USERS_COLL", "users")
os.environ.setdefault("ARTICLES_COLL", "articles")
os.environ.setdefault("OPENAIAPIKEY", "sk-test")

from generateArticle import (
    build_generation_prompt,
    slugify,
    normalize_for_similarity,
    similar_ratio,
    is_too_similar,
    str_id,
    as_list,
    tag_name,
    index_tags,
    build_topic_text,
    html_escape,
    _extract_json_block,
    _safe_json_loads,
    build_hierarchy,
    get_related_tags_for_category,
    find_subcats_with_tags,
)


class TestSlugify(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slugify("Hola Mundo"), "hola-mundo")

    def test_accents(self):
        self.assertEqual(slugify("Cómo usar @Data"), "como-usar-data")

    def test_empty(self):
        self.assertEqual(slugify(""), "")


class TestNormalize(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(normalize_for_similarity("¡Hola, Mundo!"), "hola mundo")


class TestSimilarity(unittest.TestCase):
    def test_identical(self):
        self.assertAlmostEqual(similar_ratio("hello", "hello"), 1.0)

    def test_different(self):
        self.assertLess(similar_ratio("hello", "xyz"), 0.5)

    def test_too_similar(self):
        self.assertTrue(is_too_similar("Hola Mundo", ["Hola Mundo"], threshold=0.8))

    def test_not_too_similar(self):
        self.assertFalse(is_too_similar("Hola Mundo", ["Algo diferente"], threshold=0.8))


class TestHelpers(unittest.TestCase):
    def test_str_id_string(self):
        self.assertEqual(str_id("abc"), "abc")

    def test_as_list_none(self):
        self.assertEqual(as_list(None), [])

    def test_as_list_single(self):
        self.assertEqual(as_list("x"), ["x"])

    def test_as_list_list(self):
        self.assertEqual(as_list([1, 2]), [1, 2])

    def test_tag_name_with_name(self):
        self.assertEqual(tag_name({"name": "Lombok"}), "Lombok")

    def test_tag_name_with_tag(self):
        self.assertEqual(tag_name({"tag": "@Data"}), "@Data")

    def test_html_escape(self):
        self.assertEqual(html_escape("<b>&</b>"), "&lt;b&gt;&amp;&lt;/b&gt;")


class TestExtractJson(unittest.TestCase):
    def test_plain_json(self):
        text = '{"title": "Test", "summary": "s", "body": "b"}'
        result = _extract_json_block(text)
        self.assertIn('"title"', result)

    def test_fenced_json(self):
        text = '```json\n{"title": "Test"}\n```'
        result = _extract_json_block(text)
        self.assertIn('"title"', result)

    def test_safe_json_loads(self):
        data = _safe_json_loads('{"a": 1}')
        self.assertEqual(data["a"], 1)


class TestBuildPromptWithoutRelatedTags(unittest.TestCase):
    """Tests que verifican el prompt sin tags relacionados (comportamiento original)."""

    def test_basic_prompt(self):
        prompt = build_generation_prompt("Spring Boot", "Lombok", "@Data")
        self.assertIn("@Data", prompt)
        self.assertIn("Spring Boot", prompt)
        self.assertIn("Lombok", prompt)

    def test_prompt_avoid_titles(self):
        prompt = build_generation_prompt("Cat", "Sub", "Tag", avoid_titles=["Título A"])
        self.assertIn("Título A", prompt)

    def test_prompt_no_related_block_when_empty(self):
        prompt = build_generation_prompt("Cat", "Sub", "Tag")
        self.assertNotIn("Otros tags relacionados", prompt)

    def test_prompt_no_related_block_when_none(self):
        prompt = build_generation_prompt("Cat", "Sub", "Tag", related_tags=None)
        self.assertNotIn("Otros tags relacionados", prompt)

    def test_prompt_no_related_block_when_empty_list(self):
        prompt = build_generation_prompt("Cat", "Sub", "Tag", related_tags=[])
        self.assertNotIn("Otros tags relacionados", prompt)


class TestBuildPromptWithRelatedTags(unittest.TestCase):
    """Tests que verifican la nueva funcionalidad de tags relacionados."""

    def test_related_tags_appear_in_prompt(self):
        related = ["@Builder", "@Getter", "@Setter"]
        prompt = build_generation_prompt("Spring Boot", "Lombok", "@Data", related_tags=related)
        self.assertIn("Otros tags relacionados", prompt)
        self.assertIn("@Builder", prompt)
        self.assertIn("@Getter", prompt)
        self.assertIn("@Setter", prompt)

    def test_related_tags_with_focus_instruction(self):
        related = ["@Builder"]
        prompt = build_generation_prompt("Spring Boot", "Lombok", "@Data", related_tags=related)
        self.assertIn("foco principal debe ser el tema indicado", prompt)

    def test_related_tags_limited_to_10(self):
        related = [f"Tag{i}" for i in range(20)]
        prompt = build_generation_prompt("Cat", "Sub", "Main", related_tags=related)
        # Only first 10 should appear
        self.assertIn("Tag0", prompt)
        self.assertIn("Tag9", prompt)
        self.assertNotIn("Tag10", prompt)

    def test_related_tags_with_avoid_titles(self):
        prompt = build_generation_prompt(
            "Cat", "Sub", "Main",
            avoid_titles=["Título X"],
            related_tags=["TagA", "TagB"]
        )
        self.assertIn("Título X", prompt)
        self.assertIn("TagA", prompt)
        self.assertIn("TagB", prompt)
        self.assertIn("Otros tags relacionados", prompt)

    def test_single_related_tag(self):
        prompt = build_generation_prompt("Cat", "Sub", "Main", related_tags=["OnlyOne"])
        self.assertIn("OnlyOne", prompt)
        self.assertIn("Otros tags relacionados", prompt)

    def test_main_tag_still_primary_focus(self):
        prompt = build_generation_prompt("Spring Boot", "Lombok", "@Data", related_tags=["@Builder"])
        # The main tag should appear in the primary topic line
        self.assertIn('El tema principal es "@Data"', prompt)


class TestBuildTopicText(unittest.TestCase):
    def test_with_tag(self):
        tag = {"name": "@Data"}
        self.assertEqual(build_topic_text(None, None, tag), "@Data")

    def test_without_tag_with_subcat(self):
        subcat = {"name": "Lombok"}
        self.assertEqual(build_topic_text(None, subcat, None), "Lombok")

    def test_without_tag_without_subcat(self):
        parent = {"name": "Spring Boot"}
        self.assertEqual(build_topic_text(parent, None, None), "Spring Boot")

    def test_all_none(self):
        self.assertEqual(build_topic_text(None, None, None), "General")


class TestIndexTags(unittest.TestCase):
    def test_basic_indexing(self):
        tags = [{"_id": "id1", "name": "Tag1"}, {"_id": "id2", "name": "Tag2"}]
        by_id, by_name = index_tags(tags)
        self.assertIn("id1", by_id)
        self.assertIn("Tag1", by_name)


class TestBuildHierarchy(unittest.TestCase):
    def test_parent_child(self):
        cats = [
            {"_id": "p1", "name": "Parent"},
            {"_id": "c1", "name": "Child", "parent": "p1"},
        ]
        by_id, by_parent = build_hierarchy(cats)
        self.assertIn("p1", by_id)
        self.assertIn("c1", by_id)
        self.assertIn("p1", by_parent)


class TestGetRelatedTagsForCategory(unittest.TestCase):
    def test_tags_by_category_id(self):
        cat = {"_id": "cat1", "name": "Lombok"}
        tags = [
            {"_id": "t1", "name": "@Data", "categoryId": "cat1"},
            {"_id": "t2", "name": "@Builder", "categoryId": "cat1"},
            {"_id": "t3", "name": "JPA", "categoryId": "cat2"},
        ]
        by_id, by_name = index_tags(tags)
        related = get_related_tags_for_category(cat, tags, by_id, by_name)
        names = [t["name"] for t in related]
        self.assertIn("@Data", names)
        self.assertIn("@Builder", names)
        self.assertNotIn("JPA", names)


class TestFindSubcatsWithTags(unittest.TestCase):
    def test_basic(self):
        cats = [
            {"_id": "p1", "name": "Spring Boot"},
            {"_id": "c1", "name": "Lombok", "parent": "p1"},
        ]
        tags = [{"_id": "t1", "name": "@Data", "categoryId": "c1"}]
        by_id, by_parent = build_hierarchy(cats)
        tags_by_id, tags_by_name = index_tags(tags)
        result = find_subcats_with_tags(cats, by_parent, tags, tags_by_id, tags_by_name)
        self.assertTrue(len(result) > 0)
        parent_id, subcat, rel_tags = result[0]
        self.assertEqual(parent_id, "p1")
        self.assertEqual(subcat["name"], "Lombok")
        self.assertEqual(len(rel_tags), 1)


if __name__ == "__main__":
    unittest.main()
