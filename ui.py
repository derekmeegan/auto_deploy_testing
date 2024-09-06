import os
import importlib.util
from typing import Callable, Dict
import streamlit as st
from openai import OpenAI

def load_functions_from_folder(folder_path: str) -> Dict[str, Callable]:
    functions_dict = {}

    # Iterate over each file in the folder
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.py'):  # Only process Python files
            file_path = os.path.join(folder_path, file_name)
            module_name = file_name[:-3]  # Strip the .py extension

            # Dynamically load the module
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Extract function from the module (assuming there's only one function per file)
            functions = [getattr(module, attr) for attr in dir(module) 
                         if callable(getattr(module, attr)) and not attr.startswith("__")]
            
            # If there's exactly one function, add it to the dictionary
            if len(functions) == 1:
                functions_dict[module_name] = functions[0]
            else:
                raise ValueError(f"File {file_name} contains more than one function or no function.")
    
    return functions_dict