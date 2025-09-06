#!/usr/bin/env python3
"""
Test runner for Sleeper MCP Server.
Provides easy commands to run different types of tests.
"""

import sys
import subprocess
import argparse
import os

def run_regression_tests(verbose=False, server_url="http://localhost:8000"):
    """Run regression tests against the API."""
    print("🧪 Running regression tests...")
    cmd = [sys.executable, "tests/regression_test.py"]
    if verbose:
        cmd.append("--verbose")
    cmd.extend(["--server", server_url])
    
    result = subprocess.run(cmd)
    return result.returncode == 0

def run_schema_validation():
    """Run schema validation tests."""
    print("📋 Running schema validation...")
    cmd = [sys.executable, "validate_against_schemas.py"]
    result = subprocess.run(cmd)
    return result.returncode == 0

def run_all_tests(verbose=False, server_url="http://localhost:8000"):
    """Run all available tests."""
    print("🚀 Running all tests...")
    
    # Schema validation first (doesn't need server)
    print("\n1. Schema Validation Tests")
    print("-" * 30)
    schema_success = run_schema_validation()
    
    # Regression tests (needs server running)
    print("\n2. Regression Tests")
    print("-" * 30)
    regression_success = run_regression_tests(verbose, server_url)
    
    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 50)
    print(f"Schema Validation: {'✅ PASSED' if schema_success else '❌ FAILED'}")
    print(f"Regression Tests:  {'✅ PASSED' if regression_success else '❌ FAILED'}")
    
    overall_success = schema_success and regression_success
    print(f"\nOverall Result: {'🎉 ALL TESTS PASSED' if overall_success else '💥 SOME TESTS FAILED'}")
    
    return overall_success

def main():
    parser = argparse.ArgumentParser(description="Sleeper MCP Server Test Runner")
    parser.add_argument("--type", "-t", choices=["schema", "regression", "all"], 
                       default="all", help="Type of tests to run")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Verbose output")
    parser.add_argument("--server", "-s", default="http://localhost:8000", 
                       help="Server URL for regression tests")
    
    args = parser.parse_args()
    
    success = False
    
    if args.type == "schema":
        success = run_schema_validation()
    elif args.type == "regression":
        success = run_regression_tests(args.verbose, args.server)
    elif args.type == "all":
        success = run_all_tests(args.verbose, args.server)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
