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
# Copyright (C) 2024 Tim Lauridsen

from gi.repository import Gtk, Adw, Gio

from yumex.constants import APP_ID, ROOTDIR
from yumex.utils import log
from yumex.utils.enums import FlatpakLocation


@Gtk.Template(resource_path=f"{ROOTDIR}/ui/preferences.ui")
class YumexPreferences(Adw.PreferencesWindow):
    __gtype_name__ = "YumexPreferences"

    fp_remote: Adw.ComboRow = Gtk.Template.Child()
    fp_location: Adw.ComboRow = Gtk.Template.Child()

    repo_group = Gtk.Template.Child()

    def __init__(self, presenter, **kwargs):
        super().__init__(**kwargs)
        self.presenter = presenter
        self.settings = Gio.Settings(APP_ID)
        self.connect("unrealize", self.save_settings)
        self.setup_repo()
        self.setup_flatpak()

    def setup_repo(self):
        # get repositories and add them
        repos = self.presenter.get_repositories()
        for id, name, enabled, prio in repos:
            repo_widget = YumexRepository()
            repo_widget.set_title(id)
            repo_widget.set_subtitle(f"{name}( {prio})")
            repo_widget.enabled.set_state(enabled)
            self.repo_group.add(repo_widget)

    def setup_flatpak(self):
        location = FlatpakLocation(self.settings.get_string("fp-location").lower())
        remote = self.settings.get_string("fp-remote")
        log(f" settings : {location=}")
        log(f" settings : {remote=}")
        self.set_selected_location(location)
        self.update_remote(location)

    def get_current_location(self) -> FlatpakLocation:
        return FlatpakLocation(self.fp_location.get_selected_item().get_string())

    def get_current_remote(self) -> FlatpakLocation:
        selected = self.fp_remote.get_selected_item()
        if selected:
            remote = selected.get_string()
        else:
            remote = None
        return remote

    def set_selected_location(self, current_location):
        for ndx, location in enumerate(self.fp_location.get_model()):
            if location.get_string() == current_location:
                self.fp_location.set_selected(ndx)
                break

    def save_settings(self, *args):
        location = self.get_current_location()
        self.settings.set_string("fp-location", location.value)
        remote = self.get_current_remote()
        if remote:
            self.settings.set_string("fp-remote", remote)
        return location, remote

    def update_remote(self, current_location) -> str | None:
        remotes = self.get_remotes(current_location)
        self.fp_remote.set_model(remotes)
        current_remote = self.settings.get_string("fp-remote")
        selected = None
        if not len(remotes):  # not remotes for current location
            self.fp_remote.set_sensitive(False)
            return selected

        self.fp_remote.set_sensitive(True)
        for ndx, remote in enumerate(self.fp_remote.get_model()):
            if remote.get_string() == current_remote:
                self.fp_remote.set_selected(ndx)
                selected = current_remote
                break
        if not selected:  # if current_remote not found, select first remote
            self.fp_remote.set_selected(0)
            selected = self.fp_remote.get_selected_item().get_string()
        return selected

    def get_remotes(self, location: FlatpakLocation) -> list:
        remotes = self.presenter.flatpak_backend.get_remotes(location=location)
        model = Gtk.StringList.new()
        if not remotes:
            log(f"pref: No remotes found location {location}")
            return model
        for remote in remotes:
            model.append(remote)
        return model

    @Gtk.Template.Callback()
    def on_location_selected(self, widget, data):
        """capture the Notify for the selected property is changed"""
        location = FlatpakLocation(self.fp_location.get_selected_item().get_string())
        self.update_remote(location)


@Gtk.Template(resource_path=f"{ROOTDIR}/ui/repository.ui")
class YumexRepository(Adw.ActionRow):
    __gtype_name__ = "YumexRepository"

    enabled = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
