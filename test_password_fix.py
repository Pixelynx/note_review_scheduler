#!/usr/bin/env python3
"""
Simple Git Bash password input - avoids problematic stty approach.
"""

import os
import sys
import signal
import getpass
from typing import Any

def setup_signal_handling():
    """Set up proper signal handling for Git Bash."""
    def signal_handler(signum: int, frame: Any) -> None:
        print("\nPress Enter to confirm exit, or Ctrl+C again to force quit...")
        try:
            input()
            print("Test interrupted by user")
            sys.exit(0)
        except KeyboardInterrupt:
            print("Force quit - test terminated")
            sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)

def get_password_simple(prompt: str) -> str:
    """
    Simple password input that works in Git Bash by avoiding stty.
    Matches the CLI implementation with Ctrl+C confirmation.
    """
    # If we're in Git Bash, just use visible input with a warning
    if os.name == 'nt' and 'MSYSTEM' in os.environ:
        print(f"\nNote: Running in Git Bash - password will be visible while typing.")
        print("(This is normal for Git Bash - your password is still secure)")
        sys.stdout.write(prompt)
        sys.stdout.flush()
        try:
            # Use sys.stdin.readline() for better signal handling
            password = sys.stdin.readline().strip()
            return password
        except KeyboardInterrupt:
            print("\nPress Enter to confirm exit, or Ctrl+C again to force quit...")
            try:
                input()
                print("Process cancelled by user")
                sys.exit(0)
            except KeyboardInterrupt:
                print("Force quit - process terminated")
                sys.exit(0)
    else:
        # Use standard getpass for other terminals
        try:
            return getpass.getpass(prompt)
        except KeyboardInterrupt:
            print("\nPress Enter to confirm exit, or Ctrl+C again to force quit...")
            try:
                input()
                print("Process cancelled by user")
                sys.exit(0)
            except KeyboardInterrupt:
                print("Force quit - process terminated")
                sys.exit(0)

def main():
    # Set up signal handling first
    setup_signal_handling()
    
    print("Simple Git Bash password test...")
    print("This tests the same Ctrl+C confirmation used in the CLI.\n")
    
    print("Environment:")
    print(f"  OS: {os.name}")
    print(f"  MSYSTEM: {os.environ.get('MSYSTEM', 'Not set')}")
    
    if os.name == 'nt' and 'MSYSTEM' in os.environ:
        print(" ==> Will use visible input (no hanging)")
    else:
        print(" ==> Will use hidden input (getpass)")
    
    print()
    
    try:
        password1 = get_password_simple("Enter test password: ")
        password2 = get_password_simple("Confirm password: ")
        
        if password1 == password2:
            print("SUCCESS: Passwords match!")
        else:
            print("Input works (passwords don't match)")
        
        print("No hanging!")
        
    except KeyboardInterrupt:
        print("\nPress Enter to confirm exit, or Ctrl+C again to force quit...")
        try:
            input()
            print("Test cancelled by user")
            sys.exit(0)
        except KeyboardInterrupt:
            print("Force quit - test terminated")
            sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()