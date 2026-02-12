CodeVault CLI - How to Use
=============================

We have created several ways to use the CLI:


FOR INTERACTIVE USE (Double-click these):
======================================

1. codevault-interactive.bat (RECOMMENDED for beginners)
   - Double-click this file
   - Shows a menu with numbered options
   - Type a number (1-8) to select a command
   - Can run multiple commands without closing
   - Best for learning the CLI

2. codevault.bat (Alternative)
   - Double-click this file
   - Shows a simple menu with 6 options
   - Select what you want to do
   - Can run multiple commands


FOR COMMAND LINE USE:
===================

1. Open Command Prompt or PowerShell
2. Navigate to Code Vault folder:
   cd "C:\Users\YourName\OneDrive\Desktop\Code Vault"
3. Run commands like:
   codevault.bat auth login
   codevault.bat project list
   codevault.bat project build my-project --fast


QUICK START GUIDE:
================

First time using CodeVault CLI?

1. Double-click: codevault-interactive.bat
2. Press [1] to login
3. Press [4] to list your projects
4. Press [5] to build a project
5. Follow the prompts
6. Press [0] when done


EXAMPLE COMMANDS:
===============

Login:
  codevault auth login

List projects:
  codevault project list

Build interactively:
  codevault project build --interactive

Build specific project:
  codevault project build PROJECT-ID --fast

Check status:
  codevault system status


TROUBLESHOOTING:
===============

Problem: Window closes immediately
Solution: Use codevault-interactive.bat instead

Problem: "Python not found"
Solution: Install Python from https://python.org

Problem: Can't type commands
Solution: You must use the interactive BAT files, not the regular codevault.bat


WHICH FILE SHOULD I USE?
=======================

- Complete beginner? → codevault-interactive.bat
- Want simple menu? → codevault.bat
- Using command line? → codevault.bat [command]
- Testing setup? → TEST-CLI.bat
