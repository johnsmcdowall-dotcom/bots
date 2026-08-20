import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
      // Next.js special-cases this import to error only when a "server
      // only" module gets bundled into client code; that's meaningless in
      // a plain Node test run, and the real package isn't installed since
      // Next doesn't require it to be for the app itself to build.
      "server-only": path.resolve(import.meta.dirname, "./test/server-only-stub.ts"),
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
