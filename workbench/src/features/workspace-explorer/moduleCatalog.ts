import type { ExtensionModuleDefinition } from "../../lib/ipc";

// Concrete defaults require U-4 approval. An empty catalog does not block
// user-created definitions, nor silently select a product default.
export const BUILTIN_EXTENSION_MODULES: readonly ExtensionModuleDefinition[] = [];
