import sys
import tkinter as tk
sys.path.insert(0, '.')
from views.summarizer_tab import SummarizerTab

root = tk.Tk()
root.withdraw()
notebook = tk.ttk.Notebook(root)
tab = SummarizerTab(notebook)

# Test the problematic assertions
tab.set_export_buttons_enabled(True)
state1 = tab.export_txt_btn.cget('state')
print('Enabled state:', repr(state1))
print('Type:', type(state1))
print('Equals normal:', state1 == "normal")
print('Equals disabled:', state1 == "disabled")

tab.clear_all()
state2 = tab.export_txt_btn.cget('state')
print('After clear state:', repr(state2))
print('Equals disabled:', state2 == "disabled")

# Test loading
tab.show_loading(True)
state3 = tab.send_btn.cget('state')
print('Loading state:', repr(state3))
print('Equals disabled:', state3 == "disabled")

root.destroy()