import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { IMEI_COLOMBIA_URL, ImeiCheckButton } from "./ImeiCheckButton";

describe("ImeiCheckButton", () => {
  it("copies the IMEI and opens the official public lookup", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    const open = vi.spyOn(window, "open").mockImplementation(() => null);

    render(<ImeiCheckButton imei="490154203237518" />);
    fireEvent.click(screen.getByRole("button", { name: /Consultar en IMEI Colombia/ }));

    await waitFor(() =>
      expect(open).toHaveBeenCalledWith(IMEI_COLOMBIA_URL, "_blank", "noopener,noreferrer"),
    );
    expect(writeText).toHaveBeenCalledWith("490154203237518");
    expect(IMEI_COLOMBIA_URL).toBe("https://www.imeicolombia.com.co/");
  });
});
