// vitest.setup.ts
// React 18's act() only suppresses its "not configured for act()" warning
// when this flag is set -- normally done automatically by
// @testing-library/react, which this repo doesn't use (kept the frontend
// test footprint minimal, see vitest.config.ts).
(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
