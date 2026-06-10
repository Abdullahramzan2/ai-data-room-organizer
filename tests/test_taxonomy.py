from dataroom.config import load_taxonomy, resolve_project_root


def test_taxonomy_has_twenty_categories():
    taxonomy = load_taxonomy()
    categories = taxonomy["categories"]
    assert len(categories) == 20

    folders = [c["folder"] for c in categories]
    assert folders[0] == "00_Admin_and_Index"
    assert folders[-1] == "19_Unclassified_Review_Queue"
    assert all("description" in c for c in categories)
    assert all("folder" in c for c in categories)


def test_taxonomy_file_exists():
    path = resolve_project_root() / "taxonomy" / "real_estate_development.yaml"
    assert path.is_file()
