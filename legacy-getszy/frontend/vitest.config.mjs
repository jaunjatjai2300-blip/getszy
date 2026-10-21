import { mergeConfig } from 'vite';
import { defineConfig } from 'vitest/config';
import viteConfig from './vite.config.mjs';

// Jest-compatible globals so the CRA-era tests (jest.fn / describe / it) run
// unchanged under vitest.
export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./src/test-setup.js'],
    },
  })
);
