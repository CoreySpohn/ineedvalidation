import pytest
from test_nodes import HIER

from ineedvalidation import views


def test_builtin_views_cover_reference_and_status():
    built = views.builtin()
    assert set(built) == {"reference", "status"}
    assert built["reference"].mode == "reference"
    assert built["reference"].show == ()
    assert built["status"].show == ("libraries", "tiers")


def test_a_view_file_loads_with_its_fields():
    view = views.load(HIER / "views" / "branch.yaml")
    assert view.name == "branch"
    assert view.root == "SS-mixer"
    assert view.highlight == ("widgetlib",)
    assert view.title == "Mixer branch"


def test_resolve_prefers_a_file_over_a_builtin():
    assert views.resolve("branch", HIER / "views").root == "SS-mixer"
    assert views.resolve("status", HIER / "views").root is None


def test_an_unknown_view_name_raises():
    with pytest.raises(KeyError, match="no view named nope"):
        views.resolve("nope", HIER / "views")


def test_override_path_is_found_only_when_the_file_exists(tmp_path):
    assert views.override_path(HIER / "views", "branch") is None
    (tmp_path / "branch.d2").write_text("")
    assert views.override_path(tmp_path, "branch").name == "branch.d2"
    assert views.override_path(None, "branch") is None
