import { bogotaDayBoundToUtc } from "@/modules/audit/presentation";
import { makeMe } from "@/test/fixtures";

import { can, PERMS } from "./permissions";
import { safeNextPath } from "./redirect";
import { changePasswordSchema, resetPasswordSchema } from "./schemas";

describe("safeNextPath", () => {
  it.each([
    [null, "/"],
    ["/usuarios", "/usuarios"],
    ["//evil.example.com", "/"],
    ["https://evil.example.com", "/"],
  ])("%s -> %s", (input, expected) => {
    expect(safeNextPath(input)).toBe(expected);
  });
});

describe("can", () => {
  it("checks the effective permissions of the user", () => {
    const me = makeMe();
    expect(can(me, PERMS.USERS_MANAGE)).toBe(true);
    expect(can(me, PERMS.ROLES_MANAGE)).toBe(false);
    expect(can(null, PERMS.USERS_READ)).toBe(false);
  });
});

describe("password schemas", () => {
  it("requires matching confirmation and minimum length", () => {
    const result = resetPasswordSchema.safeParse({
      new_password: "corta",
      confirm_password: "otra",
    });
    expect(result.success).toBe(false);
    const messages = result.error?.issues.map((i) => i.message) ?? [];
    expect(messages).toContain("Debe tener al menos 12 caracteres.");
    expect(messages).toContain("Las contraseñas no coinciden.");
  });

  it("rejects reusing the current password", () => {
    const result = changePasswordSchema.safeParse({
      current_password: "Una-clave-larga-1",
      new_password: "Una-clave-larga-1",
      confirm_password: "Una-clave-larga-1",
    });
    expect(result.error?.issues[0]?.message).toBe(
      "La nueva contraseña debe ser diferente a la actual.",
    );
  });
});

describe("bogotaDayBoundToUtc", () => {
  it("converts Bogotá local day bounds (UTC-5) to UTC", () => {
    expect(bogotaDayBoundToUtc("2026-11-19", "start")).toBe("2026-11-19T05:00:00.000Z");
    expect(bogotaDayBoundToUtc("2026-11-19", "end")).toBe("2026-11-20T04:59:59.999Z");
    expect(bogotaDayBoundToUtc("", "start")).toBeUndefined();
  });
});
