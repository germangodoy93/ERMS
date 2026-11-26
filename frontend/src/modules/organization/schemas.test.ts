import { organizationSchema, type OrganizationValues } from "./schemas";

const VALID: OrganizationValues = {
  name: "Taller Ficticio",
  legal_name: "Taller Ficticio S.A.S.",
  tax_id: "900123456-8",
  address: "Calle 1 # 2-3",
  city: "Bogotá",
  phone: "3001234567",
  email: "",
  warranty_days: "90",
  assembly_bottleneck_gap: "25",
  assembly_margin_percent: "15",
  assembly_min_ram_gb: "16",
};

function errorsOf(values: Partial<OrganizationValues>): string[] {
  const result = organizationSchema.safeParse({ ...VALID, ...values });
  return result.success ? [] : result.error.issues.map((i) => i.path.join("."));
}

describe("organizationSchema", () => {
  it("accepts the stored values of the workshop", () => {
    expect(errorsOf({})).toEqual([]);
    expect(errorsOf({ assembly_margin_percent: "12,5" })).toEqual([]);
    expect(errorsOf({ assembly_margin_percent: "12.75" })).toEqual([]);
  });

  it.each([
    ["assembly_bottleneck_gap", "4"],
    ["assembly_bottleneck_gap", "dd"],
    ["assembly_bottleneck_gap", "2.5"],
    ["assembly_min_ram_gb", "2"],
    ["assembly_min_ram_gb", "d"],
    ["assembly_margin_percent", "abc"],
    ["assembly_margin_percent", "301"],
    ["warranty_days", "0"],
  ] as const)("rejects %s = %s", (field, value) => {
    expect(errorsOf({ [field]: value })).toContain(field);
  });
});
