"""
MVC Project Initialization Script
Generates __init__.py files in all package directories and verifies project structure
"""
import os
import sys
from pathlib import Path


class MVCProjectCheckup:
    """Validates and initializes MVC project structure"""
    
    # Expected project structure
    EXPECTED_STRUCTURE = {
        'root_files': [
            'main.py',
            'config.py',
            'requirements.txt',
            'README.md',
            '.gitignore'
        ],
        'packages': {
            'models': ['file_scanner.py', 'http_client.py'],
            'views': ['main_window.py'],
            'controllers': ['scanner_controller.py'],
            'utils': ['logger.py', 'validators.py'],
            'tests': ['test_file_scanner.py', 'test_http_client.py']
        }
    }
    
    INIT_CONTENT = '''"""
{package_name} package
"""
'''
    
    def __init__(self, project_root='.'):
        self.project_root = Path(project_root)
        self.results = {
            'created': [],
            'existing': [],
            'missing': [],
            'warnings': []
        }
    
    def run_checkup(self):
        """Run complete project checkup and initialization"""
        print("=" * 60)
        print("MVC PROJECT CHECKUP & INITIALIZATION")
        print("=" * 60)
        print(f"Project Root: {self.project_root.absolute()}\n")
        
        # Check root files
        self._check_root_files()
        
        # Create/check package directories
        self._create_package_directories()
        
        # Create __init__.py files
        self._create_init_files()
        
        # Check package files
        self._check_package_files()
        
        # Print results
        self._print_results()
        
        return len(self.results['missing']) == 0 and len(self.results['warnings']) == 0
    
    def _check_root_files(self):
        """Check if all root files exist"""
        print("\n[1/4] Checking root files...")
        
        for filename in self.EXPECTED_STRUCTURE['root_files']:
            filepath = self.project_root / filename
            if filepath.exists():
                print(f"  ✓ {filename}")
                self.results['existing'].append(str(filepath.relative_to(self.project_root)))
            else:
                print(f"  ✗ {filename} - MISSING")
                self.results['missing'].append(filename)
    
    def _create_package_directories(self):
        """Create package directories if they don't exist"""
        print("\n[2/4] Checking/creating package directories...")
        
        for package_name in self.EXPECTED_STRUCTURE['packages'].keys():
            package_path = self.project_root / package_name
            
            if package_path.exists():
                print(f"  ✓ {package_name}/ (exists)")
            else:
                package_path.mkdir(parents=True, exist_ok=True)
                print(f"  + {package_name}/ (created)")
    
    def _create_init_files(self):
        """Create __init__.py files in all packages"""
        print("\n[3/4] Creating/checking __init__.py files...")
        
        for package_name in self.EXPECTED_STRUCTURE['packages'].keys():
            init_path = self.project_root / package_name / '__init__.py'
            
            if init_path.exists():
                print(f"  ✓ {package_name}/__init__.py (exists)")
                self.results['existing'].append(str(init_path.relative_to(self.project_root)))
            else:
                try:
                    content = self.INIT_CONTENT.format(package_name=package_name)
                    init_path.write_text(content)
                    print(f"  + {package_name}/__init__.py (created)")
                    self.results['created'].append(str(init_path.relative_to(self.project_root)))
                except Exception as e:
                    print(f"  ✗ {package_name}/__init__.py - ERROR: {e}")
                    self.results['warnings'].append(f"Failed to create {package_name}/__init__.py: {e}")
    
    def _check_package_files(self):
        """Check if expected files exist in each package"""
        print("\n[4/4] Checking package files...")
        
        for package_name, files in self.EXPECTED_STRUCTURE['packages'].items():
            package_path = self.project_root / package_name
            print(f"\n  {package_name}:")
            
            for filename in files:
                filepath = package_path / filename
                if filepath.exists():
                    size = filepath.stat().st_size
                    print(f"    ✓ {filename} ({size} bytes)")
                else:
                    print(f"    ✗ {filename} - MISSING")
                    self.results['missing'].append(f"{package_name}/{filename}")
    
    def _print_results(self):
        """Print checkup results summary"""
        print("\n" + "=" * 60)
        print("CHECKUP RESULTS")
        print("=" * 60)
        
        print(f"\n✓ Created: {len(self.results['created'])} files")
        for item in self.results['created']:
            print(f"  + {item}")
        
        print(f"\n✓ Existing: {len(self.results['existing'])} files")
        for item in self.results['existing']:
            print(f"  ✓ {item}")
        
        if self.results['missing']:
            print(f"\n✗ Missing: {len(self.results['missing'])} files")
            for item in self.results['missing']:
                print(f"  ✗ {item}")
        
        if self.results['warnings']:
            print(f"\n⚠ Warnings: {len(self.results['warnings'])}")
            for item in self.results['warnings']:
                print(f"  ⚠ {item}")
        
        print("\n" + "=" * 60)
        
        # Final status
        if len(self.results['missing']) == 0 and len(self.results['warnings']) == 0:
            print("✓ PROJECT STRUCTURE IS VALID & INITIALIZED!")
            print("=" * 60)
            return True
        else:
            print("✗ PROJECT STRUCTURE HAS ISSUES - SEE ABOVE")
            print("=" * 60)
            return False
    
    def print_tree(self):
        """Print directory tree of project"""
        print("\n" + "=" * 60)
        print("PROJECT TREE")
        print("=" * 60)
        self._print_tree_recursive(self.project_root, "", is_last=True)
    
    def _print_tree_recursive(self, path, prefix, is_last):
        """Recursively print directory tree"""
        if path == self.project_root:
            print(f"{path.name}/")
        
        try:
            items = sorted([item for item in path.iterdir() 
                          if not item.name.startswith('.')])
        except PermissionError:
            return
        
        # Filter out unwanted directories
        skip_dirs = {'__pycache__', '.git', 'venv', '.venv', '.pytest_cache', 'logs'}
        items = [item for item in items if item.name not in skip_dirs]
        
        for i, item in enumerate(items):
            is_last_item = i == len(items) - 1
            current_prefix = "└── " if is_last_item else "├── "
            print(f"{prefix}{current_prefix}{item.name}")
            
            if item.is_dir() and item.name not in skip_dirs:
                next_prefix = prefix + ("    " if is_last_item else "│   ")
                self._print_tree_recursive(item, next_prefix, is_last_item)


def main():
    """Main entry point"""
    # Determine project root (current directory or argument)
    project_root = sys.argv[1] if len(sys.argv) > 1 else '.'
    
    # Create and run checkup
    checkup = MVCProjectCheckup(project_root)
    success = checkup.run_checkup()
    
    # Print tree
    checkup.print_tree()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()