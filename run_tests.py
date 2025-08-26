import subprocess
import sys

def run_tests():
    print("🧪 Running essential tests...")
    
    # Run each test file
    test_files = [
        "tests/test_file_operations.py",
        "tests/test_core_flow.py", 
        "tests/test_ui_basic.py",
        "tests/test_llm_integration.py" 
    ]
    
    for test_file in test_files:
        print(f"\n📋 Running {test_file}...")
        result = subprocess.run([sys.executable, "-m", "pytest", test_file, "-v"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {test_file} - PASSED")
        else:
            print(f"❌ {test_file} - FAILED")
            print(result.stdout)

if __name__ == "__main__":
    run_tests()