/**
 * localStorage key constants — single source of truth.
 *
 * Every localStorage key used by the GUI must be defined here.
 * This prevents drift between runtime code, tests, and documentation
 * (e.g. release-gate.md reset snippets).
 */

/** Whether the demo nudge has been dismissed by the user. Value: "true" or absent. */
export const DEMO_NUDGE_DISMISSED_KEY = "redletters_demo_nudge_dismissed";

/** JSON array of recently visited scripture references. Max 5 entries. */
export const RECENT_REFS_KEY = "redletters_recent_refs";

/** Whether the bootstrap wizard has been completed. Value: "true" | "skipped" or absent. */
export const BOOTSTRAP_COMPLETED_KEY = "redletters_bootstrap_completed";

/** Auth token for browser-mode API access. */
export const AUTH_TOKEN_KEY = "redletters_auth_token";

/** Token display density preference. Value: "compact" | "comfortable". Default: "comfortable". */
export const TOKEN_DENSITY_KEY = "redletters_token_density";
