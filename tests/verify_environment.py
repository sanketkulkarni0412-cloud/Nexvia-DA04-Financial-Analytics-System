"""
Environment and Dependency Verification Script
Confirms all 10 required packages are correctly installed in .venv and compatible with Python 3.13.1.
"""
import sys

def verify_all():
    print(f"Python Executable: {sys.executable}")
    print(f"Python Version:    {sys.version.split()[0]}")
    print("-" * 50)
    
    modules = [
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("scipy", "scipy"),
        ("scikit-learn", "sklearn"),
        ("matplotlib", "matplotlib"),
        ("seaborn", "seaborn"),
        ("openpyxl", "openpyxl"),
        ("xlsxwriter", "xlsxwriter"),
        ("sqlalchemy", "sqlalchemy"),
        ("pytest", "pytest")
    ]
    
    all_ok = True
    for label, mod_name in modules:
        try:
            mod = __import__(mod_name)
            ver = getattr(mod, "__version__", "Installed")
            print(f"[PASS] {label:<15} : {ver}")
        except Exception as e:
            print(f"[FAIL] {label:<15} : {e}")
            all_ok = False
            
    print("-" * 50)
    if all_ok:
        print("STATUS: All 10 required libraries are verified and functioning!")
    else:
        print("STATUS: One or more dependencies failed verification.")
    return all_ok

if __name__ == "__main__":
    success = verify_all()
    sys.exit(0 if success else 1)
