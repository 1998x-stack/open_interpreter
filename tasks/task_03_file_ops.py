#!/usr/bin/env python3
"""
Task 03: File operations with batch renaming and directory organization
"""

import os
import shutil
import tempfile
import time
from pathlib import Path
from datetime import datetime
from typing import List, Tuple


def create_sample_files(directory: Path, num_files: int = 10) -> List[Path]:
    """Create sample files for demonstration"""
    file_extensions = ['.txt', '.py', '.js', '.md', '.csv', '.json']
    sample_contents = [
        "This is a sample text file.",
        "#!/usr/bin/env python\nprint('Hello World')",
        "console.log('Hello World');",
        "# Sample Markdown\nThis is a sample markdown file.",
        "name,age,city\nJohn,30,NYC",
        '{"name": "sample", "value": 42}'
    ]
    
    created_files = []
    
    for i in range(num_files):
        ext = file_extensions[i % len(file_extensions)]
        filename = f"sample_file_{i:02d}{ext}"
        filepath = directory / filename
        
        with open(filepath, 'w') as f:
            content_idx = i % len(sample_contents)
            f.write(sample_contents[content_idx])
        
        # Add some variation in modification times
        mod_time = time.time() - (i * 86400)  # Different days ago
        os.utime(filepath, (mod_time, mod_time))
        
        created_files.append(filepath)
    
    return created_files


def organize_by_extension(source_dir: Path, target_dir: Path):
    """Organize files by extension into subdirectories"""
    print(f"Organizing files from {source_dir} to {target_dir}")
    
    # Create extension-based subdirectories
    ext_dirs = {}
    for file_path in source_dir.glob("*"):
        if file_path.is_file():
            ext = file_path.suffix.lower() or "_no_ext"
            ext_dir = target_dir / ext[1:] if ext.startswith('.') else ext  # Remove dot from extension
            ext_dir.mkdir(exist_ok=True)
            
            # Move file to appropriate directory
            target_path = ext_dir / file_path.name
            shutil.move(str(file_path), str(target_path))
            print(f"  Moved {file_path.name} to {ext_dir.name}/")


def batch_rename(directory: Path, prefix: str = "renamed_"):
    """Batch rename files in a directory with a prefix"""
    files = [f for f in directory.iterdir() if f.is_file()]
    
    print(f"Renaming {len(files)} files in {directory} with prefix '{prefix}'")
    
    renamed_count = 0
    for file_path in files:
        new_name = f"{prefix}{file_path.name}"
        new_path = file_path.parent / new_name
        
        # Handle naming conflicts
        counter = 1
        while new_path.exists():
            name_part = file_path.stem
            ext_part = file_path.suffix
            new_name = f"{prefix}{name_part}_{counter}{ext_part}"
            new_path = file_path.parent / new_name
            counter += 1
        
        file_path.rename(new_path)
        print(f"  Renamed {file_path.name} -> {new_name}")
        renamed_count += 1
    
    return renamed_count


def get_file_stats(file_paths: List[Path]) -> dict:
    """Get statistics about a list of files"""
    total_size = 0
    file_types = {}
    
    for file_path in file_paths:
        if file_path.is_file():
            size = file_path.stat().st_size
            total_size += size
            
            ext = file_path.suffix.lower() or "_no_ext"
            if ext in file_types:
                file_types[ext] += 1
            else:
                file_types[ext] = 1
    
    return {
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "file_count": len(file_paths),
        "file_types": file_types
    }


def find_duplicate_names(directory: Path) -> List[Tuple[str, List[Path]]]:
    """Find files with duplicate names in subdirectories"""
    name_map = {}
    
    for file_path in directory.rglob("*"):
        if file_path.is_file():
            name = file_path.name
            if name not in name_map:
                name_map[name] = []
            name_map[name].append(file_path)
    
    duplicates = [(name, paths) for name, paths in name_map.items() if len(paths) > 1]
    return duplicates


def main():
    print("Task 3: File Operations - Batch Renaming and Directory Organization")
    print("=" * 70)
    
    # Create a temporary directory for our operations
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create sample files
        print("Creating sample files...")
        sample_files = create_sample_files(temp_path, 15)
        initial_stats = get_file_stats(sample_files)
        
        print(f"Created {initial_stats['file_count']} files with total size: {initial_stats['total_size_mb']} MB")
        print(f"File types: {initial_stats['file_types']}")
        
        # Create an 'organized' subdirectory
        organized_dir = temp_path / "organized"
        organized_dir.mkdir()
        
        # Organize files by extension
        print("\nOrganizing files by extension...")
        organize_by_extension(temp_path, organized_dir)
        
        # Get stats for organized files
        all_org_files = []
        for subdir in organized_dir.iterdir():
            if subdir.is_dir():
                all_org_files.extend(list(subdir.glob("*")))
        
        organized_stats = get_file_stats(all_org_files)
        print(f"After organization: {organized_stats['file_count']} files")
        
        # Perform batch renaming in each subdirectory
        print("\nPerforming batch renaming...")
        for subdir in organized_dir.iterdir():
            if subdir.is_dir():
                print(f"\nRenaming files in {subdir.name}/:")
                renamed_count = batch_rename(subdir, prefix=f"file_{subdir.name}_")
                print(f"Renamed {renamed_count} files in {subdir.name}/")
        
        # Look for potential duplicate names after renaming
        print("\nChecking for duplicate file names...")
        duplicates = find_duplicate_names(organized_dir)
        if duplicates:
            print("Found potential duplicates:")
            for name, paths in duplicates:
                print(f"  {name}: {[str(p) for p in paths]}")
        else:
            print("  No duplicate file names found.")
        
        # Final statistics
        all_final_files = []
        for subdir in organized_dir.iterdir():
            if subdir.is_dir():
                all_final_files.extend(list(subdir.glob("*")))
        
        final_stats = get_file_stats(all_final_files)
        print(f"\nFinal stats: {final_stats['file_count']} files, {final_stats['total_size_mb']} MB")
        print(f"File types after organization: {final_stats['file_types']}")
        
        print(f"\nOrganization completed! Files organized in: {organized_dir}")
        
        # List the final structure
        print("\nFinal directory structure:")
        for subdir in organized_dir.iterdir():
            if subdir.is_dir():
                files_in_subdir = list(subdir.glob("*"))
                print(f"  {subdir.name}/: {len(files_in_subdir)} files")
    
    print("\nTask completed successfully!")


if __name__ == "__main__":
    main()