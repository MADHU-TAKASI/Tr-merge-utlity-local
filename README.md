# # Git Commits Stager & Archiver

This utility script helps you extract and archive changed files from specific Git commits within a given date range. It allows you to interactively select commits, stages the changed files (while preserving their relative paths), creates a manifest file, and finally packages the staged files into a ZIP archive.

## Overview

The script performs the following tasks:
- **Date Range Filtering:**  
  Prompts the user to input a start and end date (in `dd/mm/yyyy` format) and retrieves all commits from the current branch within that range.

- **Commit Selection:**  
  Lists the commits and allows the user to select specific commits by their index for processing.

- **File Staging:**  
  For each selected commit, the script identifies the changed files and copies them into a staging folder while preserving the original directory structure.

- **Manifest Creation:**  
  Generates a `changes.json` manifest file in the staging folder that lists all staged files.

- **ZIP Archive:**  
  Creates a ZIP archive (`staged_commits.zip`) containing all files from the staging folder.

## Prerequisites

- **Python Version:**  
  Python 3.7 or higher is required.

- **Dependencies:**  
  Install the required Python packages using pip:
  ```bash
  pip install GitPython
