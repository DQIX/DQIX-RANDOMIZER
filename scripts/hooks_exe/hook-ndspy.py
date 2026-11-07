"""PyInstaller: ndspy with its SOURCES as well as its bytecode. son_pas patches
SDAT.save from its source (inspect.getsource), which a bytecode-only
bundle does not have (ndspy 4 crashes saving se_btl.sdat, research: son_pas)."""
module_collection_mode = "pyz+py"
