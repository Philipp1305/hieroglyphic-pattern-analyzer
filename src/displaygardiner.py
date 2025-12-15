from src.database.select import run_select
from src.database.connect import connect

def translate_to_gardiner():
    #join t_sorted_glyphs id_gylph with t_gylphes_raw 
    rows = run_select(
        "SELECT gc.unicode"
        "FROM t_gardiner_codes AS gc"
        "JOIN t_glyphes_raw AS gr"
        "ON gc.id = gr.id_gardiner"
        "JOIN t_glyphes_sorted AS gs"
        "ON gr.id_original = gs.id_glyphes;")
    
    print(rows)