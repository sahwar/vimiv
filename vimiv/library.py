#!/usr/bin/env python
# encoding: utf-8
""" Library part of self.vimiv """

import os
from subprocess import Popen, PIPE
from gi import require_version
require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk
from vimiv.fileactions import is_image, populate


class Library(object):
    """ Library class for self.vimiv
        includes the treeview with the library and all actions that apply to
        it """

    def __init__(self, vimiv, settings):
        self.vimiv = vimiv
        library = settings["LIBRARY"]

        # Settings
        self.focused = False
        self.dir_pos = {}  # Remembers positions in the library browser
        self.toggled = library["show_library"]
        self.default_width = library["library_width"]
        self.width = self.default_width
        self.expand = library["expand_lib"]
        self.border_width = library["border_width"]
        self.border_color = library["border_color"]
        try:
            self.border_color = Gdk.color_parse(self.border_color)
        except:
            self.border_color = Gdk.color_parse("#000000")
        self.markup = library["markup"]
        self.show_hidden = library["show_hidden"]
        self.desktop_start_dir = library["desktop_start_dir"]

        # Defaults
        self.files = []
        self.treepos = 0
        self.datalist = []
        self.filesize = {}
        self.filelist = []

        # Librarybox
        self.box = Gtk.HBox()
        # Set up the self.grid in which the file info will be positioned
        self.grid = Gtk.Grid()
        self.grid.set_column_homogeneous(True)
        self.grid.set_row_homogeneous(True)
        if self.vimiv.paths or not self.expand:
            self.grid.set_size_request(self.width - self.border_width, 10)
        else:
            self.grid.set_size_request(self.vimiv.winsize[0], 10)
        # A simple border
        if self.border_width:
            border = Gtk.Box()
            border.set_size_request(self.border_width, 0)
            border.modify_bg(Gtk.StateType.NORMAL, self.border_color)
            self.box.pack_end(border, False, False, 0)
        # Entering content
        self.scrollable_treelist = Gtk.ScrolledWindow()
        self.scrollable_treelist.set_vexpand(True)
        self.grid.attach(self.scrollable_treelist, 0, 0, 4, 10)
        # Pack everything
        self.box.pack_start(self.grid, True, True, 0)
        # Call the function to create the treeview
        self.treeview_create()
        self.scrollable_treelist.add(self.treeview)

    def toggle(self):
        """ Toggles the library """
        if self.toggled:
            self.remember_pos(os.path.abspath("."), self.treepos)
            self.box.hide()
            self.vimiv.image.animation_toggled = False  # Now play Gifs
            self.toggled = not self.toggled
            self.focus(False)
        else:
            self.box.show()
            if not self.vimiv.paths:
                self.vimiv.image.vimiv.image.scrolled_win.hide()
            else:  # Try to focus the current image in the library
                path = os.path.dirname(self.vimiv.paths[self.vimiv.index])
                if path == os.path.abspath("."):
                    self.treeview.set_cursor(Gtk.TreePath([self.vimiv.index]),
                                             None, False)
                    self.treepos = self.vimiv.index
            # Do not play Gifs with the lib
            self.vimiv.image.animation_toggled = True
            self.toggled = not self.toggled
            self.focus(True)
            # Markings and other stuff might have changed
            self.reload(os.path.abspath("."))
        if not self.vimiv.image.user_zoomed and self.vimiv.paths:
            self.vimiv.image.zoom_to(0)  # Always rezoom the image
        #  Change the toggle state of animation
        self.vimiv.image.update()

    def focus(self, library=True):
        """ Focused library object """
        if library:
            if not self.toggled:
                self.toggle()
            self.treeview.grab_focus()
            self.focused = True
        else:
            self.vimiv.image.vimiv.image.scrolled_win.grab_focus()
            self.focused = False
        # Update info for the current mode
        self.vimiv.statusbar.update_info()

    def treeview_create(self, search=False):
        """ Creates all the gtk widgets for the treeview """
        # The search parameter is necessary to highlight searches after a search
        # and to delete search items if a new directory is entered
        if not search:
            self.vimiv.commandline.reset_search()
        # Tree View
        current_file_filter = self.filestore(self.datalist_create())
        self.treeview = Gtk.TreeView.new_with_model(current_file_filter)
        # Needed for the movement keys
        self.treepos = 0
        self.treeview.set_enable_search(False)
        # Select file when row activated
        self.treeview.connect("row-activated", self.file_select, True)
        # Handle key events
        self.treeview.add_events(Gdk.EventMask.KEY_PRESS_MASK)
        self.treeview.connect("key_press_event",
                              self.vimiv.keyhandler.run, "LIBRARY")
        # Add the columns
        for i, name in enumerate(["Num", "Name", "Size", "M"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(name, renderer, markup=i)
            if name == "Name":
                column.set_expand(True)
                column.set_max_width(20)
            self.treeview.append_column(column)

    def filestore(self, datalist):
        """ Returns the file_filter for the tree view """
        # Filelist in a liststore model
        self.filelist = Gtk.ListStore(int, str, str, str)
        # Numerate each filename
        count = 0
        for data in datalist:
            count += 1
            data.insert(0, count)
            # The data into the filelist
            self.filelist.append(data)

        current_file_filter = self.filelist.filter_new()
        return current_file_filter

    def datalist_create(self):
        """ Returns the list of data for the file_filter model """
        self.datalist = list()
        self.files = self.filelist_create()
        # Remove unsupported files if one isn't in the self.vimiv.tags.directory
        if os.path.abspath(".") != self.vimiv.tags.directory:
            self.files = [
                possible_file
                for possible_file in self.files
                if is_image(possible_file) or os.path.isdir(possible_file)]
        # Add all the supported files
        for fil in self.files:
            markup_string = fil
            size = self.filesize[fil]
            is_marked = ""
            if os.path.abspath(fil) in self.vimiv.mark.marked:
                is_marked = "[*]"
            if os.path.isdir(fil):
                markup_string = "<b>" + markup_string + "</b>"
            if fil in self.vimiv.commandline.search_names:
                markup_string = self.markup + markup_string + '</span>'
            self.datalist.append([markup_string, size, is_marked])

        return self.datalist

    def file_select(self, alternative, count, b, close):
        """ Focus image or open dir for activated file in library """
        if isinstance(count, str):
            fil = count
        else:
            count = count.get_indices()[0]
            fil = self.files[count]
            self.remember_pos(os.path.abspath("."), count)
        # Tags
        if os.path.abspath(".") == self.vimiv.tags.directory:
            self.vimiv.tags.load(fil)
            # Close if selected twice
            if fil == self.vimiv.tags.last:
                self.toggle()
            # Remember last tag selected
            self.vimiv.tags.last = fil
            return
        # Rest
        if os.path.isdir(fil):  # Open the directory
            self.move_up(fil)
        else:  # Focus the image and populate a new list from the dir
            if self.vimiv.paths and fil in self.vimiv.paths[self.vimiv.index]:
                close = True  # Close if file selected twice
            path = 0  # Reload the path, could have changed (symlinks)
            for f in self.files:
                if f == fil:
                    break
                else:
                    path += 1
            self.treeview.set_cursor(Gtk.TreePath(path), None, False)
            self.treepos = path
            self.vimiv.paths, self.vimiv.index = populate(self.files)
            if self.vimiv.paths:
                self.grid.set_size_request(self.width - self.border_width,
                                           10)
                self.vimiv.image.vimiv.image.scrolled_win.show()
            # Show the selected file, if thumbnail toggled go out
            if self.vimiv.thumbnail.toggled:
                self.vimiv.thumbnail.toggle()
                self.treeview.grab_focus()
            self.vimiv.image.move_index(delta=count)
            # Close the library depending on key and repeat
            if close:
                self.toggle()
                self.vimiv.image.update()

    def move_up(self, directory="..", start=False):
        """ move (up/to) directory in the library """
        try:
            curdir = os.path.abspath(".")
            os.chdir(directory)
            if not start:
                self.reload(os.path.abspath("."), curdir)
        except:
            self.vimiv.statusbar.err_message("Error: directory not accessible")

    def remember_pos(self, directory, count):
        """ Write the current position in dir to the dir_pos dictionary """
        self.dir_pos[directory] = count

    def reload(self, directory, curdir="", search=False):
        """ Reloads the treeview """
        self.scrollable_treelist.remove(self.treeview)
        self.treeview_create(search)
        self.scrollable_treelist.add(self.treeview)
        self.focus(True)
        # Check if there is a saved position
        if directory in self.dir_pos.keys():
            self.treeview.set_cursor(Gtk.TreePath(self.dir_pos[directory]),
                                     None, False)
            self.treepos = self.dir_pos[directory]
        # Check if the last directory is in the current one
        else:
            curdir = os.path.basename(curdir)
            for i, fil in enumerate(self.files):
                if curdir == fil:
                    self.treeview.set_cursor(Gtk.TreePath([i]), None, False)
                    self.treepos = i
                    break
        self.box.show_all()

    def move_pos(self, forward=True):
        """ Move to pos in lib """
        max_pos = len(self.files) - 1
        if self.vimiv.keyhandler.num_str:
            pos = int(self.vimiv.keyhandler.num_str) - 1
            if pos < 0 or pos > max_pos:
                self.vimiv.statusbar.err_message("Warning: Unsupported index")
                return False
        elif forward:
            pos = max_pos
        else:
            pos = 0
        try:
            self.treepos = pos
            self.treeview.set_cursor(Gtk.TreePath(self.treepos), None, False)
        except:
            self.vimiv.statusbar.err_message("Warning: Unsupported index")
            return False

        self.vimiv.keyhandler.num_clear()
        return True

    def resize(self, val=None, inc=True):
        """ Resize the library and update the image if necessary """
        if isinstance(val, int):
            # The default 0 passed by arguments
            if not val:
                val = 300
            self.width = self.default_width
        elif val:  # A non int was given as library width
            self.vimiv.statusbar.err_message("Library width must be an integer")
            return
        elif inc:
            self.width += 20
        else:
            self.width -= 20
        # Set some reasonable limits to the library size
        if self.width > self.vimiv.winsize[0] - 200:
            self.width = self.vimiv.winsize[0] - 200
        elif self.width < 100:
            self.width = 100
        self.grid.set_size_request(self.width - self.border_width, 10)
        # Rezoom image
        if not self.vimiv.image.user_zoomed and self.vimiv.paths:
            self.vimiv.image.zoom_to(0)

    def toggle_hidden(self):
        """ Toggles showing of hidden files """
        self.show_hidden = not self.show_hidden
        self.reload('.')

    def filelist_create(self, directory="."):
        """ Create a filelist from all files in directory """
        # Get data from ls -lh and parse it correctly
        if self.show_hidden:
            p = Popen(['ls', '-lAhL', directory], stdin=PIPE, stdout=PIPE,
                      stderr=PIPE)
        else:
            p = Popen(['ls', '-lhL', directory], stdin=PIPE, stdout=PIPE,
                      stderr=PIPE)
        data = p.communicate()[0]
        data = data.decode(encoding='UTF-8').split("\n")[1:-1]
        files = []
        self.filesize = {}
        for fil in data:
            fil = fil.split()
            # Catch stupid filenames with whitespaces
            filename = " ".join(fil[8:])
            files.append(filename)
            # Number of images in directory as filesize
            if os.path.isdir(filename):
                try:
                    subfiles = os.listdir(filename)
                    subfiles = [subfile
                                for subfile in subfiles
                                if is_image(os.path.join(filename, subfile))]
                    self.filesize[filename] = str(len(subfiles))
                except:
                    self.filesize[filename] = "N/A"
            else:
                self.filesize[filename] = fil[4]

        return files

    def scroll(self, direction):
        """ Scroll the library viewer and select if necessary """
        # Handle the specific keys
        if direction == "h":  # Behave like ranger
            self.remember_pos(os.path.abspath("."), self.treepos)
            self.move_up()
        elif direction == "l":
            self.file_select("a", Gtk.TreePath(self.treepos), "b", False)
        else:
            # Scroll the tree checking for a user step
            if self.vimiv.keyhandler.num_str:
                step = int(self.vimiv.keyhandler.num_str)
            else:
                step = 1
            if direction == "j":
                self.treepos = (self.treepos + step) % len(self.filelist)
            else:
                self.treepos = (self.treepos - step) % len(self.filelist)

            self.treeview.set_cursor(Gtk.TreePath(self.treepos), None, False)
            # Clear the user prefixed step
            self.vimiv.keyhandler.num_clear()
        return True  # Deactivates default bindings (here for Arrows)