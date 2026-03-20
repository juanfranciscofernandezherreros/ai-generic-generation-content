"""Tests for seed_data.py taxonomy definition."""

from seed_data import TAXONOMY


class TestTaxonomyStructure:
    """Verifica que la taxonomía definida en seed_data cumpla requisitos básicos."""

    def test_has_three_parent_categories(self):
        assert len(TAXONOMY) == 3

    def test_parent_names(self):
        names = [c["name"] for c in TAXONOMY]
        assert "Spring Boot" in names
        assert "Data & Persistencia" in names
        assert "Inteligencia Artificial" in names

    def test_each_parent_has_subcategories(self):
        for parent in TAXONOMY:
            assert "subcategories" in parent, f"{parent['name']} carece de 'subcategories'"
            assert len(parent["subcategories"]) > 0, f"{parent['name']} no tiene subcategorías"

    def test_each_subcategory_has_name_and_tags(self):
        for parent in TAXONOMY:
            for sub in parent["subcategories"]:
                assert "name" in sub, f"Subcategoría sin nombre en {parent['name']}"
                assert "tags" in sub, f"Subcategoría '{sub['name']}' sin tags"
                assert len(sub["tags"]) >= 8, (
                    f"Subcategoría '{sub['name']}' tiene menos de 8 tags"
                )

    def test_all_tag_names_are_strings(self):
        for parent in TAXONOMY:
            for sub in parent["subcategories"]:
                for tag in sub["tags"]:
                    assert isinstance(tag, str) and tag.strip(), (
                        f"Tag vacío o no string en '{sub['name']}'"
                    )

    def test_no_duplicate_tag_names_within_subcategory(self):
        for parent in TAXONOMY:
            for sub in parent["subcategories"]:
                tags = sub["tags"]
                assert len(tags) == len(set(tags)), (
                    f"Tags duplicados en subcategoría '{sub['name']}'"
                )

    def test_spring_boot_subcategory_names(self):
        sb = next(c for c in TAXONOMY if c["name"] == "Spring Boot")
        sub_names = [s["name"] for s in sb["subcategories"]]
        for expected in ("Spring Boot Core", "Spring Security", "Spring Data JPA",
                         "Spring MVC REST", "Spring Boot Testing", "Lombok"):
            assert expected in sub_names

    def test_data_subcategory_names(self):
        data = next(c for c in TAXONOMY if c["name"] == "Data & Persistencia")
        sub_names = [s["name"] for s in data["subcategories"]]
        for expected in ("JPA e Hibernate", "Bases de Datos SQL",
                         "NoSQL y MongoDB", "Migraciones de Esquema"):
            assert expected in sub_names

    def test_ai_subcategory_names(self):
        ai = next(c for c in TAXONOMY if c["name"] == "Inteligencia Artificial")
        sub_names = [s["name"] for s in ai["subcategories"]]
        for expected in ("Spring AI", "LLMs y Modelos de Lenguaje",
                         "Machine Learning con Java", "Vector Databases y RAG"):
            assert expected in sub_names

    def test_lombok_has_expected_tags(self):
        sb = next(c for c in TAXONOMY if c["name"] == "Spring Boot")
        lombok = next(s for s in sb["subcategories"] if s["name"] == "Lombok")
        for tag in ("@Data", "@Builder", "@Slf4j"):
            assert tag in lombok["tags"]

    def test_spring_ai_subcategory_tags(self):
        ai = next(c for c in TAXONOMY if c["name"] == "Inteligencia Artificial")
        spring_ai = next(s for s in ai["subcategories"] if s["name"] == "Spring AI")
        assert "Spring AI Overview" in spring_ai["tags"]
        assert "ChatClient con Spring AI" in spring_ai["tags"]

    def test_rag_subcategory_tags(self):
        ai = next(c for c in TAXONOMY if c["name"] == "Inteligencia Artificial")
        rag = next(s for s in ai["subcategories"] if s["name"] == "Vector Databases y RAG")
        assert "RAG (Retrieval Augmented Generation)" in rag["tags"]
        assert "Embeddings con Spring AI" in rag["tags"]

    def test_total_tag_count_reasonable(self):
        total = sum(
            len(sub["tags"])
            for parent in TAXONOMY
            for sub in parent["subcategories"]
        )
        # 14 subcategorías × ~10 tags = ~140
        assert total >= 130, f"Total de tags demasiado bajo: {total}"

    def test_each_category_has_description(self):
        for parent in TAXONOMY:
            assert parent.get("description", "").strip(), (
                f"Categoría '{parent['name']}' sin descripción"
            )
        for parent in TAXONOMY:
            for sub in parent["subcategories"]:
                assert sub.get("description", "").strip(), (
                    f"Subcategoría '{sub['name']}' sin descripción"
                )
