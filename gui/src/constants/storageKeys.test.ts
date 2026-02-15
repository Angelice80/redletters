import { describe, it, expect } from "vitest";
import {
  DEMO_NUDGE_DISMISSED_KEY,
  RECENT_REFS_KEY,
  BOOTSTRAP_COMPLETED_KEY,
  AUTH_TOKEN_KEY,
  ONBOARDING_DISMISSED_KEY,
} from "./storageKeys";

describe("storageKeys constants", () => {
  it("DEMO_NUDGE_DISMISSED_KEY is the canonical demo nudge key", () => {
    expect(DEMO_NUDGE_DISMISSED_KEY).toBe("redletters_demo_nudge_dismissed");
  });

  it("RECENT_REFS_KEY is the canonical recent refs key", () => {
    expect(RECENT_REFS_KEY).toBe("redletters_recent_refs");
  });

  it("BOOTSTRAP_COMPLETED_KEY is the canonical bootstrap key", () => {
    expect(BOOTSTRAP_COMPLETED_KEY).toBe("redletters_bootstrap_completed");
  });

  it("AUTH_TOKEN_KEY is the canonical auth token key", () => {
    expect(AUTH_TOKEN_KEY).toBe("redletters_auth_token");
  });

  it("ONBOARDING_DISMISSED_KEY is the canonical onboarding key", () => {
    expect(ONBOARDING_DISMISSED_KEY).toBe("redletters_onboarding_dismissed");
  });

  it("all keys use the redletters_ prefix", () => {
    const keys = [
      DEMO_NUDGE_DISMISSED_KEY,
      RECENT_REFS_KEY,
      BOOTSTRAP_COMPLETED_KEY,
      AUTH_TOKEN_KEY,
      ONBOARDING_DISMISSED_KEY,
    ];
    for (const key of keys) {
      expect(key).toMatch(/^redletters_/);
    }
  });
});
