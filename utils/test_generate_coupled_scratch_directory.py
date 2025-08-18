#!/usr/bin/env python3
"""
Test script for the coupled scratch directory utility.
"""

import os
import sys
import tempfile
import shutil
import subprocess
from pathlib import Path

def test_coupled_scratch_directory():
    """Test the coupled scratch directory utility."""
    print("Testing coupled scratch directory utility...")
    
    # Get the script path
    script_dir = Path(__file__).parent.parent
    script_path = script_dir / "utils" / "generate_coupled_scratch_directory.py"
    
    if not script_path.exists():
        print(f"ERROR: Script not found at {script_path}")
        return False
    
    # Create temporary directories for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test static files
        atm_static_dir = temp_path / "atm_static"
        ocean_static_dir = temp_path / "ocean_static"
        atm_static_dir.mkdir()
        ocean_static_dir.mkdir()
        
        # Create dummy static files
        (atm_static_dir / "atm_config.txt").write_text("atmosphere configuration")
        (ocean_static_dir / "ocean_config.txt").write_text("ocean configuration")
        
        # Create test background files
        backgrounds_dir = temp_path / "backgrounds"
        backgrounds_dir.mkdir()
        
        atm_bg = backgrounds_dir / "atm_background.nc"
        ocean_bg = backgrounds_dir / "ocean_background.nc" 
        ice_bg = backgrounds_dir / "ice_background.nc"
        
        atm_bg.write_text("atmosphere background data")
        ocean_bg.write_text("ocean background data")
        ice_bg.write_text("ice background data")
        
        # Test output directory
        output_dir = temp_path / "scratch"
        
        # Run the utility
        cmd = [
            sys.executable, str(script_path),
            "--output-dir", str(output_dir),
            "--atm-static-dir", str(atm_static_dir),
            "--ocean-static-dir", str(ocean_static_dir),
            "--atm-backgrounds", str(atm_bg),
            "--ocean-backgrounds", str(ocean_bg),
            "--ice-backgrounds", str(ice_bg)
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"ERROR: Script failed with return code {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
        
        print("Script executed successfully")
        
        # Verify directory structure
        fv3_jedi_dir = output_dir / "fv3-jedi"
        soca_dir = output_dir / "soca"
        
        if not fv3_jedi_dir.exists():
            print("ERROR: fv3-jedi directory not created")
            return False
        
        if not soca_dir.exists():
            print("ERROR: soca directory not created")
            return False
        
        # Check fv3-jedi contents
        expected_fv3_files = ["atm_config.txt", "atm_background.nc"]
        for file in expected_fv3_files:
            if not (fv3_jedi_dir / file).exists():
                print(f"ERROR: Expected file {file} not found in fv3-jedi directory")
                return False
        
        # Check soca contents
        expected_soca_files = ["ocean_config.txt", "ocean_background.nc", "ice_background.nc", 
                              "mom6_input.nml", "MOM_input"]
        for file in expected_soca_files:
            if not (soca_dir / file).exists():
                print(f"ERROR: Expected file {file} not found in soca directory")
                return False
        
        print("All expected files found in correct directories")
        
        # Check file contents
        if (soca_dir / "mom6_input.nml").read_text().strip() == "":
            print("ERROR: mom6_input.nml is empty")
            return False
        
        if (soca_dir / "MOM_input").read_text().strip() == "":
            print("ERROR: MOM_input is empty")
            return False
        
        print("Generated configuration files have content")
        
        print("✓ All tests passed!")
        return True


def test_with_test_data():
    """Test using the project test data option."""
    print("\nTesting with --use-test-data option...")
    
    script_dir = Path(__file__).parent.parent
    script_path = script_dir / "utils" / "generate_coupled_scratch_directory.py"
    utils_dir = script_dir / "utils"
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "test_scratch"
        
        cmd = [
            sys.executable, str(script_path),
            "--output-dir", str(output_dir),
            "--use-test-data", str(utils_dir)
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"ERROR: Script failed with return code {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
        
        # Verify basic structure was created
        if not (output_dir / "fv3-jedi").exists():
            print("ERROR: fv3-jedi directory not created")
            return False
            
        if not (output_dir / "soca").exists():
            print("ERROR: soca directory not created") 
            return False
        
        # Check that SOCA files were generated
        soca_dir = output_dir / "soca"
        required_files = ["mom6_input.nml", "MOM_input"]
        for file in required_files:
            if not (soca_dir / file).exists():
                print(f"ERROR: Expected file {file} not found in soca directory")
                return False
        
        print("✓ Test data test passed!")
        return True


def main():
    """Run all tests."""
    print("Running tests for generate_coupled_scratch_directory.py\n")
    
    tests_passed = 0
    total_tests = 2
    
    if test_coupled_scratch_directory():
        tests_passed += 1
    
    if test_with_test_data():
        tests_passed += 1
    
    print(f"\n{tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("All tests completed successfully!")
        return 0
    else:
        print("Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())