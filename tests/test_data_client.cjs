const {test} = require('node:test');
const assert = require('node:assert/strict');
const {safeSourceUrl} = require('../public/data-client.js');
test('original HTTPS sources remain usable', () => {
 assert.equal(safeSourceUrl('https://example.org/poll?q=1'), 'https://example.org/poll?q=1');
});
test('malformed and unsafe sources cannot interrupt rendering or become links', () => {
 for (const input of [null, undefined, '', 'broken', '/relative', 'javascript:alert(1)', 'http://example.org', 'https://user:password@example.org']) {
  assert.equal(safeSourceUrl(input), null);
 }
});
