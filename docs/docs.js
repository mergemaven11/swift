const input = document.querySelector('#docs-search');
const sections = [...document.querySelectorAll('.searchable')];
const status = document.querySelector('#search-status');

function applySearch() {
  const query = input?.value.trim().toLowerCase() || '';
  let visible = 0;
  for (const section of sections) {
    const haystack = `${section.dataset.search || ''} ${section.textContent}`.toLowerCase();
    const match = !query || haystack.includes(query);
    section.classList.toggle('hidden', !match);
    if (match) visible += 1;
  }
  if (status) status.textContent = query ? `${visible} section${visible === 1 ? '' : 's'}` : '';
}

input?.addEventListener('input', applySearch);

const terminalOutput = document.querySelector('#terminal-output');
const terminalForm = document.querySelector('#terminal-form');
const terminalInput = document.querySelector('#terminal-input');
const commandButtons = [...document.querySelectorAll('[data-command]')];

const demoFiles = {
  './demo/dist/app.bin': {
    type: 'file',
    size: 5242880,
    mime: 'application/octet-stream',
    sha256: 'b39fd85a8f62cfdb8341b236b25b5af97d568a1f8976f093e884c8dc8ad1b32f'
  },
  './demo/dist/app-copy.bin': {
    type: 'file',
    size: 5242880,
    mime: 'application/octet-stream',
    sha256: 'b39fd85a8f62cfdb8341b236b25b5af97d568a1f8976f093e884c8dc8ad1b32f'
  },
  './demo/dist/release-manifest.json': {
    type: 'manifest',
    size: 842,
    mime: 'application/json',
    sha256: '54cda23bf18d14fcad87c8c12ea77f4ec9be91fab6281e76f1fcd822f580bfa1'
  },
  './demo/artifacts/release-2026.09.zip': {
    type: 'archive',
    size: 18423871,
    mime: 'application/zip',
    sha256: '1e80177458b052bca11e42e963d1c7c253c99f60ceca3b0a2cc2eb30ac7e6f7a'
  },
  './demo/artifacts/image.tar': {
    type: 'container',
    size: 48234496,
    mime: 'application/x-tar',
    sha256: '62d08411e6fd9d4ed54b9279aa54fcf47f1796c5855597cb644690327d76a30a'
  },
  './demo/artifacts/bom.cdx.json': {
    type: 'sbom',
    size: 15642,
    mime: 'application/vnd.cyclonedx+json',
    sha256: 'a0d878a0ca9fde9d0ecae5654d4a6ec61fef22878789d10296103183d62043a8'
  },
  './demo/data/customers.csv': {
    type: 'csv',
    size: 1248,
    mime: 'text/csv',
    sha256: '33aa85978e79c0ad175ec4237a6469778bcc1b11e3d26ec8dbb1565b27a40e2c'
  },
  './demo/docs/runbook.docx': {
    type: 'docx',
    size: 48830,
    mime: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    sha256: 'f5d1178fc5138d1f13d2bcfd90dc61bc919cc97cca3024c8b4af024f27fe346f'
  },
  './demo/docs/architecture.pdf': {
    type: 'pdf',
    size: 184220,
    mime: 'application/pdf',
    sha256: 'a96153fbfc6adfe13887545539134adbd67d46ddd98f56ece257461481b6c0c4'
  }
};

const directories = {
  '.': ['./demo'],
  './demo': ['./demo/dist', './demo/artifacts', './demo/data', './demo/docs'],
  './demo/dist': ['./demo/dist/app.bin', './demo/dist/app-copy.bin', './demo/dist/release-manifest.json'],
  './demo/artifacts': ['./demo/artifacts/release-2026.09.zip', './demo/artifacts/image.tar', './demo/artifacts/bom.cdx.json'],
  './demo/data': ['./demo/data/customers.csv'],
  './demo/docs': ['./demo/docs/runbook.docx', './demo/docs/architecture.pdf']
};

const state = {
  manifestBuilt: false,
  quarantined: false,
  history: [],
  historyIndex: 0
};

function line(text = '', kind = '') {
  if (!terminalOutput) return;
  const el = document.createElement('div');
  el.className = `terminal-line ${kind}`.trim();
  el.textContent = text;
  terminalOutput.appendChild(el);
  terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

function jsonBlock(value) {
  if (!terminalOutput) return;
  const el = document.createElement('code');
  el.className = 'terminal-json';
  el.textContent = JSON.stringify(value, null, 2);
  terminalOutput.appendChild(el);
  terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

function normalizePath(path) {
  if (!path) return '.';
  let value = path.replaceAll('\\', '/');
  if (value === '/workspace' || value === '/workspace/') return '.';
  if (value.startsWith('/workspace/')) value = '.' + value.slice('/workspace'.length);
  if (!value.startsWith('.') && !value.startsWith('/')) value = './' + value;
  return value.replace(/\/$/, '') || '.';
}

function basename(path) {
  return path.split('/').filter(Boolean).at(-1) || '.';
}

function formatBytes(bytes) {
  const units = ['B', 'KB', 'MB', 'GB'];
  let value = bytes;
  let unit = units[0];
  for (let i = 0; i < units.length - 1 && value >= 1024; i += 1) {
    value /= 1024;
    unit = units[i + 1];
  }
  return `${value >= 10 || unit === 'B' ? value.toFixed(0) : value.toFixed(1)} ${unit}`;
}

function tokensFrom(command) {
  return command.match(/(?:[^\s"]+|"[^"]*")+/g)?.map((token) => token.replace(/^"|"$/g, '')) || [];
}

function hasFlag(tokens, flag) {
  return tokens.includes(flag);
}

function valueAfter(tokens, flag, fallback = null) {
  const index = tokens.indexOf(flag);
  return index >= 0 && tokens[index + 1] ? tokens[index + 1] : fallback;
}

function requireFile(path) {
  const normalized = normalizePath(path);
  return { path: normalized, file: demoFiles[normalized] };
}

function printHelp() {
  line('SwiftFilez Browser Lab — supported demo commands', 'success');
  line('');
  line('  help | clear | pwd | ls [path]');
  line('  swf --version');
  line('  swf doctor [--json]');
  line('  swf config');
  line('  swf inspect <file> [--json]');
  line('  swf hash <file> [--algorithm sha256|sha512]');
  line('  swf scan <dir> [--json]');
  line('  swf duplicates <dir> [--apply --quarantine-dir <dir>]');
  line('  swf manifest build <dir> --output <file>');
  line('  swf manifest verify <manifest> --root <dir> --strict [--json]');
  line('  swf csv inspect <file> [--json]');
  line('  swf csv duplicates <file> --key <column>');
  line('  swf csv summarize <file> --group-by <column> --sum <column>');
  line('  swf docx inspect <file>');
  line('  swf pdf inspect <file>');
  line('  swf-artifact formats');
  line('  swf-artifact inspect <file> [--recursive] [--json]');
  line('');
  line('Tip: use ↑ / ↓ for command history.', 'muted');
}

function handleLs(tokens) {
  const path = normalizePath(tokens[1] || '.');
  const entries = directories[path];
  if (!entries) {
    line(`ls: cannot access '${tokens[1] || path}': demo directory not found`, 'error');
    return;
  }
  for (const entry of entries) {
    const isDir = Boolean(directories[entry]);
    line(`${isDir ? 'drwxr-xr-x' : '-rw-r--r--'}  ${isDir ? '   —' : formatBytes(demoFiles[entry].size).padStart(7)}  ${basename(entry)}`);
  }
}

function handleDoctor(tokens) {
  const result = {
    ok: true,
    version: '0.1.0-demo',
    python: '3.12.10',
    hash_algorithm: 'sha256',
    workers: 4,
    quarantine_dir: '.swiftfilez-quarantine',
    filesystem: 'browser demo (isolated)',
    network_required: false
  };
  if (hasFlag(tokens, '--json')) jsonBlock(result);
  else {
    line('SwiftFilez doctor', 'success');
    line('  status            healthy');
    line('  Python            3.12.10 (simulated)');
    line('  hash algorithm    sha256');
    line('  worker pool       4');
    line('  artifact access   demo workspace only');
    line('  network           not required');
  }
}

function handleConfig() {
  line('Effective configuration', 'success');
  line('  SWIFTFILEZ_HASH_ALGORITHM = sha256');
  line('  SWIFTFILEZ_WORKERS        = 4');
  line('  SWIFTFILEZ_QUARANTINE_DIR = .swiftfilez-quarantine');
  line('  runtime                    = browser simulation');
}

function handleInspect(tokens) {
  const target = tokens[2];
  if (!target) {
    line('usage: swf inspect <file> [--json]', 'error');
    return;
  }
  const { path, file } = requireFile(target);
  if (!file) {
    line(`error: '${target}' is not present in the demo workspace`, 'error');
    return;
  }
  const result = {
    path,
    name: basename(path),
    type: file.type,
    mime_type: file.mime,
    size_bytes: file.size,
    sha256: file.sha256
  };
  if (hasFlag(tokens, '--json')) jsonBlock(result);
  else {
    line(`File: ${path}`, 'success');
    line(`  type      ${file.type}`);
    line(`  MIME      ${file.mime}`);
    line(`  size      ${formatBytes(file.size)} (${file.size} bytes)`);
    line(`  SHA-256   ${file.sha256}`);
  }
}

function handleHash(tokens) {
  const target = tokens[2];
  if (!target) {
    line('usage: swf hash <file> [--algorithm sha256|sha512]', 'error');
    return;
  }
  const { path, file } = requireFile(target);
  if (!file) {
    line(`error: '${target}' is not present in the demo workspace`, 'error');
    return;
  }
  const algorithm = valueAfter(tokens, '--algorithm', 'sha256').toLowerCase();
  if (!['sha256', 'sha512'].includes(algorithm)) {
    line(`unsupported demo hash algorithm: ${algorithm}`, 'error');
    return;
  }
  const digest = algorithm === 'sha256'
    ? file.sha256
    : (file.sha256 + file.sha256.split('').reverse().join('')).slice(0, 128);
  line(`${algorithm}  ${digest}  ${path}`, 'success');
}

function scanResult(path) {
  const entries = directories[path] || [];
  return entries
    .filter((entry) => demoFiles[entry])
    .map((entry) => ({
      path: entry,
      type: demoFiles[entry].type,
      size_bytes: demoFiles[entry].size,
      sha256: demoFiles[entry].sha256
    }));
}

function handleScan(tokens) {
  const path = normalizePath(tokens[2] || '.');
  if (!directories[path]) {
    line(`error: demo directory '${tokens[2] || path}' not found`, 'error');
    return;
  }
  const results = scanResult(path);
  if (hasFlag(tokens, '--json')) {
    jsonBlock({ root: path, count: results.length, files: results });
    return;
  }
  line(`Scanning ${path} with 4 workers`, 'success');
  for (const item of results) {
    line(`  ${item.sha256.slice(0, 12)}  ${formatBytes(item.size_bytes).padStart(7)}  ${basename(item.path)}`);
  }
  line(`${results.length} file${results.length === 1 ? '' : 's'} inventoried`, 'muted');
}

function handleDuplicates(tokens) {
  const root = normalizePath(tokens[2] || './demo/dist');
  if (root !== './demo/dist') {
    line('Demo duplicate set exists in ./demo/dist', 'warn');
  }
  const apply = hasFlag(tokens, '--apply');
  const quarantine = valueAfter(tokens, '--quarantine-dir', './quarantine');
  if (state.quarantined) {
    line('No duplicate groups found. app-copy.bin is already quarantined in this demo session.', 'success');
    return;
  }
  line('Duplicate group 1', 'warn');
  line('  SHA-256  b39fd85a8f62cfdb…');
  line('  keep     ./demo/dist/app.bin');
  line('  extra    ./demo/dist/app-copy.bin');
  if (!apply) {
    line('');
    line('Dry run only — no files moved.', 'muted');
    line('Use: swf duplicates ./demo/dist --apply --quarantine-dir ./quarantine', 'muted');
  } else {
    state.quarantined = true;
    line(`Moved ./demo/dist/app-copy.bin → ${quarantine}/app-copy.bin`, 'success');
    line('Recoverable quarantine used; nothing was deleted.', 'muted');
  }
}

function handleManifest(tokens) {
  const action = tokens[2];
  if (action === 'build') {
    const root = normalizePath(tokens[3] || './demo/dist');
    const output = valueAfter(tokens, '--output', './demo/dist/release-manifest.json');
    if (!directories[root]) {
      line(`error: demo directory '${root}' not found`, 'error');
      return;
    }
    state.manifestBuilt = true;
    line(`Built integrity manifest for ${root}`, 'success');
    line(`  entries   ${scanResult(root).length}`);
    line(`  algorithm sha256`);
    line(`  output    ${output}`);
    return;
  }
  if (action === 'verify') {
    const manifest = tokens[3] || './demo/dist/release-manifest.json';
    const root = normalizePath(valueAfter(tokens, '--root', './demo/dist'));
    const result = {
      ok: true,
      manifest,
      root,
      strict: hasFlag(tokens, '--strict'),
      missing: [],
      changed: [],
      unexpected: state.quarantined ? [] : [],
      verified_files: state.quarantined ? 2 : 3
    };
    if (hasFlag(tokens, '--json')) jsonBlock(result);
    else {
      line('Integrity verification passed', 'success');
      line(`  manifest  ${manifest}`);
      line(`  root      ${root}`);
      line(`  checked   ${result.verified_files} files`);
      line('  changed   0');
      line('  missing   0');
      line('  exit code 0', 'muted');
    }
    return;
  }
  line('usage: swf manifest <build|verify> ...', 'error');
}

function handleCsv(tokens) {
  const action = tokens[2];
  const target = tokens[3] || './demo/data/customers.csv';
  if (normalizePath(target) !== './demo/data/customers.csv') {
    line('Demo CSV available at ./demo/data/customers.csv', 'error');
    return;
  }
  if (action === 'inspect') {
    const result = {
      path: './demo/data/customers.csv',
      rows: 8,
      columns: ['customer_id', 'customer', 'credit', 'debit', 'region'],
      duplicate_rows: 1,
      null_cells: 0
    };
    if (hasFlag(tokens, '--json')) jsonBlock(result);
    else {
      line('CSV inspection', 'success');
      line('  rows       8');
      line('  columns    5');
      line('  headers    customer_id, customer, credit, debit, region');
      line('  duplicates 1 row');
      line('  null cells 0');
    }
    return;
  }
  if (action === 'duplicates') {
    const key = valueAfter(tokens, '--key', 'customer_id');
    line(`Duplicate rows by key '${key}'`, 'warn');
    line('  row 3 / row 7  customer_id=C-104');
    return;
  }
  if (action === 'summarize') {
    const group = valueAfter(tokens, '--group-by', 'customer');
    const sum = valueAfter(tokens, '--sum', 'credit');
    line(`Grouped summary by ${group}; sum(${sum})`, 'success');
    line('  Acme Corp       18750.00');
    line('  Northwind        8420.00');
    line('  Contoso          6195.00');
    return;
  }
  line('Demo supports: swf csv inspect|duplicates|summarize', 'error');
}

function handleOffice(tokens, type) {
  const action = tokens[2];
  const fallback = type === 'docx' ? './demo/docs/runbook.docx' : './demo/docs/architecture.pdf';
  const target = normalizePath(tokens[3] || fallback);
  if (target !== fallback) {
    line(`Demo ${type.toUpperCase()} available at ${fallback}`, 'error');
    return;
  }
  if (action === 'inspect') {
    if (type === 'docx') {
      line('DOCX inspection', 'success');
      line('  title       Platform Operations Runbook');
      line('  paragraphs  42');
      line('  tables      3');
      line('  words       1,286');
    } else {
      line('PDF inspection', 'success');
      line('  title       Reference Architecture');
      line('  pages       12');
      line('  encrypted   false');
      line('  text layer  available');
    }
    return;
  }
  if (action === 'extract') {
    line(`Extracted demo ${type.toUpperCase()} text to stdout (simulation)`, 'success');
    line(type === 'docx'
      ? 'Runbook: verify release hash → inspect manifest → promote artifact…'
      : 'Architecture: build → verify → package → deploy → observe…');
    return;
  }
  line(`Demo supports: swf ${type} inspect|extract`, 'error');
}

function artifactResult(path, recursive) {
  const base = {
    path,
    format: path.endsWith('.zip') ? 'zip' : path.endsWith('.tar') ? 'docker-archive' : 'cyclonedx-json',
    sha256: demoFiles[path]?.sha256 || 'unknown',
    recursive
  };
  if (path.endsWith('.zip') && recursive) {
    base.children = [
      { path: 'app.whl', format: 'python-wheel' },
      { path: 'bom.cdx.json', format: 'cyclonedx-json', components: 24 },
      { path: 'provenance.json', format: 'in-toto-provenance' },
      { path: 'package.json', format: 'npm-manifest' }
    ];
  }
  return base;
}

function handleArtifact(tokens) {
  const action = tokens[1];
  if (action === 'formats') {
    line('Registered artifact families', 'success');
    line('  supply-chain  CycloneDX, SPDX, provenance, SARIF');
    line('  containers    Docker archive, OCI layout, TAR/ZIP/GZIP');
    line('  packages      wheel, JAR/WAR, NuGet, APK, IPA, deb/rpm');
    line('  dependencies  npm, Python, Go, Cargo, Bundler, Composer');
    line('  infra/config  Terraform, Dockerfile, Compose, JSON/YAML/TOML');
    line('  binaries      ELF, PE, Mach-O, WebAssembly');
    return;
  }
  if (action !== 'inspect') {
    line('usage: swf-artifact <formats|inspect>', 'error');
    return;
  }
  const target = normalizePath(tokens[2] || '');
  if (!demoFiles[target]) {
    line('Try ./demo/artifacts/release-2026.09.zip or ./demo/artifacts/image.tar', 'error');
    return;
  }
  const recursive = hasFlag(tokens, '--recursive') || hasFlag(tokens, '-r');
  const result = artifactResult(target, recursive);
  if (hasFlag(tokens, '--json')) {
    jsonBlock(result);
    return;
  }
  line(`Artifact: ${target}`, 'success');
  line(`  format     ${result.format}`);
  line(`  SHA-256    ${result.sha256}`);
  line(`  recursive  ${recursive}`);
  if (result.children) {
    line('  children');
    for (const child of result.children) {
      line(`    ↳ ${child.path.padEnd(20)} ${child.format}`);
    }
  }
}

function execute(command) {
  const trimmed = command.trim();
  if (!trimmed) return;

  line(trimmed, 'command');
  state.history.push(trimmed);
  state.historyIndex = state.history.length;

  const tokens = tokensFrom(trimmed);
  const root = tokens[0];

  if (root === 'clear') {
    if (terminalOutput) terminalOutput.innerHTML = '';
    return;
  }
  if (root === 'help') return printHelp();
  if (root === 'pwd') return line('/workspace');
  if (root === 'ls') return handleLs(tokens);
  if (root === 'whoami') return line('demo-user');
  if (root === 'swf-artifact') return handleArtifact(tokens);

  if (root !== 'swf') {
    line(`command not available in browser lab: ${root}`, 'error');
    line('Only documented SwiftFilez demo commands are accepted. Type help.', 'muted');
    return;
  }

  const action = tokens[1];
  if (action === '--version' || action === '-V') return line('swiftfilez 0.1.0-demo', 'success');
  if (action === 'doctor') return handleDoctor(tokens);
  if (action === 'config') return handleConfig();
  if (action === 'inspect') return handleInspect(tokens);
  if (action === 'hash') return handleHash(tokens);
  if (action === 'scan') return handleScan(tokens);
  if (action === 'duplicates') return handleDuplicates(tokens);
  if (action === 'manifest') return handleManifest(tokens);
  if (action === 'csv') return handleCsv(tokens);
  if (action === 'docx') return handleOffice(tokens, 'docx');
  if (action === 'pdf') return handleOffice(tokens, 'pdf');

  line(`unknown swf command: ${action || '(missing)'}`, 'error');
  line('Type help to see the browser demo command surface.', 'muted');
}

terminalForm?.addEventListener('submit', (event) => {
  event.preventDefault();
  if (!(terminalInput instanceof HTMLInputElement)) return;
  const command = terminalInput.value;
  terminalInput.value = '';
  execute(command);
});

terminalInput?.addEventListener('keydown', (event) => {
  if (!(terminalInput instanceof HTMLInputElement)) return;
  if (event.key === 'ArrowUp') {
    event.preventDefault();
    if (!state.history.length) return;
    state.historyIndex = Math.max(0, state.historyIndex - 1);
    terminalInput.value = state.history[state.historyIndex] || '';
  } else if (event.key === 'ArrowDown') {
    event.preventDefault();
    state.historyIndex = Math.min(state.history.length, state.historyIndex + 1);
    terminalInput.value = state.history[state.historyIndex] || '';
  }
});

for (const button of commandButtons) {
  button.addEventListener('click', () => {
    const command = button.dataset.command;
    if (!command) return;
    execute(command);
    terminalInput?.focus();
  });
}

if (terminalOutput) {
  line('SwiftFilez Browser Lab', 'success');
  line('Safe demo filesystem mounted at /workspace/demo', 'muted');
  line('No device files are read. No commands are executed on a server.', 'muted');
  line('');
  line('Try: swf doctor   or type help', 'success');
}
