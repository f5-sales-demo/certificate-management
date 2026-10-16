import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'docs/placeholders.json')));
const fields = new Set(manifest.fields);
let blocks = 0;
const walk = (directory) =>
  fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const file = path.join(directory, entry.name);
    return entry.isDirectory() ? walk(file) : file.endsWith('.md') ? [file] : [];
  });
for (const file of walk(path.join(root, 'docs/en'))) {
  const original = fs.readFileSync(file, 'utf8');
  const source = original.replace(/<div data-personalize="off">[\s\S]*?<\/div>/g, '');
  assert.ok(!/xXCSH_[A-Z0-9_]+x/.test(source), file + ': legacy marker');
  assert.ok(
    !/certificate-management(?:-terraform)?\.f5-sales-demo\.com/.test(source.replace(/\[[\s\S]*?\]\([^)]*\)/g, '')),
    file + ': hardcoded reader hostname',
  );
  for (const marker of source.matchAll(/<(XCSH_[A-Z0-9_]+)>/g))
    assert.ok(fields.has(marker[1]), file + ': undeclared ' + marker[1]);
  const fenced = [...source.matchAll(/```(bash|hcl|json)\n([\s\S]*?)```/g)];
  for (const block of fenced) {
    blocks++;
    const before = source.slice(0, block.index);
    const annotation = before.match(/<div data-xcsh-context="(shell|hcl|json)" data-xcsh-fields="([^"]*)">\s*$/);
    assert.ok(annotation, file + ': missing context/fields');
    const selected = new Set(annotation[2].split(/\s+/).filter(Boolean));
    for (const name of selected) assert.ok(fields.has(name), file + ': unknown dependency ' + name);
    for (const name of fields) {
      if (
        new RegExp('\\b' + name + '\\b').test(block[2]) &&
        !(name === 'XCSH_TLS_INPUT_PASSWORD' && block[1] === 'hcl')
      )
        assert.ok(selected.has(name), file + ': undeclared dependency ' + name);
      assert.ok(
        !new RegExp('^\\s*(?:export\\s+)?' + name + '=([^\\n]*)', 'm').test(block[2]),
        file + ': input assignment overrides selection ' + name,
      );
    }
    if (block[1] === 'bash' && file.includes('/terraform/'))
      assert.ok(!/^\s*(xcsh|vesctl)\b/m.test(block[2]), file + ': external encryption CLI');
  }
}
assert.equal(fields.size, 31);
assert.equal(manifest.behavior.environmentCredentials, true);
assert.equal(manifest.behavior.fallbackToDefaults, true);
console.log(
  'Customization audit passed: English pages, ' +
    blocks +
    ' annotated blocks, ' +
    fields.size +
    ' catalog fields.',
);
