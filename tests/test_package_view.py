from unittest.mock import MagicMock
import sys
import pytest
import gi

from yumex.utils.enums import PackageFilter, SearchField, SortType, InfoType


gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk
from .mock import TemplateUIFromFile, test_package
import yumex.utils


def translate(text):
    return text


# add a dummy _() method to global namespace as fake translation function
sys.modules["builtins"].__dict__["_"] = translate


def mock_presenter():
    """Mock the presenter"""
    mock = MagicMock()
    mock.get_packages_by_filter.return_value = [test_package()]
    mock.search.return_value = [test_package()]
    mock.get_packages.side_effect = lambda x: x
    return mock


def mock_win():
    """mock the main window"""
    mock = MagicMock()
    mock.package_settings.get_sort_attr.return_value = SortType.NAME
    mock.package_settings.get_info_type.return_value = InfoType.DESCRIPTION
    return mock


def mock_queueview():
    """mock the queueview"""
    mock = MagicMock()
    mock.find_by_nevra.side_effect = lambda x: None
    return mock


def run_sync(func, callback, *args, **kwargs):
    res = func(*args, **kwargs)
    return callback(res)


@pytest.fixture
def view(monkeypatch, mocker):
    """create a progress object"""
    # used the Special Gtk.Template wrapper
    monkeypatch.setattr(Gtk, "Template", TemplateUIFromFile)
    monkeypatch.setattr(yumex.utils, "RunAsync", run_sync)

    from yumex.ui.pachage_view import YumexPackageView

    presenter = mock_presenter()
    win = mock_win()
    queue_view = mock_queueview()
    view = YumexPackageView(win=win, presenter=presenter, qview=queue_view)
    return view


def test_add_packages_to_store(view):
    """should add the package to the view storage"""
    pkgs = [test_package()]
    view.add_packages_to_store(pkgs)
    assert len(view.storage) == 1


def test_add_packages_to_store_empty(view):
    """should add the package to the view storage"""
    pkgs = []
    view.add_packages_to_store(pkgs)
    assert len(view.storage) == 0


def test_get_packages(view):
    """should get one package and add it to the view storage"""
    view.get_packages(PackageFilter.INSTALLED)
    assert len(view.storage) == 1


def test_get_packages_empty(view):
    """should get one package and add it to the view storage"""
    view.presenter.get_packages_by_filter.return_value = []
    view.get_packages(PackageFilter.INSTALLED)
    assert len(view.storage) == 0


def test_search(view):
    """should get one package and add it to the view storage"""
    view.search("text", SearchField.NAME)
    assert len(view.storage) == 1


def test_search_empty(view):
    """should get one package and add it to the view storage"""
    view.presenter.search.return_value = []
    view.search("text", SearchField.NAME)
    assert len(view.storage) == 0
