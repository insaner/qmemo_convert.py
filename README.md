# qmemo_convert.py
Simple python script to convert your LG QMemo+ (QuickMemo+) memos to other formats (currently only HTML and FairNote)

LG's QuickMemo+ is an amazing, ad-free app included in LG branded Android phones. Unfortunately, the app only works on LG phones, and if you move to another app, you face losing all your memos. In my case I found a great replacement, after searching for many weeks: *FairNote*. It is also ad-free and provides an interface much like that of QMemo+ but the memo storage format is quite different, and there is no way to import from one to the other. I tried to poke around and see if there was a way to convert QMemo+'s "*.lqm*" files to FairNote's storage format.

I decided to write the script in Python also as a means of learning Python, so there might still be some parts of the code that are less-than-optimal, or "un-pythonic". There might also still be some cruft from previous revisions. The script works for me as-is, and I have to move on to other things, but you have been warned.

I have kept useful comments and links within the code for Python newbies like myself.

*NOTE*: Not all QMemo+ or FairNote Note features or attributes have been implemented, mostly it just works for: simple notes, checkboxes, and note titles. No images or files or archives or anything like that has been implemented, but it should be quite simple to modify the script to add those, as the relevant sections should have sufficient explanation in the code for even a novice coder to implement. If you do take that on, make sure to fork and share your code!

## Usage

By default, you will need to create 2 directories: *lqm/* and *fairnote/* where you will place your *.lqm* files (generated from within QuickMemo+ using the "export" feature) and the *fairnote.db* backup file (generated from within FairNote, using the "backup" feature), respectively. These paths can be modified in the config section at the top of the script. **Make sure you use a _copy_ of your FairNote db file, as it will be overwritten by the script**.

The script is run with a simple:

    python3 qmemo_convert.py
    

Usage should be quite simple to figure out, but basically the FairNote sqlite file is loaded automatically, and then you click to load your .lqm files. You can click "load" or "reload" at any time during execution if you want to switch out the files, or add (or remove) new .lqm's to your directory. There are some options you can toggle that modify how the notes are loaded or handled, and you can change in the config section whether these cause an automatic reload of the files (default is for them to not reload automatically). Most of the buttons have tooltips that give a little more explanation. Each QMemo+ note has an arrow to add it to the FairNote db, or you can add all of them at the same time. The db is not saved until you click the "save fairnote" button, after which there is **no undo**.

There is a button to generate an HTML file with the contents of both the .lqm files and the FairNote db. The default name for the output file is **lqm_fairnote_py.html** but you can change that in the config section.

Tested only on Linux. Requires GTK 3 and Python 3. **Use at your own risk!**

