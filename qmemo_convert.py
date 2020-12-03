#!/usr/bin/env python3

# remember to run as python3

# https://www.w3schools.com/python/python_json.asp
# https://www.geeksforgeeks.org/working-zip-files-python/

import os.path
import glob
from zipfile import ZipFile
import json
import sys

import uuid

import sqlite3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, GLib, Gtk, Gdk
import signal


##### CONFIG:
lqm_path = "lqm"							# name of folder in cwd which contains your .lqm files
db_filename = 'fairnote/fairnote.db'		# path to folder in cwd which contains your sqlite db file..
html_out_filename = 'lqm_fairnote_py.html'	# name of html file in cwd to which our html will be written

note_display_height = 150
auto_update_when_chockboxes_toggled = True
##### 


lqm_flist = []

hpane_vars = { 'divpos' : 0.5}

db_conn = {}
win = {}


class QMemoConvertWindow(Gtk.Window):
	def __init__(self):
		super(QMemoConvertWindow, self).__init__( default_width=800, default_height=600, title="QMemo Convert" )
		self.cancellable = Gio.Cancellable()
		
		self.disabled_lqm_buttons_arr = []
		self.lqm_obj_arr = []
		self.fairnote_obj_arr = []
		self.fairnote_add_these_arr = []
		self.add_button_arr = []
		
		self.lqm_html = ""
		self.fairnote_html = ""
        
		box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, border_width=12)

		self.cancel_button = Gtk.Button(label="Quit")
		self.cancel_button.connect("clicked", self.on_quit_clicked)
		box.pack_start(self.cancel_button, False, True, 0)

		self.generate_html_button = Gtk.Button(label="generate html for both")
		self.generate_html_button.connect("clicked", self.generate_html)
		box.pack_start(self.generate_html_button, False, False, 0)

		proc_box = Gtk.HBox()

		process_lqm_button = Gtk.Button(label="load lqm")
		process_lqm_button.set_tooltip_text("Loads the .lqm files from the '" + lqm_path + "' directory")
		process_lqm_button.connect("clicked", self.process_lqm)
		proc_box.pack_start(process_lqm_button, True, False, 0)

		process_fairnote_button = Gtk.Button(label="reload fairnote sqlite")
		process_fairnote_button.set_tooltip_text("Loads the db from '" + db_filename + "' ")
		process_fairnote_button.connect("clicked", self.reload_fairnote_sqlite)
		proc_box.pack_start(process_fairnote_button, True, False, 0)

		box.pack_start(proc_box, False, False, 0)
		
		self.first_line_bold_to_title = Gtk.CheckButton(label="If first line is bold, make it the note title. (Note: all formatting is removed when converting)")
		self.first_line_bold_to_title.set_active(True) 
		self.first_line_bold_to_title.set_tooltip_text("Only applies when first line is not a checkbox. If unselected, the first line will just be a normal entry.")
		if auto_update_when_chockboxes_toggled:
			self.first_line_bold_to_title.connect("toggled", self.toggle_first_line_bold_to_title)
		box.pack_start(self.first_line_bold_to_title, False, True, 0)

		self.break_multiline_checkbox_up = Gtk.CheckButton(label="Break multi-line checkboxes into multiple checkboxes")
		self.break_multiline_checkbox_up.set_active(True) 
		self.break_multiline_checkbox_up.set_tooltip_text("Fairnote can't handle multi-line checkboxes. If unselected, the newlines will be converted to spaces.")
		if auto_update_when_chockboxes_toggled:
			self.break_multiline_checkbox_up.connect("toggled", self.toggle_break_multiline_checkbox_up)
		box.pack_start(self.break_multiline_checkbox_up, False, False, 0)

		allbtn_box = Gtk.HBox()

		self.all_button = Gtk.Button(label="all ->")
		self.all_button.set_tooltip_text("Copies all lqm notes to fairnote notes")
		self.all_button.set_sensitive(False)
		self.all_button.connect("clicked", self.add_all_notes)
		allbtn_box.pack_start(self.all_button, True, False, 0)

		box.pack_start(allbtn_box, False, False, 0)

		self.vbox_L = Gtk.VBox()
		self.scrolled_L = Gtk.ScrolledWindow()
		self.scrolled_L.add(self.vbox_L)
		
		self.vbox_R = Gtk.VBox()
		hbox_R = Gtk.HBox()
		hbox_R.pack_start(self.vbox_R, True, True, 5)
		self.scrolled_R = Gtk.ScrolledWindow()
		self.scrolled_R.add(hbox_R)
		
		hpane = Gtk.HPaned()
		hpane.set_wide_handle(True)
		hpane.connect("size-allocate", self.hpane_resize_cb)
		hpane.pack1(self.scrolled_L)
		hpane.pack2(self.scrolled_R)
		
		box.pack_start(hpane, True, True, 0)

		# TODO: preview pane for a note?
		#textview_bottom = Gtk.TextView()
		#self.textbuffer_bottom = textview_bottom.get_buffer()
		#self.scrolled_bottom.add(textview_bottom)
		#box.pack_start(textview_bottom, False, True, 0)

		self.save_fairnote_button = Gtk.Button(label="save fairnote sqlite")
		self.save_fairnote_button.connect("clicked", self.save_fairnote_sqlite)
		self.save_fairnote_button.set_tooltip_text("Adds the new notes, without removing any content")
		self.save_fairnote_button.set_sensitive(False)
		box.pack_start(self.save_fairnote_button, False, False, 0)
		
		self.add(box)
		
		self.reload_fairnote_sqlite_h()
		
	# https://www.programcreek.com/python/example/110241/gi.repository.Gtk.Paned#Example_5
	def hpane_resize_cb(self, hpane, allocation):
		global hpane_vars
		
		if allocation.width != 1:
			if not 'lastwidth' in hpane_vars:
				hpane_vars['lastwidth'] = allocation.width
			
			elif hpane_vars['lastwidth'] == allocation.width:
				hpane_vars['divpos'] = hpane.get_position() / hpane.get_allocation().width
			hpane_pos = hpane_vars['divpos'] * allocation.width
		else:
			hpane_pos = 0.5 * allocation.width

		hpane.set_position(int(hpane_pos + .5))
		hpane_vars['lastwidth'] = allocation.width
		# hpane.disconnect(conid)

	def toggle_first_line_bold_to_title(self, widget):
		self.process_lqm_h()

	def toggle_break_multiline_checkbox_up(self, widget):
		self.process_lqm_h()
			
	def append_text(self, text):
		self.append_text_L(text)
			
	def append_text_L(self, text):
		self.append_text_h(text, self.textbuffer_L, self.scrolled_L)
			
	def append_text_R(self, text):
		self.append_text_h(text, self.textbuffer_R, self.scrolled_R)
			
	def append_text_h(self, text, textbuffer, scrolled):
		iter_ = textbuffer.get_end_iter()
		textbuffer.insert(iter_, " %s\n" % (text))
		adj = scrolled.get_vadjustment()
		adj.set_value(adj.get_upper() - adj.get_page_size())
			
	def on_quit_clicked(self, button):
		quit()

	def quit():
		exit()

	def generate_html(self, widget, data = None):
		with open(html_out_filename, 'w') as html_outfile:
			print('creating the html file.... ')
			
			print('<title>qmemo convert</title>', file=html_outfile)
			print('<style>body {font-size: 8pt;} div.note {display: inline-block; width: 49%; vertical-align:top}</style>', file=html_outfile)
			
			print ("<div class='note'>" + "<h1>QMEMO</h1>\n\n" + self.lqm_html + "</div>\n\n", file=html_outfile)
			
			print ("<div class='note'>" + "<h1>FAIRNOTE</h1>\n\n" + self.fairnote_html + "</div>\n\n", file=html_outfile)


	def reload_fairnote_sqlite(self, widget, data = None):
		self.reload_fairnote_sqlite_h()

	def reload_fairnote_sqlite_h(self):
		for button in self.disabled_lqm_buttons_arr:
			button.set_sensitive(True)
		self.disabled_lqm_buttons_arr = []
		
		self.load_fairnote_sqlite()
		self.create_noteview_R(self.fairnote_obj_arr)

	def show_fairnote(self):
		self.create_noteview_R(self.fairnote_obj_arr)

	def process_lqm(self, widget, data = None):
		self.process_lqm_h()

	def process_lqm_h(self):
		self.load_lqm()
		self.create_noteview_L(self.lqm_obj_arr)
		self.all_button.set_sensitive(True)

		
	def clear_children(self, from_this_widget):
		for child_widget in from_this_widget.get_children():
			from_this_widget.remove(child_widget)

	def create_noteview_L(self, noteobj_list):
		self.create_noteview_side(self.vbox_L, noteobj_list, True)
		
	def create_noteview_R(self, noteobj_list):
		self.create_noteview_side(self.vbox_R, noteobj_list, False)
		
	def create_noteview_side(self, noteview, noteobj_list, on_left):
		self.clear_children(noteview)
		i = 0
		for noteview_note in noteobj_list:
			vbox = Gtk.VBox()
			scrolled = Gtk.ScrolledWindow()
			scrolled.set_size_request(100, note_display_height)		# this removes gtk warnings
			scrolled.add(vbox)
			
			if noteview_note.get("title", ""):
				title_label = Gtk.Label(label="TITLE: " + noteview_note.get("title"), halign=Gtk.Align.START, valign=Gtk.Align.START, selectable=True)	# label is overwritten by markup below
				title_label.set_markup("<b>" + noteview_note.get("title") + "</b>")
				vbox.pack_start(title_label, False, True, 0)
			
			if on_left:
				self.create_noteview_note(vbox, noteview_note["entries"])
				hbox = Gtk.HBox()
				hbox.pack_start(scrolled, True, True, 5)
				button_vbox = Gtk.VBox()
				add_note_button = Gtk.Button(label="->")
				add_note_button.note_id = noteview_note["id"]
				add_note_button.note_arr_index = i
				add_note_button.connect("clicked", self.add_note)
				add_note_button.button_index = len(self.add_button_arr)
				self.add_button_arr.append(add_note_button)
				button_vbox.pack_start(add_note_button, True, False, 5)
				hbox.pack_start(button_vbox, False, False, 5)
				noteview.pack_start(hbox, False, False, 5)
			else:
				if "content" in noteview_note:
					self.create_noteview_note(vbox, self.fairnote_split_entries(noteview_note))
				else:
					self.create_noteview_note(vbox, noteview_note["entries"])
				noteview.pack_start(scrolled, False, False, 5)
			i += 1
		noteview.show_all()
		
	def fairnote_split_entries(self, note_obj):
		fairnote_ret = {}
		fairnote_ret["title"]  = note_obj["title"]	# NOTE: it's just for the noteview, so we don't need all the keys copied over
		fairnote_ret["entries"] = []
		
		checked_state_arr = note_obj["META"].split(',')
		i = 0
		for note_cont in note_obj["content"].splitlines():
			i += 1	# fairnote indexes for these start at "1"
			fairnote_note_entry = {}
			fairnote_note_entry["content"] = note_cont
			fairnote_note_entry["checkbox"] = note_obj.get("checklist", False)
			ischecked = str(i) in checked_state_arr
			fairnote_note_entry["checked"] = str(i) in checked_state_arr
			fairnote_ret["entries"].append(fairnote_note_entry)
		else:	# if content is empty
			fairnote_note_entry = {}
			fairnote_note_entry["content"] = ""
			fairnote_note_entry["checkbox"] = note_obj.get("checkbox", False)
			fairnote_note_entry["checked"] =  note_obj.get("checked", False)
			fairnote_ret["entries"].append(fairnote_note_entry)
		return fairnote_ret["entries"]
		
		
	def create_noteview_note(self, noteview, noteobj_list):
		for noteobj in noteobj_list:
			label_txt = noteobj.get("content", "")
			temp_label = Gtk.Label(label=label_txt, halign=Gtk.Align.START, valign=Gtk.Align.START, selectable=True)
			
			if noteobj.get("checkbox", False):
				cbox = Gtk.CheckButton(valign=Gtk.Align.START)
				cbox.set_sensitive(False)
				cbox.set_active(noteobj.get("checked", False))
				ch_box = Gtk.HBox()
				ch_box.pack_start(cbox, False, True, 0)
				ch_box.pack_start(temp_label, False, True, 0)
				noteview.pack_start(ch_box, False, True, 0)
			else:
				noteview.pack_start(temp_label, False, True, 0)
		
	def add_all_notes(self, button):
		for add_button in self.add_button_arr:
			self.add_note_h(add_button)
		self.show_fairnote()
		
	def add_note(self, button):
		self.add_note_h(button)
		self.show_fairnote()
		
	def add_note_h(self, button):
		button.set_sensitive(False)	# prevent double adding
		self.disabled_lqm_buttons_arr.append(button)
		fairnote_add_this = self.lqm_obj_arr[button.note_arr_index]
		last_fairnote_id = len(self.fairnote_obj_arr)
		fairnote_add_this["_id"] = last_fairnote_id + 1
		fairnote_add_this["uuid"] = str(uuid.uuid4())
		self.fairnote_add_these_arr.append(fairnote_add_this)
		self.fairnote_obj_arr.append(fairnote_add_this)
		self.save_fairnote_button.set_sensitive(True)

	def save_fairnote_sqlite(self, button):
		print('SAVING the fairnote sqlite files....')
		
		global db_filename
		global db_conn
		
		# https://stackoverflow.com/questions/61788055/sqlite3-error-you-did-not-supply-a-value-for-binding-1
		sqlite3.paramstyle = 'named'
		
		# https://docs.python.org/2/library/sqlite3.html
		db_cur = db_conn.cursor()
		
		cols = [ '_id', 'uuid', 'created_on', 'modified_on', 'title', 'content', 'checklist', 'META', 'ENCRYPTED', 'STARRED', 'ARCHIVED', 'TRASHED', 'PINNED' ]
		sql = 'INSERT INTO `note` (' + ", ".join(cols) + ') VALUES (' + ', '.join([':{0}'.format(i) for i in cols]) + ')'
		#sql = 'INSERT INTO `note` VALUES (' + ', '.join([':{0}'.format(i) for i in cols]) + ')'
		
		for addme in  self.fairnote_add_these_arr:
			db_cur.execute(sql, addme)
		# db_cur.executemany(sql, self.fairnote_add_these_arr)
		
		# https://stackoverflow.com/questions/3300464/how-can-i-get-dict-from-sqlite-query	
			## TABLE: `note`
			#  COLS:  _id (needs to be read first from sqlite), uuid, created_on, modified_on, title, content, checklist (boolean), META (first=1, list of checked items in checklist)
			
		db_ret =  db_cur.execute('SELECT * FROM `note`')
		
		for row in db_ret:
			fairnote_note = {}
			fairnote_note["id"] = dict(row)["_id"]
			fairnote_note["UUID"] = dict(row)["UUID"]
			fairnote_note["created_on"] = dict(row)["CREATED_ON"]
			fairnote_note["modified_on"] = dict(row)["MODIFIED_ON"]
			fairnote_note["title"] = dict(row)["TITLE"]
			fairnote_note["CONTENT"] = dict(row)["CONTENT"]
			fairnote_note["entries"] = []
				
			# print( " NOTE ID: " +str(dict(row)["_id"]) + " - UUID: [" +str(dict(row)["UUID"]) + "] - CREATED_ON: ["  +str(dict(row)["CREATED_ON"]) + "] - MODIFIED_ON: ["  +str(dict(row)["MODIFIED_ON"]) + "] - TITLE: ["  +str(dict(row)["TITLE"]) + "] - CHECKLIST: ["  +str(dict(row)["CHECKLIST"]) + "] - META: ["  +str(dict(row)["META"]) + "]  - CONTENT: ["  +str(dict(row)["CONTENT"]) + "]" )
		
		# prevent double add
		self.fairnote_add_these_arr = []

		# Save changes before closing connection or changes will be lost
		db_conn.commit()

		# db_cur.close()
		# db_conn.close()
		return


	def load_fairnote_sqlite(self):
		self.fairnote_obj_arr = []
		ret_html = ""
		
		global db_filename
		if not os.path.isfile(db_filename):
			print( "db file not found: " + db_filename)
			return
		
		global db_conn
		# https://docs.python.org/2/library/sqlite3.html
		db_conn = sqlite3.connect(db_filename)
		db_conn.row_factory = sqlite3.Row	# to get dict's from our queries
		db_cur = db_conn.cursor()
		
		# for table_name in db_cur.execute("select name from sqlite_master where type = 'table'"):
			# print("table_name: " +str(table_name))
			
		# for col_name in db_cur.execute('PRAGMA table_info(`note`)'):
			# print("col_name: " +str(col_name))

			## TABLE: `note`
			#  COLS: _id (needs to be read first from sqlite), uuid, created_on, modified_on, title, content, checklist (boolean), META (first=1, list of checked items in checklist)
			
		# https://stackoverflow.com/questions/3300464/how-can-i-get-dict-from-sqlite-query
		db_ret =  db_cur.execute('SELECT * FROM `note`')
		col_name_list = [tuple[0] for tuple in db_ret.description]
		# ret_html += "col names: " + str(col_name_list) + "<br><br>\n"
		# print db_cur.fetchone()
		
		for row in db_ret:
			fairnote_note = {}
			fairnote_note["id"] = dict(row)["_id"]
			fairnote_note["UUID"] = dict(row)["UUID"]
			fairnote_note["created_on"] = dict(row)["CREATED_ON"]
			fairnote_note["modified_on"] = dict(row)["MODIFIED_ON"]
			fairnote_note["title"] = dict(row)["TITLE"]
			fairnote_note["entries"] = []
				
			# print( " NOTE ID: " +str(dict(row)["_id"]) + " - UUID: [" +str(dict(row)["UUID"]) + "] - CREATED_ON: ["  +str(dict(row)["CREATED_ON"]) + "] - MODIFIED_ON: ["  +str(dict(row)["MODIFIED_ON"]) + "] - TITLE: ["  +str(dict(row)["TITLE"]) + "] - CHECKLIST: ["  +str(dict(row)["CHECKLIST"]) + "] - META: ["  +str(dict(row)["META"]) + "]" )
			
			ret_html +=  "NOTE ID: " +str(dict(row)["_id"]) + " - UUID: [" +str(dict(row)["UUID"]) + "] - c_date: ["  +str(dict(row)["CREATED_ON"]) + "] - m_date: ["  +str(dict(row)["MODIFIED_ON"]) + "]" 
			
			ret_html += "<fieldset>"
			if dict(row)["TITLE"]:
				ret_html += " TITLE: [" +str(dict(row)["TITLE"]) + "]" 
				ret_html += "<br>\n"
				
			if dict(row)["CHECKLIST"]:
				checked_state_arr = dict(row)["META"].split(',')
				checkboxes = dict(row)["CONTENT"].splitlines()
				i = 0
				for checkbox_str in checkboxes:
					i += 1	# fairnote indexes for these start at "1"
					fairnote_note_entry = {}
					fairnote_note_entry["content"] = checkbox_str
					fairnote_note_entry["checkbox"] = True
					fairnote_note_entry["checked"] = str(i) in checked_state_arr
					if str(i) in checked_state_arr:
						checked = True
						ret_html += "<input type='checkbox' checked><del>"
						ret_html += checkbox_str
						ret_html += "</del>"
					else:
						checked = False
						ret_html += "<input type='checkbox'>"
						ret_html += checkbox_str
					ret_html += "<br>\n"
					fairnote_note["entries"].append(fairnote_note_entry)
			else: 
				ret_html +=  str(dict(row)["CONTENT"]).replace("\n", "<br>\n")
				for entry_cont in dict(row)["CONTENT"].splitlines():
					fairnote_note["entries"].append({"content" : entry_cont})
			ret_html += "</fieldset><br>"
			
			self.fairnote_obj_arr.append(fairnote_note)

		# db_cur.close()
		# db_conn.close()
		
		self.fairnote_html = ret_html

	def load_lqm(self):
		print('loading the lqm files....')
		self.lqm_obj_arr = []
		ret_html = ""
		
		for (lqm_filename) in glob.glob(lqm_path + '/' + '*.lqm'):
			lqm_flist.append(lqm_filename)
			#print(lqm_filename)
			
			# FAIRNOTE: _id (needs to be read first from sqlite), uuid, created_on, modified_on, title, content, checklist (boolean), META (first=1, list of checked items in checklist)
			lqm_note = {}
			lqm_note["filename"] = lqm_filename
			
			# NOTE: each lqm_file becomes its own FAIRNOTE note.
			with ZipFile(lqm_filename, 'r') as myzip:
				lqm_json = json.loads(myzip.read('memoinfo.jlqm'))
				memo_dets_str = " MEMO ID: " + str(lqm_json["Memo"]["Id"]) + "  [" + lqm_filename + "] c_date [" + str(lqm_json["Memo"]["CreatedTime"]) + "] m_date [" + str(lqm_json["Memo"]["ModifiedTime"]) + "]  MemoObjectList= " + str(len(lqm_json["MemoObjectList"]))
				# print(memo_dets_str)
				ret_html += memo_dets_str
				# lqm_json["Category"]["CategoryName"],  lqm_json["Memo"]["Desc"], lqm_json["Memo"]["CheckboxDesc"], lqm_json["MemoObjectList"][0])
				ret_html += "<fieldset>"
				
				lqm_note["id"] = str(lqm_json["Memo"]["Id"])
				lqm_note["created_on"] = lqm_json["Memo"]["CreatedTime"]
				lqm_note["modified_on"] = lqm_json["Memo"]["ModifiedTime"]
				lqm_note["title"] = ""
				lqm_note["checklist"] = False
				lqm_note["META"] = ""
				lqm_note["content"] = ""	# not used by noteview
				lqm_note["entries"] = []
				# to satisfy NOT NULL from fairnote db:
				lqm_note["ENCRYPTED"] = False
				lqm_note["STARRED"] = False
				lqm_note["ARCHIVED"] = False
				lqm_note["TRASHED"] = False
				lqm_note["PINNED"] = False
				
				MemoObjectList = lqm_json["MemoObjectList"]
				# https://stackoverflow.com/questions/10079216/skip-first-entry-in-for-loop-in-python
				iter_MemoObjectList = iter(MemoObjectList)
				
				if self.first_line_bold_to_title.get_active() and  "<b>" in MemoObjectList[0].get("Desc", "").partition('\n')[0]:
					parts = MemoObjectList[0]["DescRaw"].partition('\n')
					lqm_note["title"] = parts[0]
					ret_html += "<b>" + lqm_note["title"] + "</b><br>\n"
					if parts[1] != "\n":
						next(iter_MemoObjectList)	# skip first item, if there's no content but the title
					else:
						MemoObjectList[0]["DescRaw"] = parts[2]
					
				itemcount = 1
				# NOTE: each MemoObjectList item becomes a single line in a FAIRNOTE note.
				for (memo_obj) in iter_MemoObjectList:
					#
					# type=0 = normal text
					# type=5 = checkbox
					# type=6 = filename
					#
					if memo_obj["Type"] == 6:
						continue
						
					lqm_note_entry = {} # for noteview
					#desc = memo_obj.get("Desc", "") # this is html encoded, includes font colors, italics, bold, etc.. we ignore it (until parsing is implemented in the future)
					desc_raw = memo_obj.get("DescRaw", "") # need to use "get" because if type=6, there is no Desc or DescRaw -- fixed above with the "continue"
					desc_raw_html = desc_raw.replace("\n", "<br>\n")
					
					desc_raw_lines = desc_raw.splitlines()
					linecount = len(desc_raw_lines)
					# print("LINE COUNT = " + str( linecount ))
					if linecount > 1:
						itemcount += linecount - 1 # because we +1 below
						if not self.break_multiline_checkbox_up.get_active():
							desc_raw = desc_raw.replace("\n", " ")
					
					if lqm_note["content"] == "":
						lqm_note["content"] = desc_raw # for FAIRNOTE
					else:
						lqm_note["content"] += "\n" + desc_raw # for FAIRNOTE 
					lqm_note_entry["content"] = desc_raw
					
					# lqm_note["checklist"] = (memo_obj["Type"] == 5)
					if memo_obj["Type"] == 5:
						lqm_note["checklist"] = True	# because just one checkbox should turn the whole memo into a checkbox obj for FAIRNOTE
						
						lqm_note_entry["checkbox"] = True
						lqm_note_entry["checked"] = memo_obj["IsChecked"]
							
						
						if memo_obj["IsChecked"]:
							if lqm_note["META"]:
								lqm_note["META"] += "," # for FAIRNOTE
							lqm_note["META"] +=  str(itemcount)
							ret_html += "<input type='checkbox' checked><del>"
							ret_html += desc_raw_html
							ret_html += "</del>"
						else:
							ret_html += "<input type='checkbox'>"
							ret_html += desc_raw_html
					else:
						ret_html += desc_raw_html
						#ret_html += desc
					ret_html += "<br>\n"
					
					lqm_note["entries"].append(lqm_note_entry)
					itemcount += 1
				ret_html += "</fieldset><br>"
				
				self.lqm_obj_arr.append(lqm_note)
				
		self.lqm_html = ret_html


def init_worker():
	signal.signal(signal.SIGINT, signal.SIG_IGN) # https://noswap.com/blog/python-multiprocessing-keyboardinterrupt

if __name__ == "__main__":
	# https://stackoverflow.com/questions/16410852/keyboard-interrupt-with-with-python-gtk
	signal.signal(signal.SIGINT, signal.SIG_DFL)
    
	win = QMemoConvertWindow()
	#win.set_icon_name("accessories-dictionary",)
	win.set_icon_name("address-book-new",) # find icon names by running: "gtk3-icon-browser"

	win.show_all()
	win.connect("delete-event", Gtk.main_quit)

	Gtk.main()


