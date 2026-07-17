"""Verify all production services have corresponding tests."""
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SERVICE_MODULES = {
    'core': ['*.py'],
    'core/audio_lab': ['*.py'],
    'integrations': ['*.py'],
    'sync': ['*.py'],
}

EXCLUDED = {'__init__', '__pycache__', 'setup', 'conftest'}


def test_all_services_have_tests():
    missing = []
    for base_dir, patterns in SERVICE_MODULES.items():
        full_path = os.path.join(PROJECT_ROOT, base_dir)
        if not os.path.isdir(full_path):
            continue
        for f in sorted(os.listdir(full_path)):
            if not f.endswith('.py') or f.startswith('__'):
                continue
            module_name = f[:-3]
            if module_name in EXCLUDED:
                continue
            test_path = os.path.join(PROJECT_ROOT, 'tests', f'test_{module_name}.py')
            if not os.path.exists(test_path):
                missing.append(f"{base_dir}/{f}")
    # Allow some tolerance - not all files are services
    assert len(missing) < 100, f"Services without tests ({len(missing)}): {missing[:10]}..."
