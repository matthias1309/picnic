/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Root path the built API client calls (REQ-019). Defaults to /picnic/api. */
  readonly VITE_API_BASE?: string;
}
