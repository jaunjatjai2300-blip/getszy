// Regression guard for the production fix (commit e67ad2a):
//  - must POST to /api/ai-tools/chat/completions (not the legacy /api/ai/chat/completions)
//  - must parse JSON `choices[0].message.content` (not raw SSE text)
import { generateWithAI } from '../utils/aiBuilder';

describe('generateWithAI', () => {
  let originalFetch;
  beforeEach(() => {
    originalFetch = global.fetch;
    localStorage.setItem('gs_token', 'test-jwt-token');
  });
  afterEach(() => {
    global.fetch = originalFetch;
    localStorage.clear();
  });

  it('posts to the chat/completions endpoint with auth and returns parsed JSON content', async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ choices: [{ message: { content: 'hello world' } }] }),
      })
    );

    const result = await generateWithAI({ prompt: 'make a plan', type: 'dashboard' });

    expect(global.fetch).toHaveBeenCalledTimes(1);
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toContain('/api/ai-tools/chat/completions');
    expect(opts.method).toBe('POST');
    expect(opts.headers.Authorization).toBe('Bearer test-jwt-token');
    const body = JSON.parse(opts.body);
    expect(body.messages[1].content).toBe('make a plan');
    expect(result).toBe('hello world');
  });

  it('throws a readable error when the response is not ok', async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) })
    );
    await expect(generateWithAI({ prompt: 'x', type: 'course' })).rejects.toThrow(/500/);
  });
});
