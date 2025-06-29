"""Test package for the Note Review Scheduler application.

This package contains comprehensive tests for all system components:
- Database operations and models
- Email system and formatting  
- Selection algorithms and content analysis
- Scheduler system and monitoring
- Security and credential management
"""

import sys
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def run_all_tests() -> int:
    """Run all test modules and return exit code."""
    import subprocess
    import os
    
    # Change to project root directory
    os.chdir(project_root)
    
    test_scripts = [
        "test_database.py",
        "test_email_system.py", 
        "test_selection_system.py",
        "test_scheduler_system.py"
    ]
    
    passed = 0
    failed = 0
    
    print("Running All Note Review Scheduler Tests")
    print("=" * 60)
    
    for script in test_scripts:
        print(f"\nRunning {script}...")
        try:
            # Run script directly from tests directory
            script_path = project_root / "tests" / script
            result = subprocess.run([
                sys.executable, str(script_path)
            ], capture_output=False, text=True)
            
            if result.returncode == 0:
                print(f"{script} PASSED")
                passed += 1
            else:
                print(f"{script} FAILED")
                failed += 1
                
        except Exception as e:
            print(f"{script} ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("FINAL TEST SUMMARY")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {passed / (passed + failed) * 100:.1f}%")
    
    return 1 if failed > 0 else 0

if __name__ == "__main__":
    exit(run_all_tests()) 