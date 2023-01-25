# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2023  Tim Lauridsen


import os

from typing import Callable
from pathlib import Path

from gi.repository import Gtk, Gio, Adw

from yumex.backend.presenter import YumexPresenter
from yumex.backend.flatpak import FlatpakPackage
from yumex.constants import ROOTDIR
from yumex.utils import RunJob, log
from yumex.ui.flatpak_installer import YumexFlatpakInstaller
from yumex.utils.enums import FlatpakLocation, FlatpakType, Page


@Gtk.Template(resource_path=f"{ROOTDIR}/ui/flatpak_view.ui")
class YumexFlatpakView(Gtk.ListView):
    __gtype_name__ = "YumexFlatpakView"

    selection = Gtk.Template.Child()

    def __init__(self, presenter: YumexPresenter, **kwargs) -> None:
        super().__init__(**kwargs)
        self.presenter: YumexPresenter = presenter
        self.icons_paths = self.get_icon_paths()
        self.reset()

    def reset(self) -> None:
        """Create a new store and populate with flatpak fron the backend"""
        self.store = Gio.ListStore.new(FlatpakPackage)
        self.presenter.reset_flatpak_backend()
        for elem in self.backend.get_installed(location=FlatpakLocation.BOTH):
            if elem.type == FlatpakType.APP:  # show only apps
                self.store.append(elem)
        self.store.sort(lambda a, b: a.name > b.name)
        self.selection.set_model(self.store)
        self.selection.set_selected(0)
        self.refresh_need_attention()

    @property
    def backend(self):
        return self.presenter.flatpak_backend

    def refresh_need_attention(self):
        self.presenter.set_needs_attention(
            Page.FLATPAKS, self.backend.number_of_updates()
        )

    def get_icon_paths(self) -> list[str]:
        """list of possible icon location for installed flatpaks"""
        return [f"{path}/icons/" for path in os.environ["XDG_DATA_DIRS"].split(":")]

    def find_icon(self, pkg: FlatpakPackage) -> str | None:
        """find icon file for an installed flatpak"""
        for path in self.icons_paths:
            if files := list(Path(f"{path}").rglob(f"{pkg.id}.*")):
                return files[0].as_posix()
        return None

    def update_all(self) -> None:
        """update all flatpaks with pending updates"""

        self.do_transaction(self.backend.do_update_all)

    def update(self, pkg) -> None:
        """update a flatpak"""

        self.do_transaction(self.backend.do_update, pkg)

    def install(self, *args) -> None:
        """install a new flatpak"""

        self.presenter.select_page(Page.FLATPAKS)
        # TODO: make and sync edition of the flatpak installer, to make code more readable
        flatpak_installer = YumexFlatpakInstaller(
            self.presenter.get_main_window(), self.backend
        )
        remotes = Gtk.StringList.new()
        for remote in self.backend.get_remotes(location=FlatpakLocation.USER):
            remotes.append(remote)
        flatpak_installer.remote.set_model(remotes)
        flatpak_installer.show()
        fp_id = flatpak_installer.current_id.get_title()
        if fp_id:
            remote = flatpak_installer.remote.get_selected_item().get_string()
            location = flatpak_installer.location.get_selected_item().get_string()
            ref = self.backend.find_ref(remote, fp_id)
            if ref:
                if flatpak_installer.confirm:
                    self.do_transaction(self.backend.do_install, ref, remote, location)
                    self.presenter.show_message(
                        _(f"{fp_id} is now installed"), timeout=2
                    )

            else:
                self.presenter.show_message(f"{fp_id} is not found om {remote}")

    def remove(self, pkg=None) -> None:
        """remove an flatpak"""

        selected = [pkg] if pkg else [self.selection.get_selected_item()]
        self.do_transaction(self.backend.do_remove, selected)
        self.presenter.show_message(_(f"{selected[0].id} is now removed"), timeout=2)

    def do_transaction(self, method: Callable, *args) -> None:
        """Excute the transaction in two runs

        The first get the refs in the transaction and show a confirmation dialog
        The second exceute the transaction

        They run async in a thread and callbacks is called after each run

        The provided callback will be called, with the state of second run
        """
        log(">> Start do_transaction")
        with RunJob(method, *args, execute=False) as job:
            refs = job.start()
        if refs:
            confirm = self.presenter.confirm_flatpak_transaction(refs)
            if confirm:
                # Second run
                with RunJob(method, *args, execute=True) as job:
                    job.start()
        self.presenter.progress.hide()
        self.reset()
        log("<< End do_transaction")

    @Gtk.Template.Callback()
    def on_row_setup(self, widget, item) -> None:
        """Setup row widgets"""
        row = YumexFlatpakRow(self)
        item.set_child(row)

    @Gtk.Template.Callback()
    def on_row_bind(self, widget, item) -> None:
        """bind row data to row widgets"""
        row = item.get_child()
        pkg: FlatpakPackage = item.get_item()
        row.pkg = pkg
        if icon_file := self.find_icon(pkg):
            row.icon.set_from_file(icon_file)
        row.user.set_label(pkg.location)
        row.origin.set_label(pkg.origin)
        row.update.set_visible(pkg.is_update)
        row.set_title(f"{pkg.name} - {pkg.version}")
        row.set_subtitle(pkg.summary)


@Gtk.Template(resource_path=f"{ROOTDIR}/ui/flatpak_row.ui")
class YumexFlatpakRow(Adw.ActionRow):
    """Row widget to show a flatpak"""

    __gtype_name__ = "YumexFlatpakRow"

    icon = Gtk.Template.Child()
    user = Gtk.Template.Child()
    update = Gtk.Template.Child()
    origin = Gtk.Template.Child()

    def __init__(self, view, **kwargs) -> None:
        super().__init__(**kwargs)
        self.view: YumexFlatpakView = view
        self.pkg: FlatpakPackage = None

    @Gtk.Template.Callback()
    def on_delete_clicked(self, widget) -> None:
        self.view.remove(pkg=self.pkg)

    @Gtk.Template.Callback()
    def on_update_clicked(self, widget) -> None:
        self.view.update(self.pkg)
