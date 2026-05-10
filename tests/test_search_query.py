from hyper3.search_query import FieldBoost, SearchFilter, SearchQuery, build_query, parse_query


class TestSearchQuery:
    def test_validate_valid(self):
        q = SearchQuery(text="test", top_k=10)
        assert q.validate() == []

    def test_validate_invalid_top_k(self):
        q = SearchQuery(top_k=0)
        errors = q.validate()
        assert any("top_k" in e for e in errors)

    def test_validate_invalid_offset(self):
        q = SearchQuery(offset=-1)
        errors = q.validate()
        assert any("offset" in e for e in errors)

    def test_validate_negative_boost(self):
        q = SearchQuery(boosts=[FieldBoost(field="x", factor=-1.0)])
        errors = q.validate()
        assert any("boost" in e for e in errors)

    def test_validate_negative_min_score(self):
        q = SearchQuery(min_score=-0.1)
        errors = q.validate()
        assert any("min_score" in e for e in errors)


class TestParseQuery:
    def test_plain_text(self):
        q = parse_query("wireless headphones")
        assert q.text == "wireless headphones"
        assert q.filters == []

    def test_single_filter(self):
        q = parse_query("noise cancelling category:electronics")
        assert q.text == "noise cancelling"
        assert len(q.filters) == 1
        assert q.filters[0].field == "category"
        assert q.filters[0].value == "electronics"

    def test_range_filter(self):
        q = parse_query("price:50..200")
        assert len(q.filters) == 1
        assert q.filters[0].min_value == 50.0
        assert q.filters[0].max_value == 200.0

    def test_multi_value_filter(self):
        q = parse_query("brand:Dell,Lenovo")
        assert len(q.filters) == 1
        assert q.filters[0].values == ["Dell", "Lenovo"]

    def test_negated_filter(self):
        q = parse_query("-type:discontinued")
        assert len(q.filters) == 1
        assert q.filters[0].field == "type"
        assert q.filters[0].negated is True

    def test_boost(self):
        q = parse_query("^brand:2.0")
        assert len(q.boosts) == 1
        assert q.boosts[0].field == "brand"
        assert q.boosts[0].factor == 2.0

    def test_empty_query(self):
        q = parse_query("")
        assert q.text == ""
        assert q.filters == []

    def test_complex_query(self):
        q = parse_query("bluetooth headphones category:electronics price:20..200 brand:Sony,Bose -condition:used ^rating:1.5")
        assert "bluetooth headphones" in q.text
        assert len(q.filters) == 4
        assert len(q.boosts) == 1


class TestBuildQuery:
    def test_build_with_filters(self):
        q = build_query(text="test", filters={"type": "movie"})
        assert q.text == "test"
        assert len(q.filters) == 1
        assert q.filters[0].field == "type"

    def test_build_with_boosts(self):
        q = build_query(boosts={"brand": 2.0})
        assert len(q.boosts) == 1
        assert q.boosts[0].factor == 2.0

    def test_build_defaults(self):
        q = build_query()
        assert q.text == ""
        assert q.top_k == 10
        assert q.strategy == "auto"
