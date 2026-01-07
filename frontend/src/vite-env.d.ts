/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_STRIPE_PUBLISHABLE_KEY?: string;
  readonly VITE_ENVIRONMENT?: "development" | "production" | "staging";
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// Tauri API types
declare global {
  interface Window {
    __TAURI__?: {
      invoke: (cmd: string, args?: Record<string, unknown>) => Promise<unknown>;
      convertFileSrc: (filePath: string, protocol?: string) => string;
    };
  }
}

// Extend Leaflet types if needed
declare module "leaflet" {
  // Add any custom Leaflet type extensions here
}

// Module declarations for assets
declare module "*.svg" {
  import React = require("react");
  export const ReactComponent: React.FC<React.SVGProps<SVGSVGElement>>;
  const src: string;
  export default src;
}

declare module "*.png" {
  const content: string;
  export default content;
}

declare module "*.jpg" {
  const content: string;
  export default content;
}

declare module "*.jpeg" {
  const content: string;
  export default content;
}

declare module "*.gif" {
  const content: string;
  export default content;
}

declare module "*.webp" {
  const content: string;
  export default content;
}

declare module "*.ico" {
  const content: string;
  export default content;
}

declare module "*.css" {
  const content: Record<string, string>;
  export default content;
}
