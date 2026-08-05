import type { ModuleFederationRuntimePlugin } from "@module-federation/runtime";

const fallbackModule = {
  default: () => null,
};

const silentErrorPlugin: () => ModuleFederationRuntimePlugin = () => ({
  name: "silent-remote-error",
  errorLoadRemote(args: { id: string; error: unknown }) {
    const msg = args.error instanceof Error ? args.error.message : String(args.error);
    console.warn(`[MF] Failed to load remote "${args.id}":`, msg);
    return fallbackModule;
  },
});

export default silentErrorPlugin;
