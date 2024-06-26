from unittest.mock import MagicMock, Mock
import pytest
import gi


gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk
from .mock import TemplateUIFromFile


def mock_presenter(remotes: list = None):
    mock = MagicMock()
    return mock


@pytest.fixture
def view(monkeypatch):
    """create a progress object"""
    # used the Special Gtk.Template wrapper
    monkeypatch.setattr(Gtk, "Template", TemplateUIFromFile)

    from yumex.ui.queue_view import YumexQueueView
    from yumex.ui.package_view import YumexPackageView

    presenter = mock_presenter()
    queue_view = YumexQueueView(presenter=presenter)
    view = YumexPackageView(win=Mock(), presenter=presenter, qview=queue_view)
    return view


def test_setup(view):
    assert True
