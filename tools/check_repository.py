"""Validate tracked source, notebook hygiene, privacy, and declared build targets."""
import ast
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
PRIVATE_PATH = re.compile(r'(?:[A-Za-z]\\?:[\\/]+Users[\\/]+|/Us' r'ers/|/ho' r'me/)[^\s"<>]+')
TOKEN = re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|sk-[A-Za-z0-9_-]{32,}|xox[baprs]-[A-Za-z0-9-]{20,})')
DISALLOWED_NAMES = {'local.properties', 'credentials.csv', 'credentials.db', '.env'}
DISALLOWED_PARTS = {'.idea', '.gradle', '__pycache__', '.ipynb_checkpoints'}
TEXT_EXTENSIONS = {'.py', '.java', '.c', '.h', '.cs', '.md', '.txt', '.csv', '.sql', '.xml', '.json', '.ipynb', '.yml', '.yaml', '.toml', '.properties', '.sh', '.bash', '.sed', '.awk'}

def source_files():
    proc = subprocess.run(['git', '-c', 'safe.directory=' + ROOT.as_posix(), 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT, capture_output=True, check=True)
    return sorted({ROOT / p.decode('utf-8') for p in proc.stdout.split(b'\0') if p})

def main():
    failures = []
    files = source_files()
    for path in files:
        relative = path.relative_to(ROOT)
        if not path.exists():
            continue  # A tracked file can be deleted in a pending change.
        if path.name in DISALLOWED_NAMES or any(p in DISALLOWED_PARTS for p in relative.parts):
            failures.append(str(relative) + ': local/private file must not be tracked')
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding='utf-8')
            if '\x00' in text:
                failures.append(str(relative) + ': unexpected NUL/mixed encoding')
            if PRIVATE_PATH.search(text) or TOKEN.search(text):
                failures.append(str(relative) + ': potential private path or credential (value withheld)')
            if path.suffix == '.py':
                ast.parse(text, filename=str(relative))
            elif path.suffix == '.xml':
                ET.fromstring(text)
            elif path.suffix == '.cs':
                declarations = re.findall(r'^\s*public class (\w+)\s*:\s*MonoBehaviour', text, re.MULTILINE)
                if declarations and path.stem not in declarations:
                    failures.append(str(relative) + ': Unity component filename must match its class')
            elif path.suffix in {'.json', '.ipynb'}:
                data = json.loads(text)
                if path.suffix == '.ipynb':
                    for cell in data.get('cells', []):
                        if cell.get('outputs') or cell.get('execution_count') is not None:
                            failures.append(str(relative) + ': clear notebook outputs and execution counts')
                        if cell.get('cell_type') == 'code':
                            code = ''.join(cell.get('source', []))
                            if not any(line.lstrip().startswith(('%', '!')) for line in code.splitlines()):
                                ast.parse(code, filename=str(relative))
        except (UnicodeError, SyntaxError, ValueError, ET.ParseError) as error:
            failures.append(str(relative) + ': ' + type(error).__name__)
    if failures:
        print('\n'.join(failures), file=sys.stderr)
        return 1
    manifest = ROOT / 'tools/build_manifest.json'
    if manifest.exists():
        groups = json.loads(manifest.read_text())
        with tempfile.TemporaryDirectory() as temp:
            for number, group in enumerate(groups):
                if group.get('platforms') and sys.platform not in group['platforms']:
                    print('Unsupported local platform; CI checks: ' + ', '.join(group['sources']))
                    continue
                compiler = shutil.which(group['compiler'])
                if compiler is None:
                    raise SystemExit('Required compiler missing: ' + group['compiler'])
                sources = [str(ROOT / p) for p in group['sources']]
                if group['compiler'] == 'javac':
                    output = pathlib.Path(temp) / str(number)
                    output.mkdir()
                    command = [compiler, '-encoding', 'UTF-8', '-d', str(output)] + sources
                else:
                    command = [compiler, '-std=c11', '-Wall', '-Wextra'] + sources + group.get('flags', []) + ['-o', str(pathlib.Path(temp) / ('program' + str(number)))]
                subprocess.run(command, check=True, cwd=ROOT)
        print('Declared build targets checked (platform exceptions reported above).')
    if (ROOT / 'tests').is_dir():
        subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=ROOT, check=True)
    print('Repository checks passed for ' + str(len(files)) + ' source/configuration files.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
