from .compat import load_main_module

main_module = load_main_module()
async_setup_entry = main_module.async_setup_entry
async_unload_entry = main_module.async_unload_entry
