from pathlib import Path

from app.plugins.loader import load_plugin

PLUGINS = Path(__file__).resolve().parents[2] / "plugins"


def test_batteries_plugin_loads_with_iso_iec_15459():
    """Art. 77.3 obliga a ISO/IEC 15459 para baterías."""
    plugin = load_plugin(PLUGINS / "batteries.yaml")
    assert plugin.regulation == "EU 2023/1542"
    assert plugin.identifier_scheme == "iso_iec_15459"


def test_batteries_has_at_least_25_required_fields():
    """F1-03 acceptance: ≥25 campos obligatorios cubriendo Secciones 1+2+3."""
    plugin = load_plugin(PLUGINS / "batteries.yaml")
    required = [f for f in plugin.fields if f.required]
    assert len(required) >= 25, f"Sólo {len(required)} campos obligatorios, F1-03 exige ≥25"


def test_batteries_covers_annex_xiii_section_1():
    """Anexo XIII Sección 1 (público): ≥19 campos."""
    plugin = load_plugin(PLUGINS / "batteries.yaml")
    public = [f for f in plugin.fields if f.access_level == "public"]
    assert (
        len(public) >= 19
    ), f"Sólo {len(public)} campos public; Anexo XIII Sección 1 tiene 19 ítems agregados"


def test_batteries_covers_annex_xiii_section_2():
    """Anexo XIII Sección 2 (interés legítimo): ≥4 campos."""
    plugin = load_plugin(PLUGINS / "batteries.yaml")
    legitimate = [f for f in plugin.fields if f.access_level == "legitimate_interest"]
    assert (
        len(legitimate) >= 4
    ), f"Sólo {len(legitimate)} campos legitimate_interest; Anexo XIII Sección 2 tiene 4 ítems"


def test_batteries_covers_annex_xiii_section_3():
    """Anexo XIII Sección 3 (autoridades): ≥1 campo."""
    plugin = load_plugin(PLUGINS / "batteries.yaml")
    authorities = [f for f in plugin.fields if f.access_level == "authorities_only"]
    assert len(authorities) >= 1, "Anexo XIII Sección 3 exige resultados de informes de ensayo"


def test_every_field_cites_reg_2023_1542_with_article_or_annex():
    """Todas las citas son al Reglamento de baterías, con Art./Annex concreto."""
    plugin = load_plugin(PLUGINS / "batteries.yaml")
    for f in plugin.fields:
        assert (
            "2023/1542" in f.citation.regulation
        ), f"Campo {f.id} cita reglamento incorrecto: {f.citation.regulation}"
        article = f.citation.article
        assert any(
            token in article for token in ("Art.", "Anexo", "Annex")
        ), f"Campo {f.id} cita sin Art./Anexo: {article}"


def test_batteries_uses_amperes_hours_for_rated_capacity():
    """Anexo XIII (1g) literal: 'capacidad asignada (en amperios-hora)'. NO kWh."""
    plugin = load_plugin(PLUGINS / "batteries.yaml")
    has_ah_capacity = any(f.id == "rated_capacity_ah" for f in plugin.fields)
    has_kwh_capacity = any(
        "kwh" in f.id.lower() and "capacity" in f.id.lower() for f in plugin.fields
    )
    assert has_ah_capacity, "Anexo XIII (1g) exige capacidad en Ah; campo rated_capacity_ah ausente"
    assert not has_kwh_capacity, "Anexo XIII (1g) exige Ah, no kWh — el plan original tenía esto incorrectamente como capacity_kwh"


def test_batteries_eu_declaration_url_cites_art_18():
    """Anexo XIII (1r) → Art. 18, NO Art. 19 (Art. 19 sería marcado CE, no DPP)."""
    plugin = load_plugin(PLUGINS / "batteries.yaml")
    decl = next((f for f in plugin.fields if f.id == "eu_declaration_of_conformity_url"), None)
    assert decl is not None, "Falta campo eu_declaration_of_conformity_url (Anexo XIII 1r)"
    assert (
        "Art. 18" in decl.citation.article
    ), f"La Declaración UE de conformidad cita Art. 18, no {decl.citation.article}"


def test_batteries_requires_typical_documents():
    """datasheet + ce_declaration son mandatorios incondicionalmente; certificate/lca/sds dependen del BOM (when)."""
    plugin = load_plugin(PLUGINS / "batteries.yaml")
    doc_types = {d.type for d in plugin.required_documents}
    assert {"datasheet", "ce_declaration"}.issubset(doc_types)


def test_batteries_required_documents_cover_all_canonical_types():
    """El plugin debe modelar los 5 tipos canónicos de documento del Recolector — los condicionales protegen del exceso."""
    plugin = load_plugin(PLUGINS / "batteries.yaml")
    doc_types = {d.type for d in plugin.required_documents}
    assert doc_types == {"datasheet", "ce_declaration", "certificate", "lca", "sds"}, (
        f"required_documents debería cubrir los 5 tipos canónicos. Falta: "
        f"{ {'datasheet', 'ce_declaration', 'certificate', 'lca', 'sds'} - doc_types}; "
        f"sobra: {doc_types - {'datasheet', 'ce_declaration', 'certificate', 'lca', 'sds'}}"
    )


def test_batteries_cross_validations_locked_by_id():
    """Los IDs de las cross_validations son contrato: si se renombran, el Verificador (paso 6) se rompe."""
    plugin = load_plugin(PLUGINS / "batteries.yaml")
    expected = {
        "voltage_consistency",
        "idle_temp_consistency",
        "lifetime_min_cycles",
        "capacity_exhaustion_required_for_ev",
    }
    actual = {cv.id for cv in plugin.cross_validations}
    assert expected.issubset(actual), (
        f"Faltan cross_validations canónicas: {expected - actual}. "
        f"Si se renombran o eliminan, hay que actualizar también este test y la lógica del Verificador."
    )
