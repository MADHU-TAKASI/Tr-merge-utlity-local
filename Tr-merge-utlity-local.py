import os
import json
import shutil
from git import Repo
from zipfile import ZipFile
from datetime import datetime


# ----- Utility Functions -----

def parse_date_input(date_str):
    """Parse a date string in dd/mm/yyyy format and return a datetime object (or None if invalid)."""
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except ValueError:
        return None


def get_commits_between_dates(repo, branch, start_date_str, end_date_str):
    """
    Retrieve commits between two dates (inclusive) in the given branch.
    Dates should be in dd/mm/yyyy format.
    Returns a list of commits (sorted newest first).
    """
    start_date_obj = parse_date_input(start_date_str)
    end_date_obj = parse_date_input(end_date_str)
    if not start_date_obj:
        print(f"Invalid start date: {start_date_str}.")
        return []
    if not end_date_obj:
        print(f"Invalid end date: {end_date_str}.")
        return []
    if start_date_obj > end_date_obj:
        print("Start date must be earlier than or equal to end date.")
        return []

    start_date = start_date_obj.strftime("%Y-%m-%d")
    end_date = end_date_obj.strftime("%Y-%m-%d")
    commits = list(repo.iter_commits(branch, since=start_date, until=end_date))
    commits.sort(key=lambda c: c.committed_date, reverse=True)
    return commits


def copy_files_to_staging(changed_files, repo_path, staging_folder):
    """
    For each file in changed_files, copy it from repo_path into staging_folder,
    preserving the relative directory structure.
    Returns a set of all files (relative paths) that were successfully staged.
    """
    staged_files = set()
    for file_path in changed_files:
        src = os.path.join(repo_path, file_path)
        if os.path.exists(src):
            dest = os.path.join(staging_folder, file_path)
            dest_dir = os.path.dirname(dest)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)
            try:
                shutil.copy2(src, dest)
                staged_files.add(file_path)
            except Exception as e:
                print(f"Error copying {file_path}: {e}")
        else:
            print(f"Warning: File '{file_path}' does not exist in the working directory.")
    return staged_files


def create_manifest(staged_files, staging_folder):
    """
    Create a JSON manifest file (changes.json) inside staging_folder listing all staged files.
    """
    manifest = {"changed_files": list(staged_files)}
    manifest_path = os.path.join(staging_folder, "changes.json")
    with open(manifest_path, "w") as mf:
        json.dump(manifest, mf, indent=4)
    return manifest_path


def zip_staging_folder(staging_folder, zip_filename):
    """
    Create a ZIP archive of the entire staging_folder.
    """
    with ZipFile(zip_filename, 'w') as zipf:
        for root, dirs, files in os.walk(staging_folder):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, staging_folder)
                zipf.write(abs_path, arcname=rel_path)
    print(f"ZIP file '{zip_filename}' created successfully.")


# ----- Main Process -----

def main():
    repo_path = os.getcwd()  # Assume the current working directory is the repository
    try:
        repo = Repo(repo_path)
    except Exception as e:
        print(f"Error opening repository: {e}")
        return

    if not repo.head.is_detached:
        current_branch = repo.active_branch.name
        print(f"Current branch: {current_branch}")
    else:
        print("Repository is in a detached HEAD state.")
        return

    # Ask for date range input
    while True:
        start_date_input = input("Enter start date (dd/mm/yyyy): ").strip()
        if parse_date_input(start_date_input):
            break
        print("Invalid start date. Please enter a valid date in dd/mm/yyyy format.")
    while True:
        end_date_input = input("Enter end date (dd/mm/yyyy): ").strip()
        if parse_date_input(end_date_input):
            break
        print("Invalid end date. Please enter a valid date in dd/mm/yyyy format.")

    print(f"Selected date range: {start_date_input} to {end_date_input}")

    commits = get_commits_between_dates(repo, current_branch, start_date_input, end_date_input)
    if not commits:
        print("No commits found in the specified date range.")
        return

    print(f"\nCommits between {start_date_input} and {end_date_input} in branch '{current_branch}':")
    for i, commit in enumerate(commits):
        commit_date = datetime.fromtimestamp(commit.committed_date).strftime("%d/%m/%Y")
        print(f"{i}: {commit.hexsha[:7]} - {commit_date} - {commit.message.strip()}")

    print("\nEnter the commit index for each commit you want to process.")
    print("After entering each index, the changed files for that commit will be staged.")
    print("When you are finished, type 'e' to end the selection and create the ZIP archive.")

    # Prepare a staging folder (clear if already exists)
    staging_folder = os.path.join(repo_path, "staging_folder")
    if os.path.exists(staging_folder):
        shutil.rmtree(staging_folder)
    os.makedirs(staging_folder, exist_ok=True)

    overall_changed_files = set()
    selected_commit_indices = []  # List to store selected commit indices

    while True:
        user_input = input("Enter commit index (or 'e' to finish): ").strip().lower()
        if user_input == 'e':
            break
        try:
            index = int(user_input)
            if 0 <= index < len(commits):
                selected_commit_indices.append(index)
                commit = commits[index]
                print(f"Processing commit {commit.hexsha[:7]} (index {index})...")
                if not commit.parents:
                    print(f"Commit {commit.hexsha[:7]} has no parent (initial commit), skipping.")
                    continue
                parent = commit.parents[0]
                diff = repo.git.diff('--name-only', parent.hexsha, commit.hexsha)
                changed_files = diff.splitlines()
                if not changed_files:
                    print(f"No changed files in commit {commit.hexsha[:7]}.")
                else:
                    staged = copy_files_to_staging(changed_files, repo_path, staging_folder)
                    overall_changed_files.update(staged)
                    print(f"Staged {len(staged)} file(s) from commit {commit.hexsha[:7]}.")
            else:
                print("Index out of range. Please enter a valid index.")
        except ValueError:
            print("Invalid input. Please enter a valid number or 'e'.")

    if not overall_changed_files:
        print("No files were staged from the selected commits. Exiting.")
        return

    # Display the selected commit indices and corresponding commit hashes before zipping
    print("\nThe following commits were selected and processed:")
    for idx in sorted(selected_commit_indices):
        commit = commits[idx]
        print(f"Index {idx}: {commit.hexsha[:7]} - {commit.message.strip()}")

    # Create manifest file in staging folder
    create_manifest(overall_changed_files, staging_folder)

    # Create a ZIP archive of the staging folder
    zip_filename = "staged_commits.zip"
    zip_staging_folder(staging_folder, zip_filename)

    print("Required commits are successfully zipped.")


if __name__ == "__main__":
    main()
