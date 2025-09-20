"""Re-validate existing anonymization mappings and interactively review suspects.

This file was copied from SHIELD3 root and adjusted to import from the local
`pii_detector` service if possible.
"""
import json
import os
import shutil
from typing import Dict

HERE = os.path.dirname(os.path.abspath(__file__))


def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def backup(path):
    if os.path.exists(path):
        bak = path + '.bak'
        shutil.copyfile(path, bak)
        print(f'Backup created: {bak}')


def main():
    try:
        from backend.app.services.pii_detector import validate_mapping
    except Exception:
        try:
            from pii_detector import validate_mapping
        except Exception as exc:
            print(f'Error: cannot import validate_mapping: {exc}')
            return

    map_dir = os.path.join(HERE, '..', 'map')
    os.makedirs(map_dir, exist_ok=True)
    map_path = os.path.join(map_dir, 'anonymized_map.json')
    suspects_path = os.path.join(map_dir, 'anonymized_map_suspects.json')

    orig_map = load_json(map_path) or {}
    orig_valid_map = orig_map.get('mapping') if isinstance(orig_map, dict) else None
    if orig_valid_map is None:
        orig_valid_map = {}

    suspects_obj = load_json(suspects_path) or {}
    orig_suspects = suspects_obj.get('suspects') if isinstance(suspects_obj, dict) else None
    if orig_suspects is None:
        orig_suspects = {}

    combined = {}
    combined.update(orig_valid_map)
    combined.update(orig_suspects)

    if not combined:
        print('No mappings found in anonymized_map.json or anonymized_map_suspects.json. Nothing to do.')
        return

    print(f'Loaded {len(orig_valid_map)} valid entries and {len(orig_suspects)} suspect entries. Re-validating...')

    valid, suspects = validate_mapping(combined)

    backup(map_path)
    backup(suspects_path)

    out_valid = {'mapping': valid}
    save_json(map_path, out_valid)
    print(f'Wrote {len(valid)} valid entries to {map_path}')

    save_json(suspects_path, {'suspects': suspects})
    print(f'Wrote {len(suspects)} suspect entries to {suspects_path}')

    if not suspects:
        print('No suspects to review.')
        return

    print('\nStarting interactive review of suspects. For each entry choose:')
    print('  (c) confirm as valid  (e) edit original value  (d) delete mapping  (s) skip/leave as suspect')

    tokens = list(suspects.keys())
    for tok in tokens:
        orig = suspects.get(tok)
        print('\nToken:', tok)
        print('Original value:', repr(orig))
        while True:
            try:
                choice = input("Choose (c/e/d/s): ").strip().lower()
            except EOFError:
                choice = 's'
            if choice not in ('c','e','d','s'):
                print('Invalid choice. Use c, e, d or s.')
                continue
            if choice == 'c':
                valid[tok] = orig
                if tok in suspects:
                    del suspects[tok]
                print(f'{tok} confirmed as valid.')
                break
            if choice == 'e':
                newval = input('New original value (empty cancels): ').strip()
                if not newval:
                    print('Edit cancelled.')
                    continue
                suspects[tok] = newval
                print('Edited. Mark as valid? (y/n)')
                yn = input().strip().lower()
                if yn in ('y','yes'):
                    valid[tok] = newval
                    del suspects[tok]
                    print(f'{tok} updated and confirmed valid.')
                else:
                    print(f'{tok} updated but left as suspect.')
                break
            if choice == 'd':
                if tok in suspects:
                    del suspects[tok]
                if tok in valid:
                    del valid[tok]
                print(f'{tok} deleted from mappings.')
                break
            if choice == 's':
                print(f'{tok} left as suspect.')
                break

    save_json(map_path, {'mapping': valid})
    save_json(suspects_path, {'suspects': suspects})
    print('\nInteractive review complete.')
    print(f'Final: {len(valid)} valid entries, {len(suspects)} suspects.')


if __name__ == '__main__':
    main()
